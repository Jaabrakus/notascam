using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

// Preserve DMI's movement-only flag and let the existing transform glide own
// its playback lifetime. Normal (movement=0) animations keep their old clock.
public static class PatchMovement {
    static void Before(MethodDefinition method, Instruction anchor, params Instruction[] instructions) {
        var il = method.Body.GetILProcessor();
        foreach (var instruction in instructions) il.InsertBefore(anchor, instruction);
        // Branches to the anchor must also run the inserted lifecycle action.
        foreach (var instruction in method.Body.Instructions.Except(instructions)) {
            if (instruction.Operand == anchor) instruction.Operand = instructions[0];
        }
    }

    static void LongBranches(MethodDefinition method) {
        foreach (var instruction in method.Body.Instructions) {
            var code = instruction.OpCode;
            if (code.OperandType != OperandType.ShortInlineBrTarget) continue;
            instruction.OpCode = code.Code switch {
                Code.Br_S => OpCodes.Br, Code.Brfalse_S => OpCodes.Brfalse,
                Code.Brtrue_S => OpCodes.Brtrue, Code.Beq_S => OpCodes.Beq,
                Code.Bne_Un_S => OpCodes.Bne_Un, Code.Bge_S => OpCodes.Bge,
                Code.Bge_Un_S => OpCodes.Bge_Un, Code.Bgt_S => OpCodes.Bgt,
                Code.Bgt_Un_S => OpCodes.Bgt_Un, Code.Ble_S => OpCodes.Ble,
                Code.Ble_Un_S => OpCodes.Ble_Un, Code.Blt_S => OpCodes.Blt,
                Code.Blt_Un_S => OpCodes.Blt_Un, Code.Leave_S => OpCodes.Leave,
                _ => throw new InvalidOperationException("Unexpected short branch " + code)
            };
        }
    }

    public static void Shared(ModuleDefinition module) {
        var parser = module.Types.Single(t => t.FullName == "OpenDreamShared.Resources.DMIParser");
        var state = parser.NestedTypes.Single(t => t.Name == "ParsedDMIState");
        if (state.Fields.Any(f => f.Name == "Movement")) throw new InvalidOperationException("Already patched shared DMI parser");
        var movement = new FieldDefinition("Movement", FieldAttributes.Public, module.TypeSystem.Boolean);
        state.Fields.Add(movement);
        var parse = parser.Methods.Single(m => m.Name == "ParseDMIDescription");
        var match = parse.Body.Instructions.Single(i => i.OpCode == OpCodes.Ldstr && (string)i.Operand == "movement");
        var branch = match.Next.Next;
        if (branch.OpCode != OpCodes.Brtrue && branch.OpCode != OpCodes.Brtrue_S)
            throw new InvalidOperationException("Unexpected movement metadata branch");
        var nextLine = (Instruction)branch.Operand;
        var current = parse.Body.Variables.Single(v => v.VariableType.FullName == state.FullName);
        // Reuse the value local used by the adjacent rewind parser.
        var rewindStore = parse.Body.Instructions.Single(i => i.OpCode == OpCodes.Stfld && i.Operand is FieldReference f && f.Name == "Rewind");
        // The String.Trim result immediately after '=' is stored into this local.
        var valueLoad = rewindStore;
        while (!(valueLoad.OpCode == OpCodes.Call && valueLoad.Operand is MethodReference method && method.Name == "Parse" && method.DeclaringType.FullName == "System.Int32")) valueLoad = valueLoad.Previous;
        valueLoad = valueLoad.Previous.Previous;
        if (valueLoad.Operand is not VariableDefinition value || value.VariableType.FullName != "System.String")
            throw new InvalidOperationException("Unexpected DMI value local");
        var il = parse.Body.GetILProcessor();
        var start = il.Create(OpCodes.Ldloc, current);
        il.Append(start); il.Emit(OpCodes.Brfalse, nextLine);
        il.Emit(OpCodes.Ldloc, current); il.Emit(OpCodes.Ldloc, value);
        il.Emit(OpCodes.Ldstr, "1");
        il.Emit(OpCodes.Call, module.ImportReference(typeof(string).GetMethod("op_Equality", new[] { typeof(string), typeof(string) })));
        il.Emit(OpCodes.Stfld, movement); il.Emit(OpCodes.Br, nextLine);
        branch.Operand = start;
        LongBranches(parse);
        var export = state.Methods.Single(m => m.Name == "ExportAsText");
        var ret = export.Body.Instructions.Last(i => i.OpCode == OpCodes.Ret);
        var append = module.ImportReference(typeof(System.Text.StringBuilder).GetMethod("AppendLine", new[] { typeof(string) }));
        // No branch targets the final return in this upstream method; do not
        // redirect our own false branch back into this added block.
        var body = export.Body.GetILProcessor();
        foreach (var i in new[] { body.Create(OpCodes.Ldarg_0), body.Create(OpCodes.Ldfld, movement), body.Create(OpCodes.Brfalse, ret),
            body.Create(OpCodes.Ldarg_1), body.Create(OpCodes.Ldstr, "\tmovement = 1"), body.Create(OpCodes.Callvirt, append), body.Create(OpCodes.Pop) }) body.InsertBefore(ret, i);
        // Existing branches to ret skip optional metadata, so redirect them to
        // the movement check, excluding its own branch.
        var check = ret.Previous.Previous.Previous.Previous.Previous.Previous.Previous;
        foreach (var i in export.Body.Instructions.Where(i => i.Operand == ret && i != check.Next.Next).ToArray()) i.Operand = check;
        LongBranches(export);
    }

    public static void Client(ModuleDefinition module) {
        var icon = module.Types.Single(t => t.FullName == "OpenDreamClient.Rendering.DreamIcon");
        var active = new FieldDefinition("_movementActive", FieldAttributes.Private, module.TypeSystem.Boolean);
        icon.Fields.Add(active);
        var dirty = icon.Methods.Single(m => m.Name == "DirtyTexture");
        var set = new MethodDefinition("SetMovementActive", MethodAttributes.Public | MethodAttributes.HideBySig, module.TypeSystem.Void);
        set.Parameters.Add(new ParameterDefinition("moving", ParameterAttributes.None, module.TypeSystem.Boolean));
        icon.Methods.Add(set);
        var il = set.Body.GetILProcessor();
        var children = il.Create(OpCodes.Nop);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldfld, active); il.Emit(OpCodes.Ldarg_1); il.Emit(OpCodes.Beq, children);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldarg_1); il.Emit(OpCodes.Stfld, active);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Call, dirty);
        il.Append(children);
        var index = new VariableDefinition(module.TypeSystem.Int32);
        set.Body.Variables.Add(index); set.Body.InitLocals = true;
        foreach (var name in new[] { "Overlays", "Underlays" }) {
            var field = icon.Fields.Single(f => f.Name == "<" + name + ">k__BackingField");
            var list = field.FieldType.Resolve();
            MethodReference Bound(string methodName) {
                var definition = module.ImportReference(list.Methods.Single(m => m.Name == methodName));
                var method = new MethodReference(definition.Name, definition.ReturnType, field.FieldType) { HasThis = true };
                foreach (var p in definition.Parameters) method.Parameters.Add(new ParameterDefinition(p.ParameterType));
                return method;
            }
            var count = Bound("get_Count"); var item = Bound("get_Item");
            var test = il.Create(OpCodes.Ldloc, index); var loop = il.Create(OpCodes.Ldarg_0);
            il.Emit(OpCodes.Ldc_I4_0); il.Emit(OpCodes.Stloc, index); il.Emit(OpCodes.Br, test);
            il.Append(loop); il.Emit(OpCodes.Ldfld, field); il.Emit(OpCodes.Ldloc, index); il.Emit(OpCodes.Callvirt, item);
            il.Emit(OpCodes.Ldarg_1); il.Emit(OpCodes.Call, set);
            il.Emit(OpCodes.Ldloc, index); il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Add); il.Emit(OpCodes.Stloc, index);
            il.Append(test); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldfld, field); il.Emit(OpCodes.Callvirt, count); il.Emit(OpCodes.Blt, loop);
        }
        il.Emit(OpCodes.Ret);
        // Equipment rebuilt during a glide inherits its parent's movement
        // immediately, including before its asynchronous DMI load completes.
        var updateIcon = icon.Methods.Single(m => m.Name == "UpdateIcon");
        foreach (var ret in updateIcon.Body.Instructions.Where(i => i.OpCode == OpCodes.Ret).ToArray())
            Before(updateIcon, ret, Instruction.Create(OpCodes.Ldarg_0), Instruction.Create(OpCodes.Ldarg_0),
                Instruction.Create(OpCodes.Ldfld, active), Instruction.Create(OpCodes.Call, set));
        LongBranches(updateIcon);

        var frame = icon.Methods.Single(m => m.Name == "GetAnimationFrame" && m.Parameters.Count == 2);
        var stateLocal = frame.Body.Variables.Single(v => v.VariableType.Name == "ParsedDMIState");
        var stateType = stateLocal.VariableType.Resolve();
        var movement = module.ImportReference(stateType.Fields.Single(f => f.Name == "Movement"));
        var animationFrame = icon.Fields.Single(f => f.Name == "_animationFrame");
        var completed = icon.Fields.Single(f => f.Name == "_animationComplete");
        // Even a completed finite movement animation must return to idle.
        // Move its early-return guard below the stationary movement check.
        var completeGuard = frame.Body.Instructions.Single(i => i.OpCode == OpCodes.Ldfld && i.Operand == completed);
        completeGuard.Previous.OpCode = OpCodes.Nop;
        completeGuard.OpCode = OpCodes.Nop; completeGuard.Operand = null;
        completeGuard.Next.OpCode = OpCodes.Br;
        var freeze = new MethodDefinition("FreezeStationaryMovement", MethodAttributes.Private, module.TypeSystem.Boolean);
        freeze.Parameters.Add(new ParameterDefinition("state", ParameterAttributes.None, stateLocal.VariableType));
        icon.Methods.Add(freeze);
        il = freeze.Body.GetILProcessor();
        var no = il.Create(OpCodes.Ldc_I4_0); var reset = il.Create(OpCodes.Ldarg_0);
        il.Emit(OpCodes.Ldarg_1); il.Emit(OpCodes.Brfalse, no);
        il.Emit(OpCodes.Ldarg_1); il.Emit(OpCodes.Ldfld, movement); il.Emit(OpCodes.Brfalse, no);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldfld, active); il.Emit(OpCodes.Brtrue, no);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldfld, animationFrame); il.Emit(OpCodes.Brfalse, reset);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Call, dirty);
        il.Append(reset); il.Emit(OpCodes.Ldc_I4_0); il.Emit(OpCodes.Stfld, animationFrame);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldc_I4_0); il.Emit(OpCodes.Stfld, completed);
        il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Ret); il.Append(no); il.Emit(OpCodes.Ret);
        // Reuse the existing parsed state without touching normal animations.
        var store = frame.Body.Instructions.Single(i => i.OpCode == OpCodes.Stloc_0 || (i.OpCode == OpCodes.Stloc && i.Operand == stateLocal));
        if (stateLocal.Index != 0) throw new InvalidOperationException("Unexpected frame state local");
        var anchor = store.Next;
        il = frame.Body.GetILProcessor();
        var guard = il.Create(OpCodes.Ldarg_0);
        foreach (var i in new[] { il.Create(OpCodes.Ldarg_0), il.Create(OpCodes.Ldloc, stateLocal), il.Create(OpCodes.Call, freeze),
            il.Create(OpCodes.Brfalse, guard), il.Create(OpCodes.Ldc_I4_0), il.Create(OpCodes.Ret),
            guard, il.Create(OpCodes.Ldfld, completed), il.Create(OpCodes.Brfalse, anchor),
            il.Create(OpCodes.Ldarg_0), il.Create(OpCodes.Ldfld, animationFrame), il.Create(OpCodes.Ret) }) il.InsertBefore(anchor, i);
        LongBranches(frame);

        var glideSystem = module.Types.Single(t => t.FullName == "OpenDreamClient.Rendering.AtomGlideSystem");
        var glide = glideSystem.NestedTypes.Single(t => t.Name == "Glide");
        var spriteField = glide.Fields.Single(f => f.Name == "Sprite");
        var spriteType = spriteField.FieldType.Resolve();
        var getIcon = spriteType.Methods.Single(m => m.Name == "get_Icon");
        var update = glideSystem.Methods.Single(m => m.Name == "FrameUpdate");
        var current = update.Body.Variables.Single(v => v.VariableType == glide);
        Instruction[] SetGlide(bool moving) => new[] { Instruction.Create(OpCodes.Ldloc, current), Instruction.Create(OpCodes.Ldfld, spriteField),
            Instruction.Create(OpCodes.Callvirt, getIcon), Instruction.Create(moving ? OpCodes.Ldc_I4_1 : OpCodes.Ldc_I4_0), Instruction.Create(OpCodes.Call, set) };
        var currentStore = update.Body.Instructions.Single(i => i.OpCode == OpCodes.Stloc_1);
        Before(update, currentStore.Next, SetGlide(true));
        var removals = update.Body.Instructions.Where(i => i.OpCode == OpCodes.Call && i.Operand is MethodReference m && m.Name == "RemoveSwap").ToArray();
        if (removals.Length != 2) throw new InvalidOperationException("Unexpected glide finish/deletion handling");
        foreach (var remove in removals) {
            // Find the start of the List/Index argument sequence for RemoveSwap.
            var start = remove;
            while (start.OpCode != OpCodes.Ldarg_0) start = start.Previous;
            Before(update, start, SetGlide(false));
        }
        LongBranches(update);
        var move = glideSystem.Methods.Single(m => m.Name == "OnTransformMove");
        // Changing container/z-level cancels the old relative-coordinate glide.
        // Upstream returned before removing it, leaving walking active until
        // an obsolete endpoint happened to be reached.
        var parentChanged = move.Body.Instructions.Single(i => i.Operand is MethodReference m && m.Name == "get_ParentChanged");
        var eventType = ((MethodReference)parentChanged.Operand).DeclaringType.Resolve();
        var component = module.ImportReference(eventType.Methods.Single(m => m.Name == "get_Component"));
        var cancel = new MethodDefinition("HandleMovementParentChange", MethodAttributes.Private, module.TypeSystem.Boolean);
        cancel.Parameters.Add(new ParameterDefinition("e", ParameterAttributes.None, move.Parameters[0].ParameterType));
        glideSystem.Methods.Add(cancel);
        var glides = glideSystem.Fields.Single(f => f.Name == "_currentGlides");
        var position = new VariableDefinition(module.TypeSystem.Int32);
        var entry = new VariableDefinition(glide);
        cancel.Body.Variables.Add(position); cancel.Body.Variables.Add(entry); cancel.Body.InitLocals = true;
        MethodReference ListMethod(string name) {
            var definition = module.ImportReference(glides.FieldType.Resolve().Methods.Single(m => m.Name == name));
            var result = new MethodReference(name, definition.ReturnType, glides.FieldType) { HasThis = true };
            foreach (var p in definition.Parameters) result.Parameters.Add(new ParameterDefinition(p.ParameterType));
            return result;
        }
        il = cancel.Body.GetILProcessor();
        var unchanged = il.Create(OpCodes.Ldc_I4_0); var testCancel = il.Create(OpCodes.Ldloc, position);
        var loopCancel = il.Create(OpCodes.Ldarg_0); var nextCancel = il.Create(OpCodes.Ldloc, position);
        il.Emit(OpCodes.Ldarg_1); il.Emit(OpCodes.Call, (MethodReference)parentChanged.Operand); il.Emit(OpCodes.Brfalse, unchanged);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldfld, glides); il.Emit(OpCodes.Callvirt, ListMethod("get_Count"));
        il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Sub); il.Emit(OpCodes.Stloc, position); il.Emit(OpCodes.Br, testCancel);
        il.Append(loopCancel); il.Emit(OpCodes.Ldfld, glides); il.Emit(OpCodes.Ldloc, position); il.Emit(OpCodes.Callvirt, ListMethod("get_Item")); il.Emit(OpCodes.Stloc, entry);
        il.Emit(OpCodes.Ldloc, entry); il.Emit(OpCodes.Ldfld, glide.Fields.Single(f => f.Name == "Transform"));
        il.Emit(OpCodes.Ldarg_1); il.Emit(OpCodes.Call, component); il.Emit(OpCodes.Bne_Un, nextCancel);
        il.Emit(OpCodes.Ldloc, entry); il.Emit(OpCodes.Ldfld, spriteField); il.Emit(OpCodes.Callvirt, getIcon);
        il.Emit(OpCodes.Ldc_I4_0); il.Emit(OpCodes.Call, set);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldfld, glides); il.Emit(OpCodes.Ldloc, position); il.Emit(OpCodes.Callvirt, ListMethod("RemoveAt"));
        il.Append(nextCancel); il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Sub); il.Emit(OpCodes.Stloc, position);
        il.Append(testCancel); il.Emit(OpCodes.Ldc_I4_0); il.Emit(OpCodes.Bge, loopCancel);
        il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Ret); il.Append(unchanged); il.Emit(OpCodes.Ret);
        move.Body.GetILProcessor().InsertBefore(parentChanged.Previous, Instruction.Create(OpCodes.Ldarg_0));
        parentChanged.Operand = cancel;
        var spriteLocal = move.Body.Variables.Single(v => v.VariableType == spriteType);
        var endPos = move.Body.Instructions.Single(i => i.OpCode == OpCodes.Stfld && i.Operand is FieldReference f && f.Name == "EndPos");
        Before(move, endPos.Next, Instruction.Create(OpCodes.Ldloc, spriteLocal), Instruction.Create(OpCodes.Callvirt, getIcon),
            Instruction.Create(OpCodes.Ldc_I4_1), Instruction.Create(OpCodes.Call, set));
        // The only early return after a valid sprite is the teleport path.
        var teleport = move.Body.Instructions.First(i => i.OpCode == OpCodes.Ret && i.Previous.OpCode == OpCodes.Stfld);
        Before(move, teleport, Instruction.Create(OpCodes.Ldloc, spriteLocal), Instruction.Create(OpCodes.Callvirt, getIcon),
            Instruction.Create(OpCodes.Ldc_I4_0), Instruction.Create(OpCodes.Call, set));
        LongBranches(move);
    }
}
