using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

public static class PatchContextClick {
    public static void Apply(ModuleDefinition module) {
        var item=module.GetType("OpenDreamClient.Input.ContextMenu.ContextMenuItem");
        var panel=item.BaseType.Resolve();
        var control=panel.Module.GetType("Robust.Client.UserInterface.Control");
        var guiArgs=control.Methods.Single(m=>m.Name=="KeyBindDown").Parameters[0].ParameterType.Resolve();
        var eventArgs=guiArgs.BaseType.Resolve();
        MethodDefinition Find(TypeDefinition t,string name) {
            while(t!=null) { var m=t.Methods.FirstOrDefault(m=>m.Name==name); if(m!=null)return m; t=t.BaseType?.Resolve(); }
            throw new Exception("Missing method "+name);
        }
        var function=Find(eventArgs,"get_Function");
        var keyType=function.ReturnType.Resolve();
        var engineKeys=keyType.Module.GetType("Robust.Shared.Input.EngineKeyFunctions");
        var uiClick=engineKeys.Fields.Single(f=>f.Name=="UIClick");
        var equals=keyType.Methods.Single(m=>m.Name=="op_Equality");
        var handle=Find(eventArgs,"Handle");
        var hasPoint=Find(control,"HasPoint");
        var rel=Find(guiArgs,"get_RelativePosition");
        var menuField=item.Fields.Single(f=>f.Name=="_menu");
        var setActive=menuField.FieldType.Resolve().Methods.Single(m=>m.Name=="SetActiveItem");
        foreach(var name in new[]{"KeyBindDown","KeyBindUp","ControlFocusExited"}) {
            if(Find(panel,name).DeclaringType.FullName!=control.FullName)
                throw new Exception("Review changed context row base handler: "+name);
        }
        if(item.Fields.Any(f=>f.Name=="_contextTapPressed"))
            throw new Exception("Context row click patch already applied");
        var pressed=new FieldDefinition("_contextTapPressed",FieldAttributes.Private,module.TypeSystem.Boolean);
        item.Fields.Add(pressed);
        foreach(var methodName in new[]{"KeyBindDown","KeyBindUp"}) {
            if(item.Methods.Any(m=>m.Name==methodName))throw new Exception("Already patched or changed item");
            var baseMethod=control.Methods.Single(m=>m.Name==methodName);
            var method=new MethodDefinition(methodName,MethodAttributes.Family|MethodAttributes.Virtual|MethodAttributes.HideBySig,module.TypeSystem.Void);
            method.Parameters.Add(new ParameterDefinition("args",ParameterAttributes.None,module.ImportReference(guiArgs)));
            item.Methods.Add(method);
            var il=method.Body.GetILProcessor();var done=il.Create(OpCodes.Ret);
            il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldarg_1);il.Emit(OpCodes.Call,module.ImportReference(baseMethod));
            il.Emit(OpCodes.Ldarg_1);il.Emit(OpCodes.Callvirt,module.ImportReference(function));il.Emit(OpCodes.Ldsfld,module.ImportReference(uiClick));
            il.Emit(OpCodes.Call,module.ImportReference(equals));il.Emit(OpCodes.Brfalse,done);
            il.Emit(OpCodes.Ldarg_1);il.Emit(OpCodes.Callvirt,module.ImportReference(handle));
            if(methodName=="KeyBindDown") {
                il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldc_I4_1);il.Emit(OpCodes.Stfld,pressed);
            } else {
                il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,pressed);il.Emit(OpCodes.Brfalse,done);
                il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldc_I4_0);il.Emit(OpCodes.Stfld,pressed);
                il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldarg_1);il.Emit(OpCodes.Callvirt,module.ImportReference(rel));
                il.Emit(OpCodes.Callvirt,module.ImportReference(hasPoint));il.Emit(OpCodes.Brfalse,done);
                // Hover styling stays owned by the unchanged enter/exit handlers.
                il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,menuField);il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Callvirt,setActive);
            }
            il.Append(done);
        }
        var focusBase=control.Methods.Single(m=>m.Name=="ControlFocusExited");
        var focusExit=new MethodDefinition("ControlFocusExited",MethodAttributes.Family|MethodAttributes.Virtual|MethodAttributes.HideBySig,module.TypeSystem.Void);
        item.Methods.Add(focusExit);
        var focusCode=focusExit.Body.GetILProcessor();
        focusCode.Emit(OpCodes.Ldarg_0);focusCode.Emit(OpCodes.Call,module.ImportReference(focusBase));
        focusCode.Emit(OpCodes.Ldarg_0);focusCode.Emit(OpCodes.Ldc_I4_0);focusCode.Emit(OpCodes.Stfld,pressed);
        focusCode.Emit(OpCodes.Ret);
        // Let the existing popup container place a submenu to the left when
        // the right edge has no room. Filtering and execution are unchanged.
        var owner=module.GetType("OpenDreamClient.Input.ContextMenu.ContextMenuPopup");
        var active=owner.Methods.Single(m=>m.Name=="SetActiveItem");
        var open=active.Body.Instructions.Single(i=>i.Operand is MethodReference m && m.Name=="Open");
        var openMethod=(MethodReference)open.Operand;
        var globalPosition=Find(control,"get_GlobalPosition");
        var nullableVector=(GenericInstanceType)openMethod.Parameters[1].ParameterType;
        var nullableCtor=module.ImportReference(nullableVector.Resolve().Methods.Single(m=>m.IsConstructor && m.Parameters.Count==1));
        nullableCtor.DeclaringType=module.ImportReference(nullableVector);
        var popup=new VariableDefinition(openMethod.DeclaringType);
        var box=new VariableDefinition(openMethod.Parameters[0].ParameterType);
        var altUp=new VariableDefinition(openMethod.Parameters[2].ParameterType);
        active.Body.InitLocals=true;active.Body.Variables.Add(popup);active.Body.Variables.Add(box);active.Body.Variables.Add(altUp);
        var code=active.Body.GetILProcessor();
        void Before(Instruction i)=>code.InsertBefore(open,i);
        Before(code.Create(OpCodes.Stloc,altUp));Before(code.Create(OpCodes.Pop));Before(code.Create(OpCodes.Stloc,box));Before(code.Create(OpCodes.Stloc,popup));
        Before(code.Create(OpCodes.Ldloc,popup));Before(code.Create(OpCodes.Ldloc,box));
        Before(code.Create(OpCodes.Ldarg_1));Before(code.Create(OpCodes.Callvirt,module.ImportReference(globalPosition)));
        Before(code.Create(OpCodes.Newobj,nullableCtor));Before(code.Create(OpCodes.Ldloc,altUp));
        Console.WriteLine("Private context row click candidate: matching UIClick down/in-row release activates existing submenu; hover and verbs unchanged.");
    }
}
