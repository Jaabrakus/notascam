using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

// Keep original state names public, with an ordered private collection retaining
// idle/movement variants. Existing same-name/same-flag lookup remains first-wins.
public static class PatchDmiVariants {
    static MethodReference Bound(ModuleDefinition m, TypeReference type, string name, int count) {
        var d=m.ImportReference(type.Resolve().Methods.Single(x=>x.Name==name&&x.Parameters.Count==count));
        var r=new MethodReference(d.Name,d.ReturnType,type){HasThis=d.HasThis};
        foreach(var p in d.Parameters)r.Parameters.Add(new ParameterDefinition(p.ParameterType));
        return r;
    }
    static void Nop(Instruction i){i.OpCode=OpCodes.Nop;i.Operand=null;}
    static void Before(MethodDefinition m,Instruction anchor,params Instruction[] code){
        var il=m.Body.GetILProcessor();foreach(var i in code)il.InsertBefore(anchor,i);
        foreach(var i in m.Body.Instructions.Except(code))if(i.Operand==anchor)i.Operand=code[0];
    }
    static void Long(MethodDefinition m){
        foreach(var i in m.Body.Instructions){
            if(i.OpCode.OperandType!=OperandType.ShortInlineBrTarget)continue;
            i.OpCode=i.OpCode.Code switch{
                Code.Br_S=>OpCodes.Br,Code.Brfalse_S=>OpCodes.Brfalse,Code.Brtrue_S=>OpCodes.Brtrue,
                Code.Beq_S=>OpCodes.Beq,Code.Bne_Un_S=>OpCodes.Bne_Un,Code.Bge_S=>OpCodes.Bge,
                Code.Bge_Un_S=>OpCodes.Bge_Un,Code.Bgt_S=>OpCodes.Bgt,Code.Bgt_Un_S=>OpCodes.Bgt_Un,
                Code.Ble_S=>OpCodes.Ble,Code.Ble_Un_S=>OpCodes.Ble_Un,Code.Blt_S=>OpCodes.Blt,
                Code.Blt_Un_S=>OpCodes.Blt_Un,Code.Leave_S=>OpCodes.Leave,
                _=>throw new InvalidOperationException("Unexpected branch "+i)};
        }
    }
    static MethodDefinition Method(TypeDefinition type,string name,TypeReference result,params (string,TypeReference)[] args){
        var method=new MethodDefinition(name,MethodAttributes.Public|MethodAttributes.HideBySig,result);
        foreach(var (n,t) in args)method.Parameters.Add(new ParameterDefinition(n,ParameterAttributes.None,t));
        type.Methods.Add(method);return method;
    }

    public static void Shared(ModuleDefinition m){
        var parser=m.Types.Single(t=>t.FullName=="OpenDreamShared.Resources.DMIParser");
        var desc=parser.NestedTypes.Single(t=>t.Name=="ParsedDMIDescription");
        var state=parser.NestedTypes.Single(t=>t.Name=="ParsedDMIState");
        var states=desc.Fields.Single(f=>f.Name=="States");
        var movement=state.Fields.Single(f=>f.Name=="Movement");
        var name=state.Fields.Single(f=>f.Name=="Name");
        var all=new FieldDefinition("AllStates",FieldAttributes.Public,states.FieldType);desc.Fields.Add(all);
        var count=Bound(m,states.FieldType,"get_Count",0);
        var add=Bound(m,states.FieldType,"Add",2);
        var item=Bound(m,states.FieldType,"get_Item",1);
        var setItem=Bound(m,states.FieldType,"set_Item",2);
        var contains=Bound(m,states.FieldType,"ContainsKey",1);
        var clear=Bound(m,states.FieldType,"Clear",0);
        var ctor=Bound(m,states.FieldType,".ctor",0);
        var number=m.ImportReference(typeof(int).GetMethod("ToString",Type.EmptyTypes));
        var equal=m.ImportReference(typeof(string).GetMethod("op_Equality",new[]{typeof(string),typeof(string)}));
        foreach(var c in desc.Methods.Where(x=>x.IsConstructor&&!x.IsStatic))
            Before(c,c.Body.Instructions.Last(),Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Newobj,ctor),Instruction.Create(OpCodes.Stfld,all));
        var getAll=Method(desc,"GetAllStates",states.FieldType);
        var il=getAll.Body.GetILProcessor();var primary=il.Create(OpCodes.Ldarg_0);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,all);il.Emit(OpCodes.Callvirt,count);il.Emit(OpCodes.Brfalse,primary);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,all);il.Emit(OpCodes.Ret);
        il.Append(primary);il.Emit(OpCodes.Ldfld,states);il.Emit(OpCodes.Ret);
        var remember=Method(desc,"RememberState",m.TypeSystem.Void,("state",state));
        var index=new VariableDefinition(m.TypeSystem.Int32);remember.Body.Variables.Add(index);remember.Body.InitLocals=true;
        il=remember.Body.GetILProcessor();
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,all);il.Emit(OpCodes.Callvirt,count);il.Emit(OpCodes.Stloc,index);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,all);il.Emit(OpCodes.Ldloca,index);il.Emit(OpCodes.Call,number);il.Emit(OpCodes.Ldarg_1);il.Emit(OpCodes.Callvirt,add);il.Emit(OpCodes.Ret);
        var reindex=Method(desc,"ReindexStates",m.TypeSystem.Void);
        var i=new VariableDefinition(m.TypeSystem.Int32);var s=new VariableDefinition(state);
        reindex.Body.Variables.Add(i);reindex.Body.Variables.Add(s);reindex.Body.InitLocals=true;il=reindex.Body.GetILProcessor();
        var test=il.Create(OpCodes.Ldloc,i);var loop=il.Create(OpCodes.Ldarg_0);var next=il.Create(OpCodes.Ldloc,i);var assign=il.Create(OpCodes.Ldarg_0);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,states);il.Emit(OpCodes.Callvirt,clear);
        il.Emit(OpCodes.Ldc_I4_0);il.Emit(OpCodes.Stloc,i);il.Emit(OpCodes.Br,test);
        il.Append(loop);il.Emit(OpCodes.Ldfld,all);il.Emit(OpCodes.Ldloca,i);il.Emit(OpCodes.Call,number);il.Emit(OpCodes.Callvirt,item);il.Emit(OpCodes.Stloc,s);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,states);il.Emit(OpCodes.Ldloc,s);il.Emit(OpCodes.Ldfld,name);il.Emit(OpCodes.Callvirt,contains);il.Emit(OpCodes.Brfalse,assign);
        il.Emit(OpCodes.Ldloc,s);il.Emit(OpCodes.Ldfld,movement);il.Emit(OpCodes.Brtrue,next);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,states);il.Emit(OpCodes.Ldloc,s);il.Emit(OpCodes.Ldfld,name);il.Emit(OpCodes.Callvirt,item);il.Emit(OpCodes.Ldfld,movement);il.Emit(OpCodes.Brfalse,next);
        il.Append(assign);il.Emit(OpCodes.Ldfld,states);il.Emit(OpCodes.Ldloc,s);il.Emit(OpCodes.Ldfld,name);il.Emit(OpCodes.Ldloc,s);il.Emit(OpCodes.Callvirt,setItem);
        il.Append(next);il.Emit(OpCodes.Ldc_I4_1);il.Emit(OpCodes.Add);il.Emit(OpCodes.Stloc,i);
        il.Append(test);il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,all);il.Emit(OpCodes.Callvirt,count);il.Emit(OpCodes.Blt,loop);il.Emit(OpCodes.Ret);
        var register=Method(desc,"RegisterState",m.TypeSystem.Void,("state",state));il=register.Body.GetILProcessor();
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldarg_1);il.Emit(OpCodes.Call,remember);il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Call,reindex);il.Emit(OpCodes.Ret);
        var original=desc.Methods.Single(x=>x.Name=="GetStateOrDefault");
        var resolve=Method(desc,"GetStateForMovement",state,("stateName",m.TypeSystem.String),("moving",m.TypeSystem.Boolean));
        i=new VariableDefinition(m.TypeSystem.Int32);s=new VariableDefinition(state);var fallback=new VariableDefinition(state);
        resolve.Body.Variables.Add(i);resolve.Body.Variables.Add(s);resolve.Body.Variables.Add(fallback);resolve.Body.InitLocals=true;il=resolve.Body.GetILProcessor();
        test=il.Create(OpCodes.Ldloc,i);loop=il.Create(OpCodes.Ldarg_0);next=il.Create(OpCodes.Ldloc,i);var done=il.Create(OpCodes.Ldloc,fallback);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldarg_1);il.Emit(OpCodes.Call,original);il.Emit(OpCodes.Stloc,fallback);il.Emit(OpCodes.Ldloc,fallback);il.Emit(OpCodes.Brfalse,done);
        il.Emit(OpCodes.Ldc_I4_0);il.Emit(OpCodes.Stloc,i);il.Emit(OpCodes.Br,test);
        il.Append(loop);il.Emit(OpCodes.Ldfld,all);il.Emit(OpCodes.Ldloca,i);il.Emit(OpCodes.Call,number);il.Emit(OpCodes.Callvirt,item);il.Emit(OpCodes.Stloc,s);
        il.Emit(OpCodes.Ldloc,s);il.Emit(OpCodes.Ldfld,name);il.Emit(OpCodes.Ldloc,fallback);il.Emit(OpCodes.Ldfld,name);il.Emit(OpCodes.Call,equal);il.Emit(OpCodes.Brfalse,next);
        il.Emit(OpCodes.Ldloc,s);il.Emit(OpCodes.Ldfld,movement);il.Emit(OpCodes.Ldarg_2);il.Emit(OpCodes.Bne_Un,next);il.Emit(OpCodes.Ldloc,s);il.Emit(OpCodes.Ret);
        il.Append(next);il.Emit(OpCodes.Ldc_I4_1);il.Emit(OpCodes.Add);il.Emit(OpCodes.Stloc,i);
        il.Append(test);il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,all);il.Emit(OpCodes.Callvirt,count);il.Emit(OpCodes.Blt,loop);il.Append(done);il.Emit(OpCodes.Ret);
        var parse=parser.Methods.Single(x=>x.Name=="ParseDMIDescription");
        var description=parse.Body.Variables.Single(v=>v.VariableType==desc);
        var current=parse.Body.Variables.Single(v=>v.VariableType==state);
        var tryAdd=parse.Body.Instructions.Single(x=>x.Operand is MethodReference r&&r.Name=="TryAdd");
        Before(parse,tryAdd,Instruction.Create(OpCodes.Ldloc,description),Instruction.Create(OpCodes.Ldloc,current),Instruction.Create(OpCodes.Call,remember));
        foreach(var ret in parse.Body.Instructions.Where(x=>x.OpCode==OpCodes.Ret).ToArray())
            Before(parse,ret,Instruction.Create(OpCodes.Dup),Instruction.Create(OpCodes.Call,reindex));
        Long(parse);
        var export=desc.Methods.Single(x=>x.Name=="ExportAsText");
        foreach(var load in export.Body.Instructions.Where(x=>x.OpCode==OpCodes.Ldfld&&x.Operand==states)){load.OpCode=OpCodes.Call;load.Operand=getAll;}
    }

    public static void Client(ModuleDefinition m){
        var resource=m.Types.Single(t=>t.FullName=="OpenDreamClient.Resources.ResourceTypes.DMIResource");
        var description=resource.Fields.Single(f=>f.Name=="Description");
        var desc=description.FieldType.Resolve();
        var resolve=m.ImportReference(desc.Methods.Single(x=>x.Name=="GetStateForMovement"));
        var getAll=m.ImportReference(desc.Methods.Single(x=>x.Name=="GetAllStates"));
        var parsed=resolve.ReturnType.Resolve();
        var movement=m.ImportReference(parsed.Fields.Single(f=>f.Name=="Movement"));
        var name=m.ImportReference(parsed.Fields.Single(f=>f.Name=="Name"));
        var states=resource.Fields.Single(f=>f.Name=="_states");
        var walking=new FieldDefinition("_movementStates",FieldAttributes.Private,states.FieldType);resource.Fields.Add(walking);
        var getDict=Method(resource,"GetVariantStates",states.FieldType,("moving",m.TypeSystem.Boolean));
        var il=getDict.Body.GetILProcessor();var regular=il.Create(OpCodes.Ldarg_0);var ready=il.Create(OpCodes.Ldarg_0);
        il.Emit(OpCodes.Ldarg_1);il.Emit(OpCodes.Brfalse,regular);il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,walking);il.Emit(OpCodes.Brtrue,ready);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Newobj,Bound(m,states.FieldType,".ctor",0));il.Emit(OpCodes.Stfld,walking);
        il.Append(ready);il.Emit(OpCodes.Ldfld,walking);il.Emit(OpCodes.Ret);il.Append(regular);il.Emit(OpCodes.Ldfld,states);il.Emit(OpCodes.Ret);
        var process=resource.Methods.Single(x=>x.Name=="ProcessDMIData");
        var local=process.Body.Variables.Single(v=>v.VariableType.FullName==parsed.FullName);
        foreach(var load in process.Body.Instructions.Where(x=>x.OpCode==OpCodes.Ldfld&&x.Operand is FieldReference f&&f.Name=="States"&&f.DeclaringType.FullName==desc.FullName).ToArray()){load.OpCode=OpCodes.Call;load.Operand=getAll;}
        var add=process.Body.Instructions.Single(x=>x.Operand is MethodReference r&&r.Name=="Add");
        var dictLoad=add;
        while(!(dictLoad.OpCode==OpCodes.Ldfld&&dictLoad.Operand==states))dictLoad=dictLoad.Previous;
        Before(process,dictLoad,Instruction.Create(OpCodes.Ldloc,local),Instruction.Create(OpCodes.Ldfld,movement));
        dictLoad.OpCode=OpCodes.Call;dictLoad.Operand=getDict;
        add.Operand=Bound(m,states.FieldType,"TryAdd",2);process.Body.GetILProcessor().InsertAfter(add,Instruction.Create(OpCodes.Pop));
        var clear=process.Body.Instructions.Single(x=>x.Operand is MethodReference r&&r.Name=="Clear");
        Before(process,clear.Next,Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldc_I4_1),Instruction.Create(OpCodes.Call,getDict),Instruction.Create(OpCodes.Callvirt,Bound(m,states.FieldType,"Clear",0)));
        Long(process);
        var oldGet=resource.Methods.Single(x=>x.Name=="GetState");
        var nullable=oldGet.ReturnType;
        var nullableCtor=(MethodReference)oldGet.Body.Instructions.First(x=>x.OpCode==OpCodes.Newobj&&x.Operand is MethodReference r&&r.DeclaringType.FullName.StartsWith("System.Nullable")).Operand;
        var newGet=Method(resource,"GetStateForMovement",nullable,("stateName",m.TypeSystem.String),("moving",m.TypeSystem.Boolean));
        var stateLocal=new VariableDefinition(m.ImportReference(parsed));var empty=new VariableDefinition(nullable);
        newGet.Body.Variables.Add(stateLocal);newGet.Body.Variables.Add(empty);newGet.Body.InitLocals=true;il=newGet.Body.GetILProcessor();
        var exists=il.Create(OpCodes.Ldarg_0);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,description);il.Emit(OpCodes.Ldarg_1);il.Emit(OpCodes.Ldarg_2);il.Emit(OpCodes.Callvirt,resolve);il.Emit(OpCodes.Stloc,stateLocal);
        il.Emit(OpCodes.Ldloc,stateLocal);il.Emit(OpCodes.Brtrue,exists);il.Emit(OpCodes.Ldloca,empty);il.Emit(OpCodes.Initobj,nullable);il.Emit(OpCodes.Ldloc,empty);il.Emit(OpCodes.Ret);
        il.Append(exists);il.Emit(OpCodes.Ldloc,stateLocal);il.Emit(OpCodes.Ldfld,movement);il.Emit(OpCodes.Call,getDict);
        il.Emit(OpCodes.Ldloc,stateLocal);il.Emit(OpCodes.Ldfld,name);il.Emit(OpCodes.Callvirt,Bound(m,states.FieldType,"get_Item",1));il.Emit(OpCodes.Newobj,nullableCtor);il.Emit(OpCodes.Ret);
        oldGet.Body=new MethodBody(oldGet);il=oldGet.Body.GetILProcessor();il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldarg_1);il.Emit(OpCodes.Ldc_I4_0);il.Emit(OpCodes.Call,newGet);il.Emit(OpCodes.Ret);
        var icon=m.Types.Single(t=>t.FullName=="OpenDreamClient.Rendering.DreamIcon");
        var active=icon.Fields.Single(f=>f.Name=="_movementActive");
        var frame=icon.Methods.Single(x=>x.Name=="GetAnimationFrame"&&x.Parameters.Count==2);
        var stateCall=frame.Body.Instructions.Single(x=>x.Operand is MethodReference r&&r.Name=="GetStateOrDefault");
        Before(frame,stateCall,Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldfld,active));stateCall.Operand=resolve;Long(frame);
        var texture=icon.Methods.Single(x=>x.Name=="GetTexture");
        var stateTexture=texture.Body.Instructions.Single(x=>x.Operand is MethodReference r&&r.Name=="GetState");
        var flick=texture.Parameters.Single(p=>p.Name=="flick");
        Before(texture,stateTexture,Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldfld,active),Instruction.Create(OpCodes.Ldarg,flick),Instruction.Create(OpCodes.Ldnull),Instruction.Create(OpCodes.Ceq),Instruction.Create(OpCodes.And));
        stateTexture.Operand=newGet;Long(texture);
        // Completing a finite variant must not suppress a different variant's
        // animation. Do not reset ordinary scenery on a movement transition.
        var reset=Method(icon,"ResetMovementVariant",m.TypeSystem.Void,("moving",m.TypeSystem.Boolean));
        var dmi=icon.Methods.Single(x=>x.Name=="get_DMI");
        il=reset.Body.GetILProcessor();var end=il.Create(OpCodes.Ret);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Call,dmi);il.Emit(OpCodes.Brfalse,end);
        foreach(var next in new[]{false,true}){
            il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Call,dmi);il.Emit(OpCodes.Ldfld,description);il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,icon.Fields.Single(f=>f.Name=="_iconState"));
            if(next)il.Emit(OpCodes.Ldarg_1);else{il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,active);}il.Emit(OpCodes.Callvirt,resolve);
        }
        il.Emit(OpCodes.Beq,end);
        foreach(var field in new[]{"_animationComplete","_animationFrame"}){il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldc_I4_0);il.Emit(OpCodes.Stfld,icon.Fields.Single(f=>f.Name==field));}
        il.Append(end);
        var set=icon.Methods.Single(x=>x.Name=="SetMovementActive");Before(set,set.Body.Instructions[0],Instruction.Create(OpCodes.Ldarg_0),Instruction.Create(OpCodes.Ldarg_1),Instruction.Create(OpCodes.Call,reset));Long(set);
    }
}
