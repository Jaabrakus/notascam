using System;
using System.Linq;
using System.Collections.Generic;
using Mono.Cecil;
using Mono.Cecil.Cil;

// Adds an explicit prompt-only API without changing OSWindow.Create, SDL
// startup placement, fullscreen transitions, or generic resize callbacks.
public static class PatchPromptPlacement {
    static IEnumerable<TypeDefinition> Types(IEnumerable<TypeDefinition> types) {
        foreach(var t in types){yield return t;foreach(var n in Types(t.NestedTypes))yield return n;}
    }
    public static void Main(string[] args) {
        var resolver=new DefaultAssemblyResolver();
        foreach(var p in args.Skip(3))resolver.AddSearchDirectory(p);
        using var target=AssemblyDefinition.ReadAssembly(args[0],new ReaderParameters{AssemblyResolver=resolver});
        using var source=AssemblyDefinition.ReadAssembly(args[2],new ReaderParameters{AssemblyResolver=resolver});
        var mod=target.MainModule;var old=source.MainModule.GetType("PromptPlacement");
        if(Types(mod.Types).Any(t=>t.Name=="PromptPlacement"))throw new Exception("Placement already patched; use clean resize candidate");
        var added=new TypeDefinition("Robust.Client.Graphics","PromptPlacement",old.Attributes,mod.TypeSystem.Object);mod.Types.Add(added);
        TypeReference MapType(TypeReference t)=>t.FullName==old.FullName?added:mod.ImportReference(t);
        var fields=new Dictionary<FieldDefinition,FieldDefinition>();
        foreach(var f in old.Fields){var nf=new FieldDefinition(f.Name,f.Attributes,MapType(f.FieldType));added.Fields.Add(nf);fields[f]=nf;}
        var methods=new Dictionary<MethodDefinition,MethodDefinition>();
        foreach(var m in old.Methods) {
            var n=new MethodDefinition(m.Name,m.Attributes,MapType(m.ReturnType));added.Methods.Add(n);methods[m]=n;
            n.ImplAttributes=m.ImplAttributes;
            if(m.HasPInvokeInfo) {
                var native=mod.ModuleReferences.FirstOrDefault(r=>r.Name==m.PInvokeInfo.Module.Name);
                if(native==null){native=new ModuleReference(m.PInvokeInfo.Module.Name);mod.ModuleReferences.Add(native);}
                n.PInvokeInfo=new PInvokeInfo(m.PInvokeInfo.Attributes,m.PInvokeInfo.EntryPoint,native);
            }
            foreach(var p in m.Parameters)n.Parameters.Add(new ParameterDefinition(p.Name,p.Attributes,MapType(p.ParameterType)));
        }
        foreach(var m in old.Methods) {
            var n=methods[m];if(!m.HasBody)continue;n.Body.InitLocals=m.Body.InitLocals;n.Body.MaxStackSize=m.Body.MaxStackSize;
            if(m.Body.HasExceptionHandlers)throw new Exception("Unexpected placement exception handler");
            var vars=new Dictionary<VariableDefinition,VariableDefinition>();
            foreach(var v in m.Body.Variables){var nv=new VariableDefinition(MapType(v.VariableType));n.Body.Variables.Add(nv);vars[v]=nv;}
            var instructions=m.Body.Instructions.ToDictionary(i=>i,i=>Instruction.Create(OpCodes.Nop));
            foreach(var i in m.Body.Instructions) {
                var ni=instructions[i];ni.OpCode=i.OpCode;
                ni.Operand=i.Operand switch {
                    Instruction b=>instructions[b],Instruction[] bs=>bs.Select(b=>instructions[b]).ToArray(),
                    VariableDefinition v=>vars[v],ParameterDefinition p=>n.Parameters[p.Index],
                    MethodReference r when r.DeclaringType.FullName==old.FullName=>methods[r.Resolve()],
                    MethodReference r=>mod.ImportReference(r),
                    FieldReference f when f.DeclaringType.FullName==old.FullName=>fields[f.Resolve()],
                    FieldReference f=>mod.ImportReference(f),TypeReference t=>MapType(t),_=>i.Operand
                };n.Body.Instructions.Add(ni);
            }
        }
        var clyde=mod.GetType("Robust.Client.Graphics.Clyde.Clyde");
        var window=mod.GetType("Robust.Client.UserInterface.Controls.OSWindow");
        var handle=clyde.NestedTypes.Single(t=>t.Name=="WindowHandle");
        var reg=clyde.NestedTypes.Single(t=>t.Name=="WindowReg");
        var windowing=clyde.NestedTypes.Single(t=>t.Name=="Sdl3WindowingImpl");
        var sdl=windowing.NestedTypes.Single(t=>t.Name=="Sdl3WindowReg");
        var getWindow=window.Methods.Single(m=>m.Name=="get_ClydeWindow");
        var getOwner=window.Methods.Single(m=>m.Name=="get_Owner");
        var getStartup=window.Methods.Single(m=>m.Name=="get_StartupLocation");
        var center=Convert.ToInt32(getStartup.ReturnType.Resolve().Fields.Single(f=>f.Name=="CenterOwner").Constant);
        var handleReg=handle.Fields.Single(f=>f.Name=="Reg");
        var handleClyde=handle.Fields.Single(f=>f.Name=="_clyde");
        var disposed=reg.Fields.Single(f=>f.Name=="IsDisposed");
        var pointer=sdl.Fields.Single(f=>f.Name=="Sdl3Window");
        var id=sdl.Fields.Single(f=>f.Name=="WindowId");
        var queue=clyde.Methods.Single(m=>m.Name=="RunOnWindowThread");
        var ctor=added.Methods.Single(m=>m.IsConstructor);
        var execute=added.Methods.Single(m=>m.Name=="Execute");
        // CLR private access is enforced between containing/nested classes.
        // Keep each private-field/type access in its declaring owner; do not
        // widen original field or nested-type visibility.
        var getClyde=new MethodDefinition("GetInitialPromptClyde",MethodAttributes.Assembly|MethodAttributes.HideBySig,clyde);handle.Methods.Add(getClyde);
        var gi=getClyde.Body.GetILProcessor();gi.Emit(OpCodes.Ldarg_0);gi.Emit(OpCodes.Ldfld,handleClyde);gi.Emit(OpCodes.Ret);
        var create=new MethodDefinition("CreateInitialPromptPlacement",MethodAttributes.Assembly|MethodAttributes.Static|MethodAttributes.HideBySig,added);
        create.Parameters.Add(new ParameterDefinition("child",ParameterAttributes.None,reg));create.Parameters.Add(new ParameterDefinition("owner",ParameterAttributes.None,reg));windowing.Methods.Add(create);
        create.Body.InitLocals=true;var childReg=new VariableDefinition(sdl);var ownerReg=new VariableDefinition(sdl);create.Body.Variables.Add(childReg);create.Body.Variables.Add(ownerReg);
        var ci=create.Body.GetILProcessor();var reject=Instruction.Create(OpCodes.Ldnull);
        void GetReg(int index,VariableDefinition to){ci.Emit(index==0?OpCodes.Ldarg_0:OpCodes.Ldarg_1);ci.Emit(OpCodes.Isinst,sdl);ci.Emit(OpCodes.Stloc,to);ci.Emit(OpCodes.Ldloc,to);ci.Emit(OpCodes.Brfalse,reject);ci.Emit(OpCodes.Ldloc,to);ci.Emit(OpCodes.Ldfld,disposed);ci.Emit(OpCodes.Brtrue,reject);}
        GetReg(0,childReg);GetReg(1,ownerReg);
        foreach(var v in new[]{childReg,ownerReg}){ci.Emit(OpCodes.Ldloc,v);ci.Emit(OpCodes.Ldfld,pointer);ci.Emit(OpCodes.Ldloc,v);ci.Emit(OpCodes.Ldfld,id);}
        ci.Emit(OpCodes.Newobj,ctor);ci.Emit(OpCodes.Ret);ci.Append(reject);ci.Emit(OpCodes.Ret);
        var bridge=new MethodDefinition("CenterInitialPromptOnOwner",MethodAttributes.Assembly|MethodAttributes.Static|MethodAttributes.HideBySig,mod.TypeSystem.Void);
        bridge.Parameters.Add(new ParameterDefinition("prompt",ParameterAttributes.None,window));clyde.Methods.Add(bridge);
        bridge.Body.InitLocals=true;
        var child=new VariableDefinition(handle);var owner=new VariableDefinition(handle);var action=new VariableDefinition(added);
        foreach(var v in new[]{child,owner,action})bridge.Body.Variables.Add(v);
        var il=bridge.Body.GetILProcessor();var done=Instruction.Create(OpCodes.Ret);
        // Only declared CenterOwner and live windows on the same Clyde may
        // request placement. SDL validates actual parentage on its thread;
        // WindowReg.Owner is not authoritative in the bundled SDL backend.
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Callvirt,getStartup);il.Emit(OpCodes.Ldc_I4,center);il.Emit(OpCodes.Bne_Un,done);
        void GetHandle(MethodDefinition getter,VariableDefinition local){il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Callvirt,getter);il.Emit(OpCodes.Isinst,handle);il.Emit(OpCodes.Stloc,local);il.Emit(OpCodes.Ldloc,local);il.Emit(OpCodes.Brfalse,done);}
        GetHandle(getWindow,child);GetHandle(getOwner,owner);
        il.Emit(OpCodes.Ldloc,child);il.Emit(OpCodes.Call,getClyde);il.Emit(OpCodes.Ldloc,owner);il.Emit(OpCodes.Call,getClyde);il.Emit(OpCodes.Bne_Un,done);
        il.Emit(OpCodes.Ldloc,child);il.Emit(OpCodes.Ldfld,handleReg);il.Emit(OpCodes.Ldloc,owner);il.Emit(OpCodes.Ldfld,handleReg);il.Emit(OpCodes.Call,create);il.Emit(OpCodes.Stloc,action);il.Emit(OpCodes.Ldloc,action);il.Emit(OpCodes.Brfalse,done);
        il.Emit(OpCodes.Ldloc,child);il.Emit(OpCodes.Call,getClyde);il.Emit(OpCodes.Ldloc,action);il.Emit(OpCodes.Ldftn,execute);
        var delegateCtor=new MethodReference(".ctor",mod.TypeSystem.Void,queue.Parameters[0].ParameterType){HasThis=true};delegateCtor.Parameters.Add(new ParameterDefinition(mod.TypeSystem.Object));delegateCtor.Parameters.Add(new ParameterDefinition(mod.TypeSystem.IntPtr));
        il.Emit(OpCodes.Newobj,delegateCtor);il.Emit(OpCodes.Call,queue);il.Append(done);
        var api=new MethodDefinition("CenterInitialPromptOnOwner",MethodAttributes.Public|MethodAttributes.HideBySig,mod.TypeSystem.Void);window.Methods.Add(api);
        var ai=api.Body.GetILProcessor();ai.Emit(OpCodes.Ldarg_0);ai.Emit(OpCodes.Call,bridge);ai.Emit(OpCodes.Ret);
        target.Write(args[1]);
        Console.WriteLine("Added initial prompt-only CenterOwner queue with SDL lifetime checks and usable-display clamping; generic window paths unchanged");
    }
}
