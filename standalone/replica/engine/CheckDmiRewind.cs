using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.Loader;
using System.Text.Json;

// Audit-only invocation of the actual client selector. No engine edits, GUI,
// live profile, fake artwork or animation algorithm replacement.
public class RewindClock : DispatchProxy {
    public static TimeSpan Now;
    protected override object Invoke(MethodInfo method, object[] args) => method.Name == "get_CurTime"
        ? Now : method.ReturnType.IsValueType ? Activator.CreateInstance(method.ReturnType) : null;
}
public static class CheckDmiRewind {
    static BindingFlags All = BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.Static;
    static object Get(object obj,string name) => obj.GetType().GetField(name,All).GetValue(obj);
    static void Put(object obj,string name,object value) => obj.GetType().GetField(name,All).SetValue(obj,value);
    public static int Main(string[] args) {
        var paths=args[0].Split(Path.PathSeparator);
        AssemblyLoadContext.Default.Resolving+=(context,name)=> {
            var found=paths.Select(p=>Path.Combine(p,name.Name+".dll")).FirstOrDefault(File.Exists);
            return found==null?null:context.LoadFromAssemblyPath(Path.GetFullPath(found));
        };
        var client=Assembly.LoadFrom(Path.Combine(paths[0],"OpenDreamClient.dll"));
        var shared=Assembly.LoadFrom(Path.Combine(paths[0],"OpenDreamShared.dll"));
        var parser=shared.GetType("OpenDreamShared.Resources.DMIParser",true);
        var iconType=client.GetType("OpenDreamClient.Rendering.DreamIcon",true);
        var resourceType=client.GetType("OpenDreamClient.Resources.ResourceTypes.DMIResource",true);
        var appearanceType=shared.GetType("OpenDreamShared.Dream.ImmutableAppearance",true);
        var directionType=shared.GetType("OpenDreamShared.Dream.AtomDirection",true);
        var selector=iconType.GetMethods(All).Single(m=>m.Name=="GetAnimationFrame"&&m.GetParameters().Length==2);
        var clock=DispatchProxy.Create(iconType.GetField("<gameTiming>P",All).FieldType,typeof(RewindClock));
        var specs=JsonSerializer.Deserialize<List<Dictionary<string,JsonElement>>>(File.ReadAllText(args[1]));
        var output=new List<object>();
        foreach(var spec in specs) {
            using var stream=File.OpenRead(spec["path"].GetString());
            var description=parser.GetMethod("ParseDMI",All).Invoke(null,new object[]{stream});
            var stateName=spec["state"].GetString();
            var state=description.GetType().GetMethod("GetStateOrDefault").Invoke(description,new object[]{stateName});
            var facing=Enum.ToObject(directionType,2);
            var frames=(Array)state.GetType().GetMethods().Single(m=>m.Name=="GetFrames"&&m.GetParameters().Length==1).Invoke(state,new[]{facing});
            var icon=RuntimeHelpers.GetUninitializedObject(iconType);
            var resource=RuntimeHelpers.GetUninitializedObject(resourceType);
            Put(resource,"Description",description);Put(icon,"_dmi",resource);
            Put(icon,"_appearance",RuntimeHelpers.GetUninitializedObject(appearanceType));
            Put(icon,"_iconState",stateName);Put(icon,"_direction",facing);Put(icon,"<gameTiming>P",clock);
            foreach(var name in new[]{"Overlays","Underlays"}){
                var field=iconType.GetField("<"+name+">k__BackingField",All);field.SetValue(icon,Activator.CreateInstance(field.FieldType));
            }
            iconType.GetMethod("SetMovementActive",All).Invoke(icon,new object[]{spec["moving"].GetBoolean()});
            object flick=null;
            MethodInfo flickSelector=null;
            if(spec.TryGetValue("flick",out var useFlick)&&useFlick.GetBoolean()) {
                var flickType=client.GetType("OpenDreamClient.Rendering.ClientAppearanceSystem+Flick",true);
                flick=Activator.CreateInstance(flickType,new object[]{resource,stateName,0L});
                flickSelector=flickType.GetMethod("GetAnimationFrame",All);
            }
            var samples=new List<object>();
            foreach(var value in spec["times_ms"].EnumerateArray()) {
                var time=value.GetInt32();RewindClock.Now=TimeSpan.FromMilliseconds(time);
                var index=flick==null?(int)selector.Invoke(icon,new object[]{stateName,facing}):(int)flickSelector.Invoke(flick,new[]{clock});
                var frame=index<0?null:frames.GetValue(index);
                samples.Add(new{time_ms=time,index,x=frame==null?-1:(int)Get(frame,"X"),y=frame==null?-1:(int)Get(frame,"Y")});
            }
            output.Add(new{name=spec["name"].GetString(),loop=Get(state,"Loop"),rewind=Get(state,"Rewind"),
                movement=Get(state,"Movement"),frame_count=frames.Length,width=Get(description,"Width"),height=Get(description,"Height"),
                exported=description.GetType().GetMethod("ExportAsText").Invoke(description,null),samples});
        }
        File.WriteAllText(args[2],JsonSerializer.Serialize(output,new JsonSerializerOptions{WriteIndented=true})+"\n");return 0;
    }
}
