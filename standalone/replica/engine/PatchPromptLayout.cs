using System;
using System.Linq;
using System.Collections.Generic;
using Mono.Cecil;
using Mono.Cecil.Cil;

// Import the readable layout helper into OpenDreamClient itself, adding no
// runtime assembly dependency, then call it only from PromptWindow.Shown.
public static class PatchPromptLayout {
    public static void Main(string[] args) {
        var resolver=new DefaultAssemblyResolver();
        foreach(var p in args.Skip(3))resolver.AddSearchDirectory(p);
        using var target=AssemblyDefinition.ReadAssembly(args[0],new ReaderParameters{AssemblyResolver=resolver});
        using var source=AssemblyDefinition.ReadAssembly(args[2],new ReaderParameters{AssemblyResolver=resolver});
        var mod=target.MainModule;var old=source.MainModule.GetType("PromptLayout");
        var added=new TypeDefinition("OpenDreamClient.Interface.Prompts","PromptLayout",old.Attributes,mod.TypeSystem.Object);mod.Types.Add(added);
        var methods=new Dictionary<MethodDefinition,MethodDefinition>();
        foreach(var m in old.Methods) {
            var n=new MethodDefinition(m.Name,m.Attributes,mod.ImportReference(m.ReturnType));added.Methods.Add(n);methods[m]=n;
            foreach(var p in m.Parameters)n.Parameters.Add(new ParameterDefinition(p.Name,p.Attributes,mod.ImportReference(p.ParameterType)));
        }
        foreach(var m in old.Methods) {
            var n=methods[m];n.Body.InitLocals=m.Body.InitLocals;n.Body.MaxStackSize=m.Body.MaxStackSize;
            if(m.Body.HasExceptionHandlers)throw new Exception("Helper unexpectedly has exception handlers");
            var vars=new Dictionary<VariableDefinition,VariableDefinition>();
            foreach(var v in m.Body.Variables){var nv=new VariableDefinition(mod.ImportReference(v.VariableType));n.Body.Variables.Add(nv);vars[v]=nv;}
            var instructions=m.Body.Instructions.ToDictionary(i=>i,i=>Instruction.Create(OpCodes.Nop));
            foreach(var i in m.Body.Instructions) {
                var ni=instructions[i];ni.OpCode=i.OpCode;
                ni.Operand=i.Operand switch {
                    Instruction b=>instructions[b],Instruction[] bs=>bs.Select(b=>instructions[b]).ToArray(),
                    VariableDefinition v=>vars[v],ParameterDefinition p=>n.Parameters[p.Index],
                    MethodReference r when r.DeclaringType.FullName==old.FullName=>methods[r.Resolve()],
                    MethodReference r=>mod.ImportReference(r),FieldReference f=>mod.ImportReference(f),
                    TypeReference t=>mod.ImportReference(t),_=>i.Operand
                };
                n.Body.Instructions.Add(ni);
            }
        }
        var prompt=mod.GetType("OpenDreamClient.Interface.Prompts.PromptWindow");
        if(prompt.Methods.Any(m=>m.Name=="Shown"))throw new Exception("PromptWindow already declares Shown; review required");
        var shown=new MethodDefinition("Shown",MethodAttributes.Family|MethodAttributes.Virtual|MethodAttributes.HideBySig,mod.TypeSystem.Void);prompt.Methods.Add(shown);
        var il=shown.Body.GetILProcessor();
        var getWindow=mod.ImportReference(prompt.BaseType.Resolve().Methods.Single(m=>m.Name=="get_ClydeWindow"));
        var lastWindow=new FieldDefinition("_initialLayoutWindow",FieldAttributes.Private,mod.ImportReference(getWindow.ReturnType));prompt.Fields.Add(lastWindow);
        var done=Instruction.Create(OpCodes.Ret);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Call,mod.ImportReference(prompt.BaseType.Resolve().Methods.Single(m=>m.Name=="Shown")));
        // Re-showing an existing native window must preserve user sizing and
        // placement. A genuinely new native window may receive initial layout.
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Call,getWindow);il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldfld,lastWindow);il.Emit(OpCodes.Beq,done);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Call,getWindow);il.Emit(OpCodes.Stfld,lastWindow);
        il.Emit(OpCodes.Ldarg_0);il.Emit(OpCodes.Call,added.Methods.Single(m=>m.Name=="Shown"));il.Append(done);
        var inputShown=mod.GetType("OpenDreamClient.Interface.Prompts.InputWindow").Methods.Single(m=>m.Name=="Shown");
        var originalBase=inputShown.Body.Instructions.Single(i=>i.OpCode==OpCodes.Call && i.Operand is MethodReference r && r.Name=="Shown" && r.DeclaringType.FullName==prompt.BaseType.FullName);
        originalBase.Operand=shown;
        target.Write(args[1]);
        Console.WriteLine("Added one-time OpenDream prompt layout refresh after root attachment; original InputWindow focus runs afterward");
    }
}
