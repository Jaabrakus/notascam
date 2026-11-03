# Remastered engine patch: packaged icons are saved by name, not copied in (map-memory, 2026-10-25;
# reports/map-memory/join-hitch.md). Exact-match edits on the build's copies of the replica's DatumPersistence.cs and
# OpenDream's DreamResourceManager.cs (work/src/; replica/ and standalone/opendream are never touched).
#
# Before: WriteDatum wrote an atom's icon as the icon file's bytes. Each item carrying its type's icon stored a full copy
# of the sheet (Cave.dmi: 132 KB of base64), which an engine loads back as a nameless copy, so it keeps the art it had
# when first saved and is written as a copy again. The user's unit save: 3.26 MB for 3 units and 19 items, every one of
# its 22 icons a copy of the original game's file.
# After:
# - Write: an atom's icon that is a packaged icon (one of the game's own files) is saved as its path, a text value.
#   Setting an atom's icon to a path gives it that packaged icon on any engine (AtomManager: TryLoadIcon loads the path),
#   so an engine without this patch reads the new saves exactly. Anything else (a composed icon) is saved as before.
# - Read: an atom's saved icon file is taken as a packaged icon (today's art, no decoding) when it names one, or when it
#   is a nameless copy whose SHA-256 is a known earlier version of one (icon-history.txt in the world folder, made by
#   icon_history.py; a different picture can't match). Anything else loads as before.

FILES = {
    'Objects/Types/DatumPersistence.cs': [
        ("""            foreach (var key in datum.ObjectDefinition.Variables.Keys) {
                if (!datum.IsSaved(key)) continue;
                using var value = datum.GetVariable(key);
                CurrentDir[key] = EncodeGraphValue(value);
            }
""", """            foreach (var key in datum.ObjectDefinition.Variables.Keys) {
                if (!datum.IsSaved(key)) continue;
                using var value = datum.GetVariable(key);
                if (RmPackagedIconPath(datum, key, value) is { } rmPath) {   // Remastered: a packaged icon is saved by name
                    CurrentDir[key] = new SfDreamPrimitive { Value = new DreamValue(rmPath) };
                    continue;
                }
                CurrentDir[key] = EncodeGraphValue(value);
            }
""", 1),
        ("""            foreach (var key in CurrentDir.Keys.ToArray()) {
                if (!datum.IsSaved(key)) continue;
                using var value = DecodeGraphValue(CurrentDir[key]);
""", """            foreach (var key in CurrentDir.Keys.ToArray()) {
                if (!datum.IsSaved(key)) continue;
                if (CurrentDir[key] is SfDreamFileValue rmFile && key == "icon" && datum is DreamObjectAtom && RmKnownIcon(rmFile) is { } rmPath) {
                    datum.SetVariable(key, new DreamValue(rmPath));   // Remastered: a copy of a packaged icon is that icon
                    continue;
                }
                using var value = DecodeGraphValue(CurrentDir[key]);
""", 1),
        ("""        return new DreamValue(DreamResourceManager.CreateResource(data));
    }
}
""", """        return new DreamValue(DreamResourceManager.CreateResource(data));
    }

    // --- Remastered: packaged icons are saved by name, not copied in (map-memory, 2026-10-25) ---
    private static HashSet<string>? _rmPackaged;            // the paths of the game's own resources
    private static Dictionary<string, string>? _rmHistory;  // SHA-256 of an earlier version of a packaged icon -> its path

    private HashSet<string> RmPackaged() {
        if (_rmPackaged != null) return _rmPackaged;
        var set = new HashSet<string>();
        var all = DreamResourceManager.RmResources;
        for (var i = 1; i < DreamResourceManager.RmPackagedCount && i < all.Count; i++)
            if (all[i].ResourcePath is { } p) set.Add(p);
        return _rmPackaged = set;
    }

    // An atom's icon that is one of the game's own icon files: its path (saved as text), else null (saved as before).
    private string? RmPackagedIconPath(DreamObject datum, string key, DreamValue value) {
        if (key != "icon" || datum is not DreamObjectAtom || !value.TryGetValueAsDreamResource(out var res) || res is not IconResource) return null;
        return res.ResourcePath != null && RmPackaged().Contains(res.ResourcePath) ? res.ResourcePath : null;
    }

    // A saved icon file that is a packaged icon: by its name, or a nameless copy that is a known earlier version of one.
    private string? RmKnownIcon(SfDreamFileValue file) {
        if (file.Name != null) return RmPackaged().Contains(file.Name) ? file.Name : null;
        if (string.IsNullOrEmpty(file.Data)) return null;
        var history = RmHistory();
        if (history.Count == 0) return null;
        byte[] bytes;
        try { bytes = Convert.FromBase64String(file.Data); } catch (FormatException) { return null; }
        var hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes)).ToLowerInvariant();
        return history.TryGetValue(hash, out var path) ? path : null;
    }

    // icon-history.txt in the world folder: {"icons": {"<sha256>": "<file name>"}}, each name resolved to the one packaged
    // icon with that file name (none or several: left out).
    private Dictionary<string, string> RmHistory() {
        if (_rmHistory != null) return _rmHistory;
        var byName = new Dictionary<string, string?>();
        foreach (var p in RmPackaged()) {
            if (!p.EndsWith(".dmi", StringComparison.OrdinalIgnoreCase)) continue;
            var n = Path.GetFileName(p);
            byName[n] = byName.ContainsKey(n) ? null : p;
        }
        var history = new Dictionary<string, string>();
        try {
            if (File.Exists("icon-history.txt")) {
                using var doc = System.Text.Json.JsonDocument.Parse(File.ReadAllText("icon-history.txt"));
                foreach (var e in doc.RootElement.GetProperty("icons").EnumerateObject())
                    if (e.Value.GetString() is { } n && byName.TryGetValue(n, out var p) && p != null) history[e.Name] = p;
            }
        } catch (Exception e) when (e is IOException or System.Text.Json.JsonException or KeyNotFoundException or InvalidOperationException) {
            history.Clear();
        }
        return _rmHistory = history;
    }
}
""", 1),
    ],
    'Resources/DreamResourceManager.cs': [
        ("""    private readonly List<DreamResource> _resourceCache = new();
""", """    private readonly List<DreamResource> _resourceCache = new();
    internal IReadOnlyList<DreamResource> RmResources => _resourceCache;   // Remastered: the save patch's packaged icons
    internal int RmPackagedCount { get; private set; }                    // resources below this id are the game's own
""", 1),
        ("""        _aczProvider = new DreamAczProvider(_dependencyCollection, rootPath, resources);
""", """        RmPackagedCount = _resourceCache.Count;
        _aczProvider = new DreamAczProvider(_dependencyCollection, rootPath, resources);
""", 1),
    ],
}
NEW = {}


# --- Remastered: saves written off the game thread (the spike hunt, 10-31; RmSaveLater.cs) ---
# The autosave's unit saves (a savefile the game marks rm_later, Saves.dm) are turned into text and written by a background
# task when they close; anything that reads, checks, copies or deletes a file waits for those writes first, and the process
# waits before it exits. A savefile another datum still has open, a temporary one, or one not marked is flushed as before.
FILES.setdefault('Objects/Types/DreamObjectSavefile.cs', []).append(("""    public void Close() {
        // We need to avoid Flush() recreating a nonexistent file
        if (File.Exists(Resource!.ResourcePath)) Flush();
""", """    public void Close() {
        // We need to avoid Flush() recreating a nonexistent file
        if (File.Exists(Resource!.ResourcePath)) {
            if (!_isTemporary && RmLater() && RmAlone()) {   // Remastered: written off the game thread (RmSaveLater.cs)
                var root = _rootNode;
                var own = Resource.ResourcePath!;
                var to = _rmLaterTo ?? own;   // a fresh file stood in for this one, so its old contents were never read
                RmSaveLater.Write(() => JsonSerializer.Serialize(root), to, to != own ? own : null);
                Resource.ReloadFromDisk();
                if (to != own) DreamResourceManager.LoadResource(to).ReloadFromDisk();
            } else Flush();
        }
""", 1))
FILES['Objects/Types/DreamObjectSavefile.cs'].append(("""    public void Flush() {
        Resource!.Clear();
""", """    // Remastered: the game asked for this save to be written later (S.rm_later = 1, Saves.dm), or written later to
    // another file (S.rm_later = "its path": this one opened fresh in its place, so the old save was never read in)
    private bool _rmLater;
    private string? _rmLaterTo;
    private bool RmLater() => _rmLater;

    // Remastered: no other savefile datum has this file open (its contents are shared with them)
    private bool RmAlone() {
        foreach (var savefile in Savefiles)
            if (savefile != this && savefile.Resource?.ResourcePath == Resource!.ResourcePath) return false;
        return true;
    }

    public void Flush() {
        Resource!.Clear();
""", 1))
FILES.setdefault('Resources/DreamResource.cs', []).append(("""        get {
            if (_resourceDataBacking == null && File.Exists(filePath)) {
""", """        get {
            if (_resourceDataBacking == null) RmSaveLater.Wait();   // Remastered: a save still being written first
            if (_resourceDataBacking == null && File.Exists(filePath)) {
""", 1))
FILES['Resources/DreamResourceManager.cs'] += [
    ("""    public bool DoesFileExist(string resourcePath) {
""", """    public bool DoesFileExist(string resourcePath) {
        RmSaveLater.Wait();   // Remastered: a save still being written first (RmSaveLater.cs)
""", 1),
    ("""    public bool DeleteFile(string filePath) {
""", """    public bool DeleteFile(string filePath) {
        RmSaveLater.Wait();   // Remastered: a save still being written first (RmSaveLater.cs)
""", 1),
    ("""    public bool CopyFile(DreamResource sourceFile, string destinationFilePath) {
""", """    public bool CopyFile(DreamResource sourceFile, string destinationFilePath) {
        RmSaveLater.Wait();   // Remastered: a save still being written first (RmSaveLater.cs)
""", 1),
]
NEW['RmSaveLater.cs'] = 'RmSaveLater.cs'
FILES['Objects/Types/DreamObjectSavefile.cs'] += [
    ("""            case "dir":
                value = new DreamValue(new SavefileDirList(ObjectTree.List.ObjectDefinition, this));
                return true;
            default:
                return base.TryGetVar(varName, out value);
""", """            case "dir":
                value = new DreamValue(new SavefileDirList(ObjectTree.List.ObjectDefinition, this));
                return true;
            case "rm_later":   // Remastered: written off the game thread when it closes (RmSaveLater.cs)
                value = _rmLaterTo != null ? new DreamValue(_rmLaterTo) : _rmLater ? DreamValue.True : DreamValue.False;
                return true;
            default:
                return base.TryGetVar(varName, out value);
""", 1),
    ("""            default:
                throw new DMException($"Cannot set var \\"{varName}\\" on savefiles");
""", """            case "rm_later":   // Remastered: written off the game thread when it closes (RmSaveLater.cs)
                _rmLater = value.IsTruthy();
                _rmLaterTo = value.TryGetValueAsString(out var rmTo) && rmTo.Length > 0 ? rmTo : null;
                break;
            default:
                throw new DMException($"Cannot set var \\"{varName}\\" on savefiles");
""", 1),
]
