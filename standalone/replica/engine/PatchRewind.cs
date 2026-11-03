using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

// BYOND RenderIcon oracle: looping rewind visits 0..N-1,N-2..1;
// each visit uses that source frame's own delay. Explicit flick ignores rewind.
public static class PatchRewind {
    public static void Client(ModuleDefinition m) {
        var icon=m.Types.Single(t=>t.FullName=="OpenDreamClient.Rendering.DreamIcon");
        var frame=icon.Methods.Single(x=>x.Name=="GetAnimationFrame"&&x.Parameters.Count==2);
        var stateLocal=frame.Body.Variables.Single(v=>v.VariableType.Name=="ParsedDMIState");
        var state=stateLocal.VariableType.Resolve();
        var getFrames=m.ImportReference(state.Methods.Single(x=>x.Name=="GetFrames"&&x.Parameters.Count==1));
        var array=(ArrayType)getFrames.ReturnType;
        var parsedFrame=array.ElementType.Resolve();
        var delay=m.ImportReference(parsedFrame.Fields.Single(f=>f.Name=="Delay"));
        var ticks=m.ImportReference(typeof(TimeSpan).GetProperty("Ticks").GetMethod);
        var getTime=(MethodReference)frame.Body.Instructions.Single(i=>i.Operand is MethodReference r&&r.Name=="get_CurTime").Operand;
        var clock=icon.Fields.Single(f=>f.Name=="<gameTiming>P");
        var animationFrame=icon.Fields.Single(f=>f.Name=="_animationFrame");
        var dirty=icon.Methods.Single(x=>x.Name=="DirtyTexture");
        var helper=new MethodDefinition("GetLoopingRewindFrame",MethodAttributes.Private,m.TypeSystem.Int32);
        helper.Parameters.Add(new ParameterDefinition("state",ParameterAttributes.None,m.ImportReference(state)));
        helper.Parameters.Add(new ParameterDefinition("dir",ParameterAttributes.None,frame.Parameters[1].ParameterType));
        icon.Methods.Add(helper);
        var frames=new VariableDefinition(m.ImportReference(array));
        var count=new VariableDefinition(m.TypeSystem.Int32);
        var length=new VariableDefinition(m.TypeSystem.Int32);
        var position=new VariableDefinition(m.TypeSystem.Int32);
        var selected=new VariableDefinition(m.TypeSystem.Int32);
        var duration=new VariableDefinition(m.TypeSystem.Int64);
        var remaining=new VariableDefinition(m.TypeSystem.Int64);
        var currentDelay=new VariableDefinition(m.TypeSystem.Int64);
        var now=new VariableDefinition(m.ImportReference(typeof(TimeSpan)));
        foreach(var v in new[]{frames,count,length,position,selected,duration,remaining,currentDelay,now})helper.Body.Variables.Add(v);
        helper.Body.InitLocals=true;
        var il=helper.Body.GetILProcessor();
        var finish=il.Create(OpCodes.Ldarg_0);
        var unchanged=il.Create(OpCodes.Ldloc,selected);
        var sumTest=il.Create(OpCodes.Ldloc,position);
        var sumLoop=il.Create(OpCodes.Nop);
        var pickLoop=il.Create(OpCodes.Nop);
        void SelectFrame() {
            var forward=il.Create(OpCodes.Ldloc,position);
            var store=il.Create(OpCodes.Stloc,selected);
            il.Emit(OpCodes.Ldloc,position);il.Emit(OpCodes.Ldloc,count);il.Emit(OpCodes.Blt,forward);
            il.Emit(OpCodes.Ldloc,length);il.Emit(OpCodes.Ldloc,position);il.Emit(OpCodes.Sub);il.Emit(OpCodes.Br,store);
            il.Append(forward);il.Append(store);
        }
        void Delay() {
            il.Emit(OpCodes.Ldloc,frames);il.Emit(OpCodes.Ldloc,selected);il.Emit(OpCodes.Ldelem_Ref);
            il.Emit(OpCodes.Ldflda,delay);il.Emit(OpCodes.Call,ticks);
        }
        il.Emit(OpCodes.Ldarg_1);il.Emit(OpCodes.Ldarg_2);il.Emit(OpCodes.Callvirt,getFrames);il.Emit(OpCodes.Stloc,frames);
        il.Emit(OpCodes.Ldloc,frames);il.Emit(OpCodes.Ldlen);il.Emit(OpCodes.Conv_I4);il.Emit(OpCodes.Stloc,count);
        il.Emit(OpCodes.Ldloc,count);il.Emit(OpCodes.Ldc_I4_1);il.Emit(OpCodes.Ble,finish);
        il.Emit(OpCodes.Ldloc,count);il.Emit(OpCodes.Ldc_I4_1);il.Emit(OpCodes.Sub);il.Emit(OpCodes.Ldc_I4_2);il.Emit(OpCodes.Mul);il.Emit(OpCodes.Stloc,length);
        il.Emit(OpCodes.Br,sumTest);
        il.Append(sumLoop);SelectFrame();il.Emit(OpCodes.Ldloc,duration);Delay();il.Emit(OpCodes.Add);il.Emit(OpCodes.Stloc,duration);
        il.Emit(OpCodes.Ldloc,position);il.Emit(OpCodes.Ldc_I4_1);il.Emit(OpCodes.Add);il.Emit(OpCodes.Stloc,position);
        il.Append(sumTest);il.Emit(OpCodes.Ldloc,length);il.Emit(OpCodes.Blt,sumLoop);
        il.Emit(OpCodes.Ldc_I4_0);il.Emit(OpCodes.Stloc,selected);
        il.Emit(OpCodes.Ldloc,duration);il.Emit(OpCodes.Ldc_I4_0);il.Emit(OpCodes.Conv_I8);il.Emit(OpCodes.Ble,finish);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,clock);il.Emit(OpCodes.Callvirt,getTime);il.Emit(OpCodes.Stloc,now);
        il.Emit(OpCodes.Ldloca,now);il.Emit(OpCodes.Call,ticks);il.Emit(OpCodes.Ldloc,duration);il.Emit(OpCodes.Rem);il.Emit(OpCodes.Stloc,remaining);
        il.Emit(OpCodes.Ldc_I4_0);il.Emit(OpCodes.Stloc,position);
        il.Append(pickLoop);SelectFrame();Delay();il.Emit(OpCodes.Stloc,currentDelay);
        il.Emit(OpCodes.Ldloc,remaining);il.Emit(OpCodes.Ldloc,currentDelay);il.Emit(OpCodes.Blt,finish);
        il.Emit(OpCodes.Ldloc,remaining);il.Emit(OpCodes.Ldloc,currentDelay);il.Emit(OpCodes.Sub);il.Emit(OpCodes.Stloc,remaining);
        il.Emit(OpCodes.Ldloc,position);il.Emit(OpCodes.Ldc_I4_1);il.Emit(OpCodes.Add);il.Emit(OpCodes.Stloc,position);
        il.Emit(OpCodes.Ldloc,position);il.Emit(OpCodes.Ldloc,length);il.Emit(OpCodes.Blt,pickLoop);
        il.Emit(OpCodes.Ldc_I4_0);il.Emit(OpCodes.Stloc,selected);
        il.Append(finish);il.Emit(OpCodes.Ldfld,animationFrame);il.Emit(OpCodes.Ldloc,selected);il.Emit(OpCodes.Beq,unchanged);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldloc,selected);il.Emit(OpCodes.Stfld,animationFrame);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Call,dirty);il.Append(unchanged);il.Emit(OpCodes.Ret);

        // This anchor follows state null/completion checks and the stationary
        // movement freeze added by PatchMovement. Forward and finite paths stay
        // byte-for-byte intact; no texture-cache or Flick scheduling changes.
        var call=frame.Body.Instructions.Single(i=>i.Operand is MethodReference r&&r.Name=="GetFrames");
        var anchor=call.Previous.Previous;
        if(anchor.OpCode!=OpCodes.Ldloc_0||call.Previous.OpCode!=OpCodes.Ldarg_2)
            throw new InvalidOperationException("Unexpected frame-array lookup; review rewind insertion");
        var code=new[]{Instruction.Create(OpCodes.Ldloc,stateLocal),Instruction.Create(OpCodes.Ldfld,m.ImportReference(state.Fields.Single(f=>f.Name=="Rewind"))),Instruction.Create(OpCodes.Brfalse,anchor),
            Instruction.Create(OpCodes.Ldloc,stateLocal),Instruction.Create(OpCodes.Ldfld,m.ImportReference(state.Fields.Single(f=>f.Name=="Loop"))),Instruction.Create(OpCodes.Brfalse,anchor),
            Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldloc,stateLocal),Instruction.Create(OpCodes.Ldarg_2),Instruction.Create(OpCodes.Call,helper),Instruction.Create(OpCodes.Ret)};
        il=frame.Body.GetILProcessor();foreach(var instruction in code)il.InsertBefore(anchor,instruction);
        foreach(var instruction in frame.Body.Instructions.Except(code))if(instruction.Operand==anchor)instruction.Operand=code[0];
    }
}
