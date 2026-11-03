using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

// Small audited IL edits to the published client; avoids rebuilding unrelated
// engine/XAML tooling. Equivalent source changes are retained alongside this.
public static class PatchClient {
    public static void Main(string[] args) {
        if (args[0] == "--shared") {
            var sharedResolver = new DefaultAssemblyResolver();
            foreach (var directory in args.Skip(3)) sharedResolver.AddSearchDirectory(directory);
            using var shared = AssemblyDefinition.ReadAssembly(args[1], new ReaderParameters { AssemblyResolver = sharedResolver });
            PatchMovement.Shared(shared.MainModule);
            PatchDmiVariants.Shared(shared.MainModule);
            shared.Write(args[2]);
            Console.WriteLine("Patched shared DMI movement metadata parse/export");
            return;
        }
        var resolver = new DefaultAssemblyResolver();
        foreach (var directory in args.Skip(2)) resolver.AddSearchDirectory(directory);
        using var assembly = AssemblyDefinition.ReadAssembly(args[0], new ReaderParameters { AssemblyResolver = resolver });
        var module = assembly.MainModule;
        var verbs = module.Types.Single(t => t.FullName == "OpenDreamClient.ClientVerbSystem");
        var onAll = verbs.Methods.Single(m => m.Name == "OnAllVerbsEvent");
        var verbField = verbs.Fields.Single(f => f.Name == "_verbs");
        InsertClear(module, onAll, verbField, onAll.Body.Instructions[0]);
        var ui = module.Types.Single(t => t.FullName == "OpenDreamClient.Interface.DreamInterfaceManager");
        var reset = ui.Methods.Single(m => m.Name == "Reset");
        var ids = ui.Fields.Single(f => f.Name.Contains("ClydeWindowIdToControl") && f.Name.Contains("BackingField"));
        foreach (var ret in reset.Body.Instructions.Where(i => i.OpCode == OpCodes.Ret).ToArray())
            InsertClear(module, reset, ids, ret);
        WrapPromptMessages(module);
        FixVerbGrid(module);
        UnquoteTextArguments(module, ui);
        SelectPromptDefaults(module);
        StopAllOnChannelZero(module);
        PatchMovement.Client(module);
        PatchDmiVariants.Client(module);
        PatchRewind.Client(module);
        PatchContextClick.Apply(module);
        PatchPromptSelection.Apply(module);
        PatchPromptTargets.Apply(module);
        assembly.Write(args[1]);
        Console.WriteLine("Patched client: replace verb snapshots; clear native window IDs; wrap prompt messages; bound verb-grid columns; unquote text verb arguments; select prompt default text.");
    }
    // BYOND: sound(null) on channel 0 stops every channel. The client indexed
    // channel - 1 and threw, so the game's `usr << sound(null)` crashed its handler.
    private static void StopAllOnChannelZero(ModuleDefinition module) {
        var engine = module.Types.Single(t => t.FullName == "OpenDreamClient.Audio.DreamSoundEngine");
        var stop = engine.Methods.Single(m => m.Name == "StopChannel" && m.Parameters.Count == 1);
        var stopAll = engine.Methods.Single(m => m.Name == "StopAllChannels" && !m.HasParameters);
        var il = stop.Body.GetILProcessor();
        var first = stop.Body.Instructions[0];
        il.InsertBefore(first, il.Create(OpCodes.Ldarg_1));
        il.InsertBefore(first, il.Create(OpCodes.Brtrue, first));
        il.InsertBefore(first, il.Create(OpCodes.Ldarg_0));
        il.InsertBefore(first, il.Create(OpCodes.Call, stopAll));
        il.InsertBefore(first, il.Create(OpCodes.Ret));
    }
    // Dream Seeker's input() text/number dialogs open with the default value
    // selected, so typing replaces it. The client left the caret after it, so a
    // typed name was appended ("Orc" + "Grok" -> "OrcGrok").
    private static void SelectPromptDefaults(ModuleDefinition module) {
        var window = module.Types.Single(t => t.FullName == "OpenDreamClient.Interface.Prompts.InputWindow");
        var shown = window.Methods.Single(m => m.Name == "Shown" && !m.HasParameters);
        var focus = window.Fields.Single(f => f.Name == "_focusControl");
        var lineEditType = focus.FieldType.Resolve().Module.GetType("Robust.Client.UserInterface.Controls.LineEdit"); // Robust.Client, like Control
        MethodReference LineEdit(string name) => module.ImportReference(lineEditType.Methods.Single(m => m.Name == name));
        var helper = new MethodDefinition("SelectPromptDefault", MethodAttributes.Private | MethodAttributes.Static, module.TypeSystem.Void);
        helper.Parameters.Add(new ParameterDefinition("control", ParameterAttributes.None, module.TypeSystem.Object));
        var edit = new VariableDefinition(module.ImportReference(lineEditType));
        helper.Body.Variables.Add(edit);
        helper.Body.InitLocals = true;
        window.Methods.Add(helper);
        var il = helper.Body.GetILProcessor();
        var done = il.Create(OpCodes.Ret);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Isinst, module.ImportReference(lineEditType)); il.Emit(OpCodes.Stloc, edit);
        il.Emit(OpCodes.Ldloc, edit); il.Emit(OpCodes.Brfalse, done);
        il.Emit(OpCodes.Ldloc, edit); il.Emit(OpCodes.Ldloc, edit); il.Emit(OpCodes.Callvirt, LineEdit("get_Text"));
        il.Emit(OpCodes.Callvirt, module.ImportReference(typeof(string).GetProperty("Length")!.GetMethod));
        il.Emit(OpCodes.Callvirt, LineEdit("set_CursorPosition"));
        il.Emit(OpCodes.Ldloc, edit); il.Emit(OpCodes.Ldc_I4_0); il.Emit(OpCodes.Callvirt, LineEdit("set_SelectionStart"));
        il.Append(done);
        var body = shown.Body.GetILProcessor();
        foreach (var ret in shown.Body.Instructions.Where(i => i.OpCode == OpCodes.Ret).ToArray()) {
            body.InsertBefore(ret, body.Create(OpCodes.Ldarg_0));
            body.InsertBefore(ret, body.Create(OpCodes.Ldfld, focus));
            body.InsertBefore(ret, body.Create(OpCodes.Call, helper));
        }
    }
    // BYOND removes the quotes around a quoted command argument; the client kept
    // them, so skin macros such as `Quick 1 "Select"` sent the text "\"Select\"".
    private static void UnquoteTextArguments(ModuleDefinition module, TypeDefinition ui) {
        var run = ui.Methods.Single(m => m.Name == "RunCommand");
        var stringType = module.TypeSystem.String;
        MethodReference StringMethod(string name, params Type[] types) => module.ImportReference(typeof(string).GetMethod(name, types));
        var length = module.ImportReference(typeof(string).GetProperty("Length")!.GetMethod);
        var chars = module.ImportReference(typeof(string).GetMethod("get_Chars", new[] { typeof(int) }));
        var substring = StringMethod("Substring", typeof(int));
        var substringRange = StringMethod("Substring", typeof(int), typeof(int));
        var unquote = new MethodDefinition("UnquoteVerbArgument", MethodAttributes.Private | MethodAttributes.Static, stringType);
        unquote.Parameters.Add(new ParameterDefinition("argument", ParameterAttributes.None, stringType));
        ui.Methods.Add(unquote);
        var il = unquote.Body.GetILProcessor();
        var original = il.Create(OpCodes.Ldarg_0);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Brfalse, original);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Callvirt, length); il.Emit(OpCodes.Brfalse, original);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldc_I4_0); il.Emit(OpCodes.Callvirt, chars);
        il.Emit(OpCodes.Ldc_I4, '"'); il.Emit(OpCodes.Bne_Un, original);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Callvirt, substring); il.Emit(OpCodes.Starg, unquote.Parameters[0]);
        // An unterminated quote (BYOND's `say "` prefix style) keeps the rest as text.
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Callvirt, length); il.Emit(OpCodes.Brfalse, original);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Callvirt, length); il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Sub);
        il.Emit(OpCodes.Callvirt, chars); il.Emit(OpCodes.Ldc_I4, '"'); il.Emit(OpCodes.Bne_Un, original);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldc_I4_0); il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Callvirt, length);
        il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Sub); il.Emit(OpCodes.Callvirt, substringRange); il.Emit(OpCodes.Ret);
        il.Append(original); il.Emit(OpCodes.Ret);
        // Only the text branch stores a parsed argument straight into the object array.
        var stores = run.Body.Instructions.Where(i => i.OpCode == OpCodes.Callvirt && i.Operand is MethodReference m &&
            m.Name == "get_Item" && m.DeclaringType.FullName.StartsWith("System.Collections.Generic.List`1<System.String>") &&
            i.Next.OpCode == OpCodes.Stelem_Ref).ToArray();
        if (stores.Length != 1) throw new InvalidOperationException("Unexpected RunCommand argument parser; refusing partial unquote patch");
        run.Body.GetILProcessor().InsertAfter(stores[0], Instruction.Create(OpCodes.Call, unquote));
    }
    private static void FixVerbGrid(ModuleDefinition module) {
        var grid = module.Types.Single(t => t.FullName == "OpenDreamClient.Interface.Controls.UI.VerbPanelGrid");
        var measure = grid.Methods.Single(m => m.Name == "MeasureOverride");
        var il = measure.Body.GetILProcessor();
        var columns = grid.Fields.Single(f => f.Name == "_columns");
        var max = module.ImportReference(typeof(Math).GetMethod("Max", new[] { typeof(int), typeof(int) }));
        foreach (var instruction in measure.Body.Instructions.Where(i => i.OpCode == OpCodes.Stfld && i.Operand == columns).ToArray()) {
            il.InsertBefore(instruction, il.Create(OpCodes.Ldc_I4_1));
            il.InsertBefore(instruction, il.Create(OpCodes.Call, max));
        }
        // The infinite-width branch sets three columns; make its subsequent
        // cell calculation use the measured natural width, not infinity / 3.
        var infinity = measure.Body.Instructions.Single(i => i.Operand is MethodReference m && m.Name == "IsPositiveInfinity");
        var branch = infinity.Next;
        var before = branch.Next;
        var vectorX = (FieldReference)infinity.Previous.Operand;
        il.InsertBefore(before, il.Create(OpCodes.Ldarga, measure.Parameters[0]));
        il.InsertBefore(before, il.Create(OpCodes.Ldloc, measure.Body.Variables[0]));
        il.InsertBefore(before, il.Create(OpCodes.Ldfld, vectorX));
        il.InsertBefore(before, il.Create(OpCodes.Ldc_R4, 3f));
        il.InsertBefore(before, il.Create(OpCodes.Mul));
        il.InsertBefore(before, il.Create(OpCodes.Stfld, vectorX));
    }
    private static void WrapPromptMessages(ModuleDefinition module) {
        var prompt = module.Types.Single(t => t.FullName == "OpenDreamClient.Interface.Prompts.PromptWindow");
        var constructor = prompt.Methods.Single(m => m.IsConstructor);
        var client = prompt.BaseType.Resolve().Module;
        var control = client.GetType("Robust.Client.UserInterface.Control");
        var scroll = client.GetType("Robust.Client.UserInterface.Controls.ScrollContainer");
        var rich = client.GetType("Robust.Client.UserInterface.Controls.RichTextLabel");
        MethodReference Ref(TypeDefinition type, string name, int count) => module.ImportReference(type.Methods.Single(m => m.Name == name && m.Parameters.Count == count));
        var setter = new MethodDefinition("SetWrappedPromptMessage", MethodAttributes.Private | MethodAttributes.Static, module.TypeSystem.Void);
        setter.Parameters.Add(new ParameterDefinition("container", ParameterAttributes.None, module.ImportReference(scroll)));
        setter.Parameters.Add(new ParameterDefinition("message", ParameterAttributes.None, module.TypeSystem.String));
        prompt.Methods.Add(setter);
        var il = setter.Body.GetILProcessor();
        void Property(TypeDefinition type, string name, float value) {
            il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldc_R4, value); il.Emit(OpCodes.Callvirt, Ref(type, "set_"+name, 1));
        }
        void Flag(string name, bool value) {
            il.Emit(OpCodes.Ldarg_0); il.Emit(value ? OpCodes.Ldc_I4_1 : OpCodes.Ldc_I4_0); il.Emit(OpCodes.Callvirt, Ref(scroll, "set_"+name, 1));
        }
        Property(control, "MaxWidth", 480);
        Property(control, "MaxHeight", 360);
        Flag("HScrollEnabled", false);
        Flag("VScrollEnabled", true);
        Flag("ReturnMeasure", true);
        var text = new VariableDefinition(module.ImportReference(rich));
        setter.Body.Variables.Add(text);
        setter.Body.InitLocals = true;
        il.Emit(OpCodes.Newobj, Ref(rich, ".ctor", 0)); il.Emit(OpCodes.Stloc, text);
        // SetMessage(string, Color?) treats brackets and markup as literal text.
        var message = rich.Methods.Single(m => m.Name == "SetMessage" && m.Parameters.Count == 2 && m.Parameters[0].ParameterType.FullName == "System.String");
        var colorType = (GenericInstanceType)message.Parameters[1].ParameterType;
        var color = colorType.GenericArguments[0].Resolve();
        var nullableCtor = module.ImportReference(colorType.Resolve().Methods.Single(m => m.IsConstructor && m.Parameters.Count == 1));
        nullableCtor.DeclaringType = module.ImportReference(colorType);
        il.Emit(OpCodes.Ldloc, text); il.Emit(OpCodes.Ldarg_1);
        il.Emit(OpCodes.Call, Ref(color, "get_Black", 0));
        il.Emit(OpCodes.Newobj, nullableCtor);
        il.Emit(OpCodes.Callvirt, module.ImportReference(message));
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Ldloc, text); il.Emit(OpCodes.Callvirt, Ref(control, "AddChild", 1));
        il.Emit(OpCodes.Ret);
        var replaced = 0;
        foreach (var variable in constructor.Body.Variables)
            if (variable.VariableType.FullName == "Robust.Client.UserInterface.Controls.Label") variable.VariableType = module.ImportReference(scroll);
        foreach (var instruction in constructor.Body.Instructions) {
            if (instruction.Operand is not MethodReference method || method.DeclaringType.FullName != "Robust.Client.UserInterface.Controls.Label") continue;
            if (method.Name == ".ctor") { instruction.Operand = Ref(scroll, ".ctor", 0); replaced++; }
            if (method.Name == "set_Text") { instruction.OpCode = OpCodes.Call; instruction.Operand = setter; replaced++; }
        }
        if (replaced != 2) throw new InvalidOperationException("Unexpected prompt constructor; refusing partial layout patch");
    }
    private static void InsertClear(ModuleDefinition module, MethodDefinition method, FieldDefinition field, Instruction before) {
        var clear = new MethodReference("Clear", module.TypeSystem.Void, field.FieldType) { HasThis = true };
        var il = method.Body.GetILProcessor();
        il.InsertBefore(before, il.Create(OpCodes.Ldarg_0));
        il.InsertBefore(before, il.Create(OpCodes.Ldfld, field));
        il.InsertBefore(before, il.Create(OpCodes.Callvirt, clear));
    }
}
