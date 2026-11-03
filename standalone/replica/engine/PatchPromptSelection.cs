using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

// Required-choice prompts must keep one row selected. A repeated tap selects
// that same choice; it does not turn OK into an unexplained no-op. Only the
// ListPrompt instance subscribes; global ItemList and nullable lists are intact.
public static class PatchPromptSelection {
    public static void Apply(ModuleDefinition module) {
        var prompt=module.GetType("OpenDreamClient.Interface.Prompts.ListPrompt");
        if(prompt.Methods.Any(m=>m.Name=="KeepRequiredSelection"))throw new InvalidOperationException("Prompt selection already patched");
        var field=prompt.Fields.Single(f=>f.Name=="_itemList");
        var list=field.FieldType.Resolve();
        var add=list.Methods.Single(m=>m.Name=="add_OnItemDeselected");
        var delegateType=(GenericInstanceType)add.Parameters[0].ParameterType;
        var eventType=delegateType.GenericArguments[0].Resolve();
        var index=eventType.Fields.Single(f=>f.Name=="ItemIndex");
        var getSelected=list.Methods.Single(m=>m.Name=="GetSelected");
        var getItem=list.Methods.Single(m=>m.Name=="get_IndexItem");
        var item=getItem.ReturnType.Resolve();
        var setSelected=item.Methods.Single(m=>m.Name=="set_Selected");
        var any=new GenericInstanceMethod(module.ImportReference(typeof(Enumerable).GetMethods().Single(m=>m.Name=="Any" && m.GetParameters().Length==1)));
        any.GenericArguments.Add(module.ImportReference(item));
        var helper=new MethodDefinition("KeepRequiredSelection",MethodAttributes.Private|MethodAttributes.HideBySig,module.TypeSystem.Void);
        helper.Parameters.Add(new ParameterDefinition("args",ParameterAttributes.None,module.ImportReference(eventType)));
        prompt.Methods.Add(helper);
        var il=helper.Body.GetILProcessor();var done=il.Create(OpCodes.Ret);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,field);il.Emit(OpCodes.Callvirt,module.ImportReference(getSelected));
        il.Emit(OpCodes.Call,any);il.Emit(OpCodes.Brtrue,done);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,field);il.Emit(OpCodes.Ldarg_1);il.Emit(OpCodes.Ldfld,module.ImportReference(index));
        il.Emit(OpCodes.Callvirt,module.ImportReference(getItem));il.Emit(OpCodes.Ldc_I4_1);il.Emit(OpCodes.Callvirt,module.ImportReference(setSelected));
        il.Append(done);
        var ctor=prompt.Methods.Single(m=>m.IsConstructor);
        var canCancel=ctor.Parameters.Single(p=>p.Name=="canCancel");
        var delegateCtor=module.ImportReference(delegateType.Resolve().Methods.Single(m=>m.IsConstructor && m.Parameters.Count==2));
        delegateCtor.DeclaringType=module.ImportReference(delegateType);
        var code=ctor.Body.GetILProcessor();
        foreach(var ret in ctor.Body.Instructions.Where(i=>i.OpCode==OpCodes.Ret).ToArray()) {
            void Before(Instruction instruction)=>code.InsertBefore(ret,instruction);
            Before(code.Create(OpCodes.Ldarg,canCancel));Before(code.Create(OpCodes.Brtrue,ret));
            Before(code.Create(OpCodes.Ldarg_0));Before(code.Create(OpCodes.Ldfld,field));
            Before(code.Create(OpCodes.Ldarg_0));Before(code.Create(OpCodes.Ldftn,helper));
            Before(code.Create(OpCodes.Newobj,delegateCtor));Before(code.Create(OpCodes.Callvirt,module.ImportReference(add)));
        }
    }
}
