using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

// Larger native prompt targets. This changes OpenDream prompt construction and
// its own ItemList stylesheet, never Robust's global control implementation.
public static class PatchPromptTargets {
    public static void Apply(ModuleDefinition module) {
        var prompt=module.GetType("OpenDreamClient.Interface.Prompts.PromptWindow");
        var control=prompt.BaseType.Resolve().BaseType.Resolve();
        if(control.FullName!="Robust.Client.UserInterface.Control")throw new Exception("Unexpected prompt base type");
        var client=control.Module;
        MethodReference Ref(TypeDefinition t,string name,int count)=>module.ImportReference(t.Methods.Single(m=>m.Name==name&&m.Parameters.Count==count));
        var setHeight=Ref(control,"set_MinHeight",1);var setWidth=Ref(control,"set_MinWidth",1);
        // Prompt buttons only; their callbacks, labels and response values stay.
        var create=prompt.Methods.Single(m=>m.Name=="CreateButton");
        var button=create.Body.Variables.Single(v=>v.VariableType.FullName=="Robust.Client.UserInterface.Controls.Button");
        var body=create.Body.GetILProcessor();
        foreach(var ret in create.Body.Instructions.Where(i=>i.OpCode==OpCodes.Ret).ToArray()) {
            body.InsertBefore(ret,body.Create(OpCodes.Ldloc,button));body.InsertBefore(ret,body.Create(OpCodes.Ldc_R4,72f));body.InsertBefore(ret,body.Create(OpCodes.Callvirt,setWidth));
            body.InsertBefore(ret,body.Create(OpCodes.Ldloc,button));body.InsertBefore(ret,body.Create(OpCodes.Ldc_R4,44f));body.InsertBefore(ret,body.Create(OpCodes.Callvirt,setHeight));
        }
        // Text and numeric entry have the same minimum touch height.
        var input=module.GetType("OpenDreamClient.Interface.Prompts.InputWindow");
        var set=input.Methods.Single(m=>m.Name=="SetPromptControl");
        var line=client.GetType("Robust.Client.UserInterface.Controls.LineEdit");
        var helper=new MethodDefinition("SizePromptEntry",MethodAttributes.Private|MethodAttributes.Static,module.TypeSystem.Void);
        helper.Parameters.Add(new ParameterDefinition("control",ParameterAttributes.None,module.ImportReference(control)));
        input.Methods.Add(helper);var il=helper.Body.GetILProcessor();var done=il.Create(OpCodes.Ret);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Isinst,module.ImportReference(line));il.Emit(OpCodes.Brfalse,done);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldc_R4,44f);il.Emit(OpCodes.Callvirt,setHeight);il.Append(done);
        var setIl=set.Body.GetILProcessor();var first=set.Body.Instructions[0];setIl.InsertBefore(first,setIl.Create(OpCodes.Ldarg_1));setIl.InsertBefore(first,setIl.Create(OpCodes.Call,helper));
        // OpenDream currently uses ItemList only for its native list prompts.
        // Preserve all existing colors, horizontal padding and font properties;
        // replace just vertical content margins in its three row backgrounds.
        var sheet=module.GetType("OpenDreamClient.Interface.DreamStylesheet");
        var style=client.GetType("Robust.Client.Graphics.StyleBox");
        var row=new MethodDefinition("SizePromptRow",MethodAttributes.Private|MethodAttributes.Static,module.TypeSystem.Object);
        row.Parameters.Add(new ParameterDefinition("style",ParameterAttributes.None,module.TypeSystem.Object));sheet.Methods.Add(row);
        var ri=row.Body.GetILProcessor();
        var nullable=module.ImportReference(typeof(float?).GetConstructor(new[]{typeof(float)}));
        foreach(var name in new[]{"set_ContentMarginTopOverride","set_ContentMarginBottomOverride"}) {
            ri.Emit(OpCodes.Ldarg_0);ri.Emit(OpCodes.Castclass,module.ImportReference(style));ri.Emit(OpCodes.Ldc_R4,12f);ri.Emit(OpCodes.Newobj,nullable);ri.Emit(OpCodes.Callvirt,Ref(style,name,1));
        }
        ri.Emit(OpCodes.Ldarg_0);ri.Emit(OpCodes.Ret);
        var ctor=sheet.Methods.Single(m=>m.Name=="Make");var code=ctor.Body.GetILProcessor();
        foreach(var key in new[]{"item-background","selected-item-background","disabled-item-background"}) {
            var start=ctor.Body.Instructions.Single(i=>i.OpCode==OpCodes.Ldstr&&(string)i.Operand==key);
            var call=start.Next;
            while(call!=null&&!(call.Operand is MethodReference m&&m.Name=="Prop"))call=call.Next;
            if(call==null)throw new Exception("Missing row style property "+key);
            var prop=(MethodReference)call.Operand;
            if(prop.Parameters.Last().ParameterType.FullName!="System.Object")throw new Exception("Changed style property signature");
            code.InsertBefore(call,code.Create(OpCodes.Call,row));
        }
        // Four choices fit without scrolling; longer original menus remain
        // bounded with the same ItemList scrolling and choice indexes.
        var list=module.GetType("OpenDreamClient.Interface.Prompts.ListPrompt").Methods.Single(m=>m.IsConstructor);
        var hundred=list.Body.Instructions.Single(i=>(i.OpCode==OpCodes.Ldc_I4_S||i.OpCode==OpCodes.Ldc_I4)&&Convert.ToInt32(i.Operand)==100);
        hundred.OpCode=OpCodes.Ldc_I4;hundred.Operand=140;
        var twentyFour=list.Body.Instructions.Single(i=>(i.OpCode==OpCodes.Ldc_I4_S||i.OpCode==OpCodes.Ldc_I4)&&Convert.ToInt32(i.Operand)==24);
        twentyFour.OpCode=OpCodes.Ldc_I4;twentyFour.Operand=48;
        var max=list.Body.Instructions.Single(i=>i.Operand is MethodReference m&&m.Name=="get_MinWidth");
        if(max.Previous.OpCode!=OpCodes.Ldarg_0)throw new Exception("Unexpected ListPrompt clamp");
        max.Previous.OpCode=OpCodes.Nop;max.OpCode=OpCodes.Ldc_R4;max.Operand=400f;
        Console.WriteLine("Patched native prompt buttons/entries to44px and list row margins; original response routes unchanged");
    }
}
