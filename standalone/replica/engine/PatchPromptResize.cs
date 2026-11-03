using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

// OSWindow.Create applies UI scale while the native window is hidden. Keep
// render-target dimensions current even then; callbacks remain visible-only.
public static class PatchPromptResize {
    public static void Main(string[] args) {
        var resolver=new DefaultAssemblyResolver();
        resolver.AddSearchDirectory(System.IO.Path.GetDirectoryName(System.IO.Path.GetFullPath(args[0])));
        foreach(var path in args.Skip(2))resolver.AddSearchDirectory(path);
        using var assembly=AssemblyDefinition.ReadAssembly(args[0],new ReaderParameters {AssemblyResolver=resolver});
        var type=assembly.MainModule.GetType("Robust.Client.Graphics.Clyde.Clyde");
        var method=type.Methods.Single(m=>m.Name=="SendWindowResized");
        if(args.Length==1) { foreach(var i in method.Body.Instructions)Console.WriteLine(i);return; }
        var code=method.Body.Instructions;
        var firstReturn=code.First(i=>i.OpCode==OpCodes.Ret);
        var guard=code.Take(code.IndexOf(firstReturn)+1).ToArray();
        var test=guard.Single(i=>i.OpCode.FlowControl==FlowControl.Cond_Branch);
        if(!guard.Any(i=>i.Operand is FieldReference f&&f.Name=="IsVisible") || guard.Length!=4 || test.Operand!=firstReturn.Next)
            throw new Exception("Unexpected resize visibility guard; refusing partial patch");
        var store=code.Single(i=>i.OpCode==OpCodes.Stfld&&i.Operand is FieldReference f&&f.Name=="Size");
        if(!code.Take(code.IndexOf(store)).Any(i=>i.Operand is MethodReference m&&m.Name=="RtToLoaded"))
            throw new Exception("Missing render-target resize bookkeeping");
        var continuation=store.Next;
        foreach(var i in guard)code.Remove(i);
        test.Operand=continuation;
        var il=method.Body.GetILProcessor();
        foreach(var i in guard)il.InsertBefore(continuation,i);
        assembly.Write(args[1]);
        Console.WriteLine("Moved render-target size bookkeeping before hidden-window guard; visible callback/event branch unchanged");
    }
}
