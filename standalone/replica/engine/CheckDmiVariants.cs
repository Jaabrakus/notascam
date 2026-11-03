using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.Loader;
using System.Text.Json;

// Read-only probe of actual installed shared parser and client frame selector.
// No graphics context, user input, normal game profile, or engine replacement.
public class VariantClock : DispatchProxy {
    public static TimeSpan Now;
    protected override object Invoke(MethodInfo method, object[] args) => method.Name == "get_CurTime"
        ? Now : method.ReturnType.IsValueType ? Activator.CreateInstance(method.ReturnType) : null;
}

public static class CheckDmiVariants {
    static BindingFlags All = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;
    static object Get(object obj, string field) => obj.GetType().GetField(field, All).GetValue(obj);
    static void Put(object obj, string field, object value) => obj.GetType().GetField(field, All).SetValue(obj, value);

    public static int Main(string[] args) {
        var dirs = args[0].Split(Path.PathSeparator);
        AssemblyLoadContext.Default.Resolving += (context, name) => {
            var found = dirs.Select(d => Path.Combine(d, name.Name + ".dll")).FirstOrDefault(File.Exists);
            return found == null ? null : context.LoadFromAssemblyPath(Path.GetFullPath(found));
        };
        var client = Assembly.LoadFrom(Path.Combine(dirs[0], "OpenDreamClient.dll"));
        var shared = Assembly.LoadFrom(Path.Combine(dirs[0], "OpenDreamShared.dll"));
        var parser = shared.GetType("OpenDreamShared.Resources.DMIParser", true);
        var iconType = client.GetType("OpenDreamClient.Rendering.DreamIcon", true);
        var resourceType = client.GetType("OpenDreamClient.Resources.ResourceTypes.DMIResource", true);
        var appearanceType = shared.GetType("OpenDreamShared.Dream.ImmutableAppearance", true);
        var directionType = shared.GetType("OpenDreamShared.Dream.AtomDirection", true);
        var robust=Assembly.Load("Robust.Client");
        var dummyType=robust.GetTypes().Single(t=>t.Name=="DummyTexture");
        var dummyCtor=dummyType.GetConstructors(All).Single();
        var sizeType=dummyCtor.GetParameters()[0].ParameterType;
        var renderedType=resourceType.GetNestedType("State",All);
        var select = iconType.GetMethods(All).Single(m => m.Name == "GetAnimationFrame" && m.GetParameters().Length == 2);
        var move = iconType.GetMethod("SetMovementActive", All);
        var clock = DispatchProxy.Create(iconType.GetField("<gameTiming>P", All).FieldType, typeof(VariantClock));
        var cases = JsonSerializer.Deserialize<List<Dictionary<string, JsonElement>>>(File.ReadAllText(args[1]));
        var results = new List<object>();
        foreach (var spec in cases) {
            var stateName = spec["state"].GetString();
            using var stream = File.OpenRead(spec["path"].GetString());
            var description = parser.GetMethod("ParseDMI", All).Invoke(null, new object[] {stream});
            var state = description.GetType().GetMethod("GetStateOrDefault").Invoke(description, new object[] {stateName});
            var getFrames = state.GetType().GetMethods().Single(m => m.Name == "GetFrames" && m.GetParameters().Length == 1);
            var output = new List<object>();
            var textureSize=Activator.CreateInstance(sizeType,new object[]{spec["sheet_width"].GetInt32(),spec["sheet_height"].GetInt32()});
            var texture=dummyCtor.Invoke(new[]{textureSize});
            foreach (var direction in new[] {2,1,4,8,6,10,5,9}) {
                var facing = Enum.ToObject(directionType, direction);
                var icon = RuntimeHelpers.GetUninitializedObject(iconType);
                var resource = RuntimeHelpers.GetUninitializedObject(resourceType);
                Put(resource, "Description", description);
                var cacheField=resourceType.GetField("_states",All);
                cacheField.SetValue(resource,Activator.CreateInstance(cacheField.FieldType));
                var getDict=resourceType.GetMethod("GetVariantStates",All);
                var allGetter=description.GetType().GetMethod("GetAllStates");
                var entries=(IDictionary)(allGetter==null?Get(description,"States"):allGetter.Invoke(description,null));
                foreach(var entry in entries.Values){
                    var cache=(IDictionary)(getDict==null?cacheField.GetValue(resource):getDict.Invoke(resource,new[]{Get(entry,"Movement")}));
                    var entryName=(string)Get(entry,"Name");
                    if(!cache.Contains(entryName))cache.Add(entryName,Activator.CreateInstance(renderedType,new[]{texture,entry,Get(description,"Width"),Get(description,"Height")}));
                }
                Put(icon, "_dmi", resource);
                Put(icon, "_appearance", RuntimeHelpers.GetUninitializedObject(appearanceType));
                Put(icon, "_iconState", stateName);
                Put(icon, "_direction", facing);
                Put(icon, "<gameTiming>P", clock);
                foreach (var name in new[] {"Overlays", "Underlays"}) {
                    var field = iconType.GetField("<" + name + ">k__BackingField", All);
                    field.SetValue(icon, Activator.CreateInstance(field.FieldType));
                }
                foreach (var phase in new[] {"idle", "walking", "stopped"}) {
                    move.Invoke(icon, new object[] {phase == "walking"});
                    var resolver=description.GetType().GetMethod("GetStateForMovement");
                    var selected=resolver==null?state:resolver.Invoke(description,new object[]{stateName,phase=="walking"});
                    var frames=(Array)getFrames.Invoke(selected,new[]{facing});
                    foreach (var time in new[] {50,150,250,350,450,550,650}) {
                        VariantClock.Now = TimeSpan.FromMilliseconds(time);
                        var index = (int)select.Invoke(icon, new object[] {stateName, facing});
                        var frame = frames.GetValue(index);
                        var textureResolver=resourceType.GetMethod("GetStateForMovement",All);
                        var rendered=textureResolver==null?resourceType.GetMethod("GetState",All).Invoke(resource,new object[]{stateName}):textureResolver.Invoke(resource,new object[]{stateName,phase=="walking"});
                        var atlasFrames=(Array)renderedType.GetMethod("GetFrames").Invoke(rendered,new[]{facing});
                        var atlas=atlasFrames.GetValue(index);var region=atlas.GetType().GetProperty("SubRegion").GetValue(atlas);
                        var textureX=Convert.ToInt32(region.GetType().GetProperty("Left").GetValue(region));
                        var textureY=Convert.ToInt32(region.GetType().GetProperty("Top").GetValue(region));
                        output.Add(new {phase, direction, time, index, x=(int)Get(frame,"X"), y=(int)Get(frame,"Y"), textureX,textureY,movement=(bool)Get(selected,"Movement")});
                    }
                }
            }
            results.Add(new {name=spec["name"].GetString(), width=(int)Get(description,"Width"), height=(int)Get(description,"Height"),
                selectedMovement=(bool)Get(state,"Movement"), selectedFrameCount=(int)state.GetType().GetProperty("FrameCount").GetValue(state),
                exported=(string)description.GetType().GetMethod("ExportAsText").Invoke(description,null), observations=output});
        }
        File.WriteAllText(args[2],JsonSerializer.Serialize(results,new JsonSerializerOptions {WriteIndented=true})+"\n");
        return 0;
    }
}
