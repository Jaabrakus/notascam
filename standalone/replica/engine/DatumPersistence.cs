using System.IO;
using System.Linq;
using System.Text.Json.Serialization;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Procs;
using OpenDreamRuntime.Resources;
using OpenDreamShared.Resources;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;

namespace OpenDreamRuntime.Objects.Types;

// A graph is required: selected units, ownership, inventory and ordinary DM
// lists may contain aliases and cycles. The upstream tree serializer loses both.
public sealed partial class DreamObjectSavefile {
    private WriteGraph? _writeGraph;
    private ReadGraph? _readGraph;
    private const string GraphKey = ".opendream_graph";

    public sealed class SfGraphReference : SfDreamJsonValue {
        public int Id { get; set; }
    }
    public sealed class SfGraphTable : SfDreamJsonValue {
        public List<GraphNode> Objects { get; set; } = new();
    }
    public sealed class GraphNode {
        public string? Type { get; set; }
        public SfDreamDir Fields { get; set; } = new();
        public List<SfDreamJsonValue> Values { get; set; } = new();
        public List<SfDreamJsonValue?> Associated { get; set; } = new();
        public SfDreamJsonValue? IconData { get; set; }
    }
    private sealed class WriteGraph {
        public readonly SfGraphTable Table = new();
        public readonly Dictionary<DreamObject, int> Ids = new();
    }
    private sealed class ReadGraph(SfGraphTable table) {
        public readonly SfGraphTable Table = table;
        // Keep DreamValues alive until the whole graph has been restored.
        public readonly Dictionary<int, DreamValue> Values = new();
    }

    public void WriteDatum(DreamObject datum) {
        var outer = _writeGraph == null;
        if (outer) {
            _writeGraph = new WriteGraph();
            CurrentDir[GraphKey] = _writeGraph.Table;
        }
        try {
            foreach (var key in datum.ObjectDefinition.Variables.Keys) {
                if (!datum.IsSaved(key)) continue;
                using var value = datum.GetVariable(key);
                CurrentDir[key] = EncodeGraphValue(value);
            }
            SavefilesToFlush.Add(this);
        } finally {
            if (outer) _writeGraph = null;
        }
    }

    public void ReadDatum(DreamObject datum) {
        var outer = _readGraph == null;
        if (outer && CurrentDir.TryGetValue(GraphKey, out var graph) && graph is SfGraphTable table)
            _readGraph = new ReadGraph(table);
        try {
            foreach (var key in CurrentDir.Keys.ToArray()) {
                if (!datum.IsSaved(key)) continue;
                using var value = DecodeGraphValue(CurrentDir[key]);
                if (key == "contents" && datum is DreamObjectMovable container && value.TryGetValueAsDreamList(out var contents)) {
                    foreach (var item in contents.EnumerateValues())
                        if (item.TryGetValueAsDreamObject<DreamObjectMovable>(out var child)) child.SetLoc(container);
                } else datum.SetVariable(key, value);
            }
        } finally {
            if (outer && _readGraph != null) {
                foreach (var value in _readGraph.Values.Values) value.Dispose();
                _readGraph = null;
            }
        }
    }

    private SfDreamJsonValue EncodeGraphValue(DreamValue value) {
        if (value.IsNull) return new SfDreamPrimitive();
        if (!value.TryGetValueAsDreamObject(out var obj) || obj == null)
            return SerializeDreamValue(value);
        if (obj is DreamObjectSavefile) return SerializeDreamValue(value);
        var graph = _writeGraph!;
        if (graph.Ids.TryGetValue(obj, out var existing)) return new SfGraphReference { Id = existing };
        var id = graph.Table.Objects.Count;
        graph.Ids.Add(obj, id);
        var node = new GraphNode();
        graph.Table.Objects.Add(node);
        if (obj is DreamList list) {
            foreach (var item in list.EnumerateValues()) {
                node.Values.Add(EncodeGraphValue(item));
                if (list.ContainsKey(item)) {
                    using var associated = list.GetValue(item);
                    node.Associated.Add(EncodeGraphValue(associated));
                } else node.Associated.Add(null);
            }
        } else {
            node.Type = obj.ObjectDefinition.Type;
            if (obj is DreamObjectIcon && DreamResourceManager.TryLoadIcon(value, out var icon))
                node.IconData = SerializeDreamValue(new DreamValue(icon));
            var directory = CurrentDir;
            try {
                CurrentDir = node.Fields;
                obj.SpawnProc("Write", null, new DreamValue(this)).Dispose();
            } finally { CurrentDir = directory; }
        }
        return new SfGraphReference { Id = id };
    }

    private DreamValue DecodeGraphValue(SfDreamJsonValue encoded) {
        if (encoded is not SfGraphReference reference) return DeserializeJsonValue(encoded);
        var graph = _readGraph ?? throw new InvalidDataException("Save reference has no object table");
        if (graph.Values.TryGetValue(reference.Id, out var existing)) {
            existing.IncRef();
            return existing;
        }
        if (reference.Id < 0 || reference.Id >= graph.Table.Objects.Count)
            throw new InvalidDataException("Save reference is outside the object table");
        var node = graph.Table.Objects[reference.Id];
        if (node.Type == null) {
            var list = ObjectTree.CreateList();
            var result = new DreamValue(list);
            result.IncRef();
            graph.Values.Add(reference.Id, result);
            for (var i = 0; i < node.Values.Count; i++) {
                using var item = DecodeGraphValue(node.Values[i]);
                if (node.Associated[i] is { } associated) {
                    using var data = DecodeGraphValue(associated);
                    list.SetValue(item, data);
                } else list.AddValue(item);
            }
            return result;
        }
        if (!ObjectTree.TryGetTreeEntry(node.Type, out var type))
            throw new InvalidDataException("Unknown saved type: " + node.Type);
        var obj = ObjectTree.CreateObject(type);
        var value = new DreamValue(obj);
        value.IncRef();
        graph.Values.Add(reference.Id, value);
        // BYOND calls New with initial fields, followed by Read. Cache first so
        // recursive ownership references resolve to this very same object.
        if (node.IconData != null) {
            using var icon = DecodeGraphValue(node.IconData);
            obj.InitSpawn(new DreamProcArguments(icon));
        } else obj.InitSpawn(new DreamProcArguments());
        var directory = CurrentDir;
        try {
            CurrentDir = node.Fields;
            obj.SpawnProc("Read", null, new DreamValue(this)).Dispose();
        } finally { CurrentDir = directory; }
        return value;
    }

    private DreamValue RestoreFileValue(SfDreamFileValue file) {
        var data = Convert.FromBase64String(file.Data);
        // Reuse an unchanged packaged asset, preserving its icon resource type
        // and identity. Otherwise reconstruct a typed image from the saved bytes.
        if (!string.IsNullOrEmpty(file.Name) && File.Exists(file.Name)) {
            var original = DreamResourceManager.LoadResource(file.Name);
            if (original.ResourceData is { } bytes && bytes.AsSpan().SequenceEqual(data))
                return new DreamValue(original);
        }
        var extension = file.Ext?.TrimStart('.').ToLowerInvariant();
        if (extension is "dmi" or "png" or "bmp") {
            var texture = Image.Load<Rgba32>(data);
            var description = DMIParser.ParseDMI(new MemoryStream(data));
            return new DreamValue(DreamResourceManager.CreateIconResource(data, texture, description));
        }
        return new DreamValue(DreamResourceManager.CreateResource(data));
    }
}
