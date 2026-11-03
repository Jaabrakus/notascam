using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.Loader;
using System.Text.Json;

// Executes the real published/patched client animation selector without a GUI,
// graphics device, game input, or a connection to the user's running world.
public class ProbeClock : DispatchProxy {
    public static TimeSpan Now;
    protected override object Invoke(MethodInfo method, object[] args) => method.Name == "get_CurTime"
        ? Now : method.ReturnType.IsValueType ? Activator.CreateInstance(method.ReturnType) : null;
}

public static class CheckMovement {
    static BindingFlags All = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;
    static Type Icon;
    static Type Resource;
    static Type Appearance;
    static object Clock;
    static object South;
    static MethodInfo Parse;
    static MethodInfo Select;
    static MethodInfo Move;
    static List<object> Results = new();

    static void Put(object obj, string name, object value) => obj.GetType().GetField(name, All).SetValue(obj, value);
    static object Get(object obj, string name) => obj.GetType().GetField(name, All).GetValue(obj);
    static object Description(string path) {
        using var stream = File.OpenRead(path);
        return Parse.Invoke(null, new object[] { stream });
    }
    static object NewIcon(object description, string state) {
        var obj = RuntimeHelpers.GetUninitializedObject(Icon);
        var dmi = RuntimeHelpers.GetUninitializedObject(Resource);
        Put(dmi, "Description", description);
        Put(obj, "_dmi", dmi);
        Put(obj, "_appearance", RuntimeHelpers.GetUninitializedObject(Appearance));
        Put(obj, "_iconState", state);
        Put(obj, "_direction", South);
        Put(obj, "<gameTiming>P", Clock);
        foreach (var name in new[] { "Overlays", "Underlays" }) {
            var field = Icon.GetField("<" + name + ">k__BackingField", All);
            field.SetValue(obj, Activator.CreateInstance(field.FieldType));
        }
        return obj;
    }
    static int Frame(object icon, string state, int milliseconds) {
        ProbeClock.Now = TimeSpan.FromMilliseconds(milliseconds);
        return (int)Select.Invoke(icon, new[] { (object)state, South });
    }
    static void Check(string name, bool passed, object details = null) {
        Results.Add(new { name, passed, details });
        Console.WriteLine((passed ? "PASS " : "FAIL ") + name);
    }
    public static int Main(string[] args) {
        var dirs = args[0].Split(Path.PathSeparator);
        AssemblyLoadContext.Default.Resolving += (context, name) => {
            var found = dirs.Select(d => Path.Combine(d, name.Name + ".dll")).FirstOrDefault(File.Exists);
            return found == null ? null : context.LoadFromAssemblyPath(Path.GetFullPath(found));
        };
        var client = Assembly.LoadFrom(Path.Combine(dirs[0], "OpenDreamClient.dll"));
        var shared = Assembly.LoadFrom(Path.Combine(dirs[0], "OpenDreamShared.dll"));
        Icon = client.GetType("OpenDreamClient.Rendering.DreamIcon", true);
        Resource = client.GetType("OpenDreamClient.Resources.ResourceTypes.DMIResource", true);
        Appearance = shared.GetType("OpenDreamShared.Dream.ImmutableAppearance", true);
        var parser = shared.GetType("OpenDreamShared.Resources.DMIParser", true);
        Parse = parser.GetMethod("ParseDMI", All);
        Select = Icon.GetMethods(All).Single(m => m.Name == "GetAnimationFrame" && m.GetParameters().Length == 2);
        Move = Icon.GetMethod("SetMovementActive", All);
        var timing = Icon.GetField("<gameTiming>P", All).FieldType;
        Clock = DispatchProxy.Create(timing, typeof(ProbeClock));
        South = Enum.ToObject(shared.GetType("OpenDreamShared.Dream.AtomDirection", true), 2);
        var specs = JsonSerializer.Deserialize<List<Dictionary<string, JsonElement>>>(File.ReadAllText(args[1]));
        foreach (var spec in specs) {
            var name = spec["name"].GetString(); var state = spec["state"].GetString();
            var movement = spec["movement"].GetBoolean();
            var description = Description(spec["path"].GetString());
            var parsed = description.GetType().GetMethod("GetStateOrDefault").Invoke(description, new[] { state });
            var flag = parsed.GetType().GetField("Movement", All);
            Check(name + " metadata", (flag != null && (bool)flag.GetValue(parsed)) == movement);
            var icon = NewIcon(description, state);
            var times = new[] { 50, 250, 450, 650, 850, 1050, 1250 };
            var idle = times.Select(t => Frame(icon, state, t)).ToArray();
            if (Move != null) Move.Invoke(icon, new object[] { true });
            var moving = times.Select(t => Frame(icon, state, t)).ToArray();
            if (Move != null) Move.Invoke(icon, new object[] { false });
            var stopped = times.Select(t => Frame(icon, state, t)).ToArray();
            Check(name + " idle-move-idle", movement
                ? idle.All(f => f == 0) && moving.Any(f => f != 0) && stopped.All(f => f == 0)
                : idle.Any(f => f != 0) && idle.SequenceEqual(moving) && idle.SequenceEqual(stopped), new { idle, moving, stopped });
            if (movement && Move != null) {
                var overlay = NewIcon(description, state); var underlay = NewIcon(description, state);
                ((IList)Get(icon, "<Overlays>k__BackingField")).Add(overlay);
                ((IList)Get(icon, "<Underlays>k__BackingField")).Add(underlay);
                Move.Invoke(icon, new object[] { true });
                var advancing = times.Any(t => Frame(overlay, state, t) != 0) && times.Any(t => Frame(underlay, state, t) != 0);
                Move.Invoke(icon, new object[] { false });
                Check(name + " child layers stop", advancing && times.All(t => Frame(overlay, state, t) == 0 && Frame(underlay, state, t) == 0));
                Put(icon, "_animationFrame", 2); Put(icon, "_animationComplete", true);
                Check(name + " completed walking returns idle", Frame(icon, state, 450) == 0);
                var stableDirections = true;
                foreach (var direction in new[] { 1, 2, 4, 8, 5, 6, 9, 10 }) {
                    var facing = Enum.ToObject(South.GetType(), direction);
                    Put(icon, "_direction", facing);
                    var before = times.Select(t => { ProbeClock.Now = TimeSpan.FromMilliseconds(t); return (int)Select.Invoke(icon, new[] { (object)state, facing }); }).ToArray();
                    Move.Invoke(icon, new object[] { true });
                    var walking = times.Select(t => { ProbeClock.Now = TimeSpan.FromMilliseconds(t); return (int)Select.Invoke(icon, new[] { (object)state, facing }); }).ToArray();
                    Move.Invoke(icon, new object[] { false });
                    var after = times.Select(t => { ProbeClock.Now = TimeSpan.FromMilliseconds(t); return (int)Select.Invoke(icon, new[] { (object)state, facing }); }).ToArray();
                    stableDirections &= before.All(f => f == 0) && walking.Any(f => f != 0) && after.All(f => f == 0) && Get(icon, "_direction").Equals(facing);
                }
                Check(name + " all cardinal/diagonal facings stable", stableDirections);
            }
            var exported = (string)description.GetType().GetMethod("ExportAsText").Invoke(description, null);
            var reparsed = parser.GetMethod("ParseDMIDescription", All).Invoke(null, new object[] { exported, (uint)(int)Get(description, "Width") * 64 });
            var again = reparsed.GetType().GetMethod("GetStateOrDefault").Invoke(reparsed, new[] { state });
            Check(name + " metadata text roundtrip", flag != null && (bool)flag.GetValue(again) == movement);
        }
        var json = JsonSerializer.Serialize(Results, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(args[2], json + "\n");
        return json.Contains("\"passed\": false") ? 1 : 0;
    }
}
