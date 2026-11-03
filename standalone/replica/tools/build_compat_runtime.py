#!/usr/bin/env python3
"""Build a narrowly patched OpenDream runtime against its published assemblies.

Requires a matching OpenDream source checkout/server release, .NET 10 SDK and
JetBrains.Annotations.dll. Never edits the upstream checkout or game source.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'robust_source', 'server', 'sdk', 'annotations', 'build_dir'):
        parser.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--shared-assembly',type=Path,help='Staged compatible OpenDreamShared.dll with movement metadata support')
    parser.add_argument('--output',type=Path,help='Override retained DLL output for a fully private staged build')
    args = parser.parse_args()
    work = args.build_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, DOTNET_CLI_HOME=str(work/'sdk-home'),
               DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',
               DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    # Use the matching Robust serialization generator, with the SDK's Roslyn
    # assemblies. Omitting generation compiles but fails at runtime.
    generator_dir = work/'generator'
    generator_dir.mkdir(exist_ok=True)
    generator = ET.Element('Project', Sdk='Microsoft.NET.Sdk')
    gp = ET.SubElement(generator, 'PropertyGroup')
    for key, value in {'TargetFramework': 'net10.0', 'ImplicitUsings': 'enable',
                       'Nullable': 'enable', 'EnableDefaultCompileItems': 'false',
                       'AllowUnsafeBlocks': 'true', 'AssemblyName': 'Robust.Serialization.Generator'}.items():
        ET.SubElement(gp, key).text = value
    gi = ET.SubElement(generator, 'ItemGroup')
    for folder in ('Robust.Serialization.Generator', 'Robust.Roslyn.Shared'):
        directory = args.robust_source.resolve()/folder
        ET.SubElement(gi, 'Compile', Include=str(directory/'**/*.cs'), Exclude=str(directory/'obj/**'))
    sdk_roots = sorted((args.sdk.resolve().parent/'sdk').glob('*'))
    sdk_root = sdk_roots[-1]
    for name in ('Microsoft.CodeAnalysis', 'Microsoft.CodeAnalysis.CSharp', 'Microsoft.CodeAnalysis.Workspaces'):
        candidates = list(sdk_root.rglob(name+'.dll'))
        path = next((p for p in candidates if 'dotnet-format' in str(p)), candidates[0])
        ref = ET.SubElement(gi, 'Reference', Include=name)
        ET.SubElement(ref, 'HintPath').text = str(path)
    generator_project = generator_dir/'Generator.csproj'
    ET.ElementTree(generator).write(generator_project, encoding='unicode')
    with (ROOT/'reports/generator-build.log').open('w') as log:
        subprocess.run([str(args.sdk.resolve()), 'build', str(generator_project), '-c', 'Release',
                        '--ignore-failed-sources'], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    upstream = args.source.resolve() / 'OpenDreamRuntime'
    shutil.copytree(upstream, work/'src', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('bin', 'obj'))
    # /mob has a separate registry. Only world for-loops opt in to including
    # it for exact /atom/movable; locate() keeps the original helper behavior.
    # Retain the existing single-argument method for binary callers.
    atoms = work/'src/AtomManager.cs'
    text = atoms.read_text(encoding='utf-8-sig')
    before_method = '    public IEnumerable<DreamObjectAtom> EnumerateAtoms(TreeEntry? filterType = null) {'
    after_method = '''    public IEnumerable<DreamObjectAtom> EnumerateAtoms(TreeEntry? filterType = null) =>
        EnumerateAtoms(filterType, includeMobsForMovable: false);

    public IEnumerable<DreamObjectAtom> EnumerateAtoms(TreeEntry? filterType, bool includeMobsForMovable) {'''
    before_mobs = 'if (filterType?.IsSubtypeOf(_objectTree.Mob) != false) {'
    after_mobs = 'if ((includeMobsForMovable && filterType == _objectTree.Movable) || filterType?.IsSubtypeOf(_objectTree.Mob) != false) {'
    if text.count(before_method) != 1 or text.count(before_mobs) != 1:
        raise RuntimeError('Upstream world atom enumeration changed; review exact Movable fix')
    atoms.write_text(text.replace(before_method, after_method).replace(before_mobs, after_mobs))
    enumerators = work/'src/Procs/DreamEnumerators.cs'
    text = enumerators.read_text(encoding='utf-8-sig')
    before_call = 'atomManager.EnumerateAtoms(filterType).GetEnumerator()'
    after_call = 'atomManager.EnumerateAtoms(filterType, includeMobsForMovable: true).GetEnumerator()'
    if text.count(before_call) != 1:
        raise RuntimeError('Upstream world contents consumer changed; review Movable opt-in')
    enumerators.write_text(text.replace(before_call, after_call))
    target = work/'src/Procs/InitDreamObject.cs'
    text = target.read_text()
    before = 'newProc.CreateState(Thread, src, _usr, new DreamProcArguments(args))'
    after = 'newProc.CreateState(Thread, src, src is DreamObjectMob ? src : _usr, new DreamProcArguments(args))'
    if text.count(before) != 1:
        raise RuntimeError('Upstream constructor changed; review the patch before building')
    target.write_text(text.replace('using OpenDreamRuntime.Objects;',
                      'using OpenDreamRuntime.Objects;\nusing OpenDreamRuntime.Objects.Types;')
                      .replace(before, after))
    delays = work/'src/Procs/ProcScheduler.Delays.cs'
    text = delays.read_text(encoding='utf-8-sig')
    before_queue = 'private PriorityQueue<DelayTicker, uint> _tickers = new();'
    before_enqueue = '_tickers.Enqueue(ticker, ticker.TicksAt);'
    if text.count(before_queue) != 1 or text.count(before_enqueue) != 1:
        raise RuntimeError('Upstream scheduler changed; review the FIFO patch')
    delays.write_text(text.replace(before_queue,
        'private PriorityQueue<DelayTicker, (uint Tick, ulong Order)> _tickers = new();\n    private ulong _delayOrder;')
        .replace(before_enqueue, '_tickers.Enqueue(ticker, (ticker.TicksAt, _delayOrder++));'))
    resource = work/'src/Resources/DMFResource.cs'
    text = resource.read_text()
    text = text.replace('public sealed class DMFResource : DreamResource {',
        'public sealed class DMFResource : DreamResource {\n    public string? DefaultBrowserId { get; private set; }\n    public string? DefaultBrowserOnShow { get; private set; }')
    anchor = 'foreach (ControlDescriptor controlDescriptor in windowDescriptor.ControlDescriptors) {'
    if text.count(anchor) != 1:
        raise RuntimeError('Upstream DMF resource changed; review default browser routing')
    text = text.replace(anchor, anchor+'\n                if (DefaultBrowserId == null && controlDescriptor is ControlDescriptorBrowser browser && browser.IsDefault.Value) {\n                    DefaultBrowserId = windowDescriptor.Id.Value + "." + browser.Id.Value;\n                    DefaultBrowserOnShow = browser.OnShowCommand.AsRaw();\n                }')
    resource.write_text(text)
    connection = work/'src/DreamConnection.cs'
    text = connection.read_text()
    anchor = '        var msg = new MsgBrowse() {'
    if text.count(anchor) != 1:
        raise RuntimeError('Upstream Browse changed; review default browser routing')
    connection.write_text(text.replace(anchor,
        '        var skin = _resourceManager.InterfaceFile;\n'
        '        window ??= skin?.DefaultBrowserId;\n'
        '        if (body != null && window == skin?.DefaultBrowserId && !string.IsNullOrWhiteSpace(skin?.DefaultBrowserOnShow))\n'
        '            WinSet(null, "command=" + HttpUtility.JavaScriptStringEncode(skin.DefaultBrowserOnShow, true));\n\n'+anchor))
    shutil.copy2(ROOT/'engine/ByondRandom.cs', work/'src/ByondRandom.cs')
    shutil.copy2(ROOT/'engine/DreamProcNativeWander.cs', work/'src/Procs/Native/DreamProcNativeWander.cs')
    shutil.copy2(ROOT/'engine/DreamManager.LocalHosting.cs', work/'src/DreamManager.LocalHosting.cs')
    manager = work/'src/DreamManager.cs'
    manager.write_text(manager.read_text().replace('public Random Random { get; set; } = new();',
                                                  'public ByondRandom Random { get; set; } = new();'))
    text = manager.read_text()
    anchor = '        if (!Initialized)\n            return;'
    assert text.count(anchor) == 1
    manager.write_text(text.replace(anchor, anchor + '\n\n        ProcessLocalSaveRequest();'))
    opcodes = work/'src/Procs/DMOpcodeHandlers.cs'
    text = opcodes.read_text(encoding='utf-8-sig')
    text = text.replace('Random.NextDouble() * totalWeight', 'Random.NextWeight() * totalWeight')
    # Values are popped in reverse source order. BYOND's weighted intervals
    # follow source order, so walk the cumulative table backwards by weight.
    text = text.replace('for (int i = 0; i < values.Length; i++) {\n                if (pick < values[i].CumulativeWeight) {',
        'for (int i = values.Length - 1; i >= 0; i--) {\n'
        '                pick -= values[i].CumulativeWeight - (i == 0 ? 0 : values[i-1].CumulativeWeight);\n'
        '                if (pick < 0) {')
    text = text.replace('Random.Next(0, values.Count)', 'Random.NextPick(values.Count)')
    text = text.replace('Random.Next(0, count)', 'Random.NextPick(count)')
    text = text.replace('a.TryGetValueAsFloatCoerceNull(out _)) { // no-op',
                        'a.TryGetValueAsFloatCoerceNull(out _) || a.TryGetValueAsString(out _)) { // no-op')
    old_self = 'case DMReference.Type.Self: {\n                    instance = state.Instance;\n                    proc = state.Proc;'
    assert text.count(old_self) == 1
    text = text.replace(old_self, old_self + '\n                    if (argumentInfo.Type == DMCallArgumentsType.None)\n                        argumentInfo = new(DMCallArgumentsType.FromProcArguments, 0);')
    opcodes.write_text(text)
    resources = work/'src/Resources/DreamResourceManager.cs'
    text = resources.read_text(encoding='utf-8-sig')
    before = 'File.WriteAllText(filePath, text);'
    assert text.count(before) == 1
    text = text.replace(before,
        'File.AppendAllText(filePath, text.Replace("\\r\\n", "\\n").Replace("\\n", "\\r\\n") + "\\r\\n");\n'
        '            if (TryLoadResource(filePath, out var cached)) cached.ReloadFromDisk();')
    resources.write_text(text)
    root_natives = work/'src/Procs/Native/DreamProcNativeRoot.cs'
    text = root_natives.read_text(encoding='utf-8-sig')
    start = text.index('    public static DreamValue NativeProc_file2text(')
    end = text.index('    [DreamProc("filter")]', start)
    section = text[start:end].replace('resource = bundle.ResourceManager.LoadResource(rscPath);',
        'resource = bundle.ResourceManager.LoadResource(rscPath);\n            resource.ReloadFromDisk();')
    section = section.replace('string? text = resource.ReadAsString();',
        'string? text = resource.ResourceData == null ? null : System.Text.Encoding.UTF8.GetString(resource.ResourceData);')
    text = (text[:start]+section+text[end:]).replace('bundle.DreamManager.Random = new Random(seed);',
                                                              'bundle.DreamManager.Random = new ByondRandom(seed);')
    text = text.replace('bundle.DreamManager.Random.Next(high+1)',
                        '(int)(bundle.DreamManager.Random.NextSingle() * (high + 1))')
    old_turn = """        if (dirArg.TryGetValueAsDreamObject<DreamObjectIcon>(out var icon)) {
            DreamObjectIcon clonedIcon = icon.Clone();

            icon.Turn(angleArg);
            return new(clonedIcon);
        }"""
    assert old_turn in text
    text = text.replace(old_turn, """        if (dirArg.TryGetValueAsDreamObject<DreamObjectIcon>(out _) ||
            bundle.ResourceManager.TryLoadIcon(dirArg, out _)) {
            var clonedIcon = new DreamObjectIcon(bundle.ObjectTree.Icon.ObjectDefinition);
            clonedIcon.Initialize(new DreamProcArguments(new[] { dirArg }));
            clonedIcon.Turn(angleArg);
            return new(clonedIcon);
        }""")
    # BYOND stat panels: statpanel("Inventory", contents) lists each item (the
    # list may be the Name argument), stat(obj) shows the object, and an
    # object's suffix ("(Equipped)") follows its name. Upstream printed "/list".
    old_stat = '''        if (name.IsNull && value.TryGetValueAsDreamList(out var list)) {
            foreach (var item in list.EnumerateValues())
                OutputToStatPanel(refManager, connection, name, item);
        } else {
            string nameStr = name.Stringify();
            string? atomRef = null;
            if (value.TryGetValueAsDreamObject<DreamObjectAtom>(out _)) // Atoms are clickable
                atomRef = refManager.GetRefString(value);

            connection.AddStatPanelLine(nameStr, value.Stringify(), atomRef);
        }'''
    new_stat = '''        if (value.IsNull && (name.TryGetValueAsDreamList(out _) || name.TryGetValueAsDreamObject<DreamObjectAtom>(out _))) {
            value = name;
            name = DreamValue.Null;
        }
        if (name.IsNull && value.TryGetValueAsDreamList(out var list)) {
            foreach (var item in list.EnumerateValues())
                OutputToStatPanel(refManager, connection, name, item);
        } else {
            string nameStr = name.Stringify();
            string valueStr = value.Stringify();
            string? atomRef = null;
            if (value.TryGetValueAsDreamObject<DreamObjectAtom>(out var statAtom)) { // Atoms are clickable
                atomRef = refManager.GetRefString(value);
                if (statAtom.GetVariable("suffix").TryGetValueAsString(out var suffix) && !string.IsNullOrEmpty(suffix))
                    valueStr += " " + suffix;
            }

            connection.AddStatPanelLine(nameStr, valueStr, atomRef);
        }'''
    if text.count(old_stat) != 1:
        raise RuntimeError('Upstream stat panel output changed; review list/suffix handling')
    text = text.replace(old_stat, new_stat)
    # typesof(/Type/verb) enumerates direct verb declarations, not the
    # inherited list of automatically granted instance verbs. ConstantProcStub
    # already compiles to a string, including for datum-like command groups.
    old_typesof = """                    if (typeString.EndsWith("/proc")) {
                        type = bundle.ObjectTree.GetTreeEntry(typeString.Substring(0, typeString.Length - 5));
                        addingProcs = type.ObjectDefinition.Procs.Values;
                    } else if (typeString.EndsWith("/verb")) {
                        type = bundle.ObjectTree.GetTreeEntry(typeString.Substring(0, typeString.Length - 5));
                        addingProcs = type.ObjectDefinition.Verbs?.Values ?? Enumerable.Empty<int>();
                    } else {
                        type = bundle.ObjectTree.GetTreeEntry(typeString);
                    }"""
    new_typesof = """                    if (typeString.Length > 1) typeString = typeString.TrimEnd('/');
                    if (typeString.EndsWith("/proc") || typeString.EndsWith("/verb")) {
                        if (!bundle.ObjectTree.TryGetTreeEntry(typeString[..^5], out type))
                            continue;
                        var wantVerbs = typeString.EndsWith("/verb");
                        var procDefinitions = bundle.ObjectTree.Procs;
                        addingProcs = type.ObjectDefinition.Procs.Values.Where(id =>
                            procDefinitions[id].IsVerb == wantVerbs);
                    } else if (!bundle.ObjectTree.TryGetTreeEntry(typeString, out type)) {
                        continue;
                    }"""
    if text.count(old_typesof) != 1:
        raise RuntimeError('Upstream typesof changed; review direct declaration enumeration')
    text = text.replace(old_typesof, new_typesof)
    root_natives.write_text(text)
    icon_source = work/'src/Objects/DreamIcon.cs'
    text = icon_source.read_text()
    # Blend's missing-direction fallback is always SOUTH, unlike renderer
    # diagonal fallback. The original explicit SOUTH underwear source must be
    # blended onto every corpse direction. Keep pixel math/frame policy intact.
    old_blend_direction = """        if (_blendingState?.Directions.TryGetValue(dir, out var blendingDirFrames) is not true)
            return;"""
    new_blend_direction = """        if (_blendingState == null)
            return;
        if (!_blendingState.Directions.TryGetValue(dir, out var blendingDirFrames) &&
            !_blendingState.Directions.TryGetValue(AtomDirection.South, out blendingDirFrames))
            return;"""
    if text.count(old_blend_direction) != 1:
        raise RuntimeError('Upstream image Blend changed; review SOUTH fallback')
    text = text.replace(old_blend_direction, new_blend_direction)
    # Adding directions reindexes deferred-operation frame offsets. First
    # materialize the current appearance; new directions then inherit the
    # already-processed SOUTH pixels, rather than replaying old directional ops.
    materialize_anchor = '    public void ApplyOperation(IDreamIconOperation operation) {'
    materialize = """    internal void MaterializeOperations() {
        if (_operations.Count == 0)
            return;
        var current = GenerateDMI();
        _operations.Clear();
        States.Clear();
        InsertStates(current, DreamValue.Null, DreamValue.Null, DreamValue.Null);
    }

"""
    if text.count(materialize_anchor) != 1:
        raise RuntimeError('Icon operation entry changed; review materialization')
    text = text.replace(materialize_anchor, materialize + materialize_anchor)
    growth_anchor = """        // If any states in the icon have less directions than the one we're blending onto it,
        // We give them the new directions.
"""
    growth_prepare = """        if (icon.States.Values.Any(state =>
                _blendingState.Directions.Keys.Any(dir => !state.Directions.ContainsKey(dir))))
            icon.MaterializeOperations();

"""
    if text.count(growth_anchor) != 1:
        raise RuntimeError('Blend direction expansion changed; review materialization')
    text = text.replace(growth_anchor, growth_prepare + growth_anchor)
    growth_old = """                    // Create the empty frames
                    for (int i = 0; i < state.Frames; i++) {
                        newFrames.Add(new(null, new ParsedDMIFrame(), icon.Width, icon.Height));
                    }
"""
    growth_new = """                    // BYOND expands from SOUTH after all prior operations.
                    state.Directions.TryGetValue(AtomDirection.South, out var southFrames);
                    for (int i = 0; i < state.Frames; i++) {
                        newFrames.Add(southFrames != null && i < southFrames.Count
                            ? southFrames[i]
                            : new(null, new ParsedDMIFrame(), icon.Width, icon.Height));
                    }
"""
    if text.count(growth_old) != 1:
        raise RuntimeError('Blend empty direction initialization changed')
    text = text.replace(growth_old, growth_new)
    # ArrayPool storage can contain previous allocations. Blank directions and
    # empty icons must begin transparent before any alpha composition.
    rent = '        Rgba32[] pixels = PixelArrayPool.Rent(span * frameHeight);'
    if text.count(rent) != 1:
        raise RuntimeError('Upstream icon buffer changed; review initialization')
    text = text.replace(rent, rent + '\n        Array.Clear(pixels, 0, span * frameHeight);')
    # Generated equipment/hair icons must retain the original movement-only
    # state flag, or the renderer cannot distinguish walking from idle art.
    movement_changes = [
        ('public int Frames;', 'public int Frames;\n        public bool Movement;\n        public bool Rewind;'),
        ('new IconState { Frames = Frames }', 'new IconState { Frames = Frames, Movement = Movement, Rewind = Rewind }'),
        ('{ Loop = false, Rewind = false }', '{ Loop = false, Rewind = iconState.Rewind, Movement = iconState.Movement }'),
        ('        foreach (var insertingPair in insertingDirections) {',
         '        iconState.Movement = inserting.Movement;\n\n        foreach (var insertingPair in insertingDirections) {'),
    ]
    for before, after in movement_changes:
        if text.count(before) != 1:
            raise RuntimeError('Upstream icon metadata changed; review movement flag preservation: '+before)
        text = text.replace(before, after)
    # Serialized DMI pixels must be frame-major: S1,N1,E1,W1,S2,N2,... .
    # Direction-major output looks correct to the server's in-memory metadata,
    # but clients reconstruct coordinates from the PNG description and would
    # animate a generated equipment/hair layer through different directions.
    icon_layout_changes = [
        ('int firstFrame = currentFrame;\n\n                currentFrame += iconState.Frames;',
         'int firstFrame = currentFrame + directionIndex;'),
        ('DrawFrames(pixels, firstFrame, frames, direction)',
         'DrawFrames(pixels, firstFrame, frames, direction, exportedDirectionCount)'),
        ('newState.Directions.Add(direction, newFrames);\n            }',
         'newState.Directions.Add(direction, newFrames);\n            }\n            currentFrame += iconState.Frames * exportedDirectionCount;'),
        ('List<IconFrame> frames, AtomDirection dir) {',
         'List<IconFrame> frames, AtomDirection dir, int directionStride) {'),
        ('operation.AppliedFrames <= firstFrameIndex + frameIndex',
         'operation.AppliedFrames <= firstFrameIndex + frameIndex * directionStride'),
        ('            x += Width;', '            x += Width * directionStride;'),
    ]
    for before, after in icon_layout_changes:
        if text.count(before) != 1:
            raise RuntimeError('Upstream icon layout changed; review direction/frame interleaving: ' + before)
        text = text.replace(before, after)
    # State names alone are not a unique DMI key. Preserve ordinary/walking
    # variants in copies and generated equipment without exposing tuple keys to
    # DM icon_states(). Explicit constructors and Insert have distinct semantics
    # verified against the isolated BYOND 516.1655 reference fixture.
    text = text.replace('Dictionary<string, IconState> States',
                        'Dictionary<(string Name, bool Movement), IconState> States')
    text = text.replace('new(iconStatePair.Key) {', 'new(iconStatePair.Key.Name) {')
    text = text.replace('newDescription.States.Add(newState.Name, newState);',
                        'newDescription.RegisterState(newState);')
    begin = text.index('    public void InsertStates(')
    end = text.index('    private ParsedDMIFrame[] DrawFrames(', begin)
    text = text[:begin] + '''    public void InsertStates(IconResource icon, DreamValue state, DreamValue dir, DreamValue frame,
        DreamValue moving = default, bool isConstructor = false, bool insertion = false) {
        // Optional internal copy callers omit this struct argument; default(T)
        // is an uninitialized DreamValue, distinct from DM's explicit null.
        if (moving.Type == 0) moving = DreamValue.Null;
        bool copyingAllDirs = !dir.TryGetValueAsInteger(out var dirVal);
        bool copyingAllStates = !state.TryGetValueAsString(out var copyingState);
        // Constructor zero/negative frame selectors retain the full animation.
        bool copyingAllFrames = !frame.TryGetValueAsInteger(out var copyingFrame) ||
            (isConstructor && copyingFrame <= 0);
        AtomDirection copyingDirection = (AtomDirection)dirVal;
        if (!Enum.IsDefined(copyingDirection) || copyingDirection == AtomDirection.None)
            copyingAllDirs = true;
        Width = Math.Max(Width, icon.DMI.Width);
        Height = Math.Max(Height, icon.DMI.Height);
        var allStates = icon.DMI.GetAllStates().Values;
        if (insertion) {
            // Insert's state/moving arguments name and classify the destination;
            // the first source state provides pixels, regardless of its flag.
            var first = allStates.FirstOrDefault();
            if (first != null)
                InsertState(icon, copyingState ?? string.Empty, first, moving.IsTruthy(),
                    copyingAllDirs ? null : copyingDirection, copyingAllFrames ? null : copyingFrame);
            return;
        }
        // An absent constructor state name copies the entire original resource,
        // ignoring dir/frame/moving selectors. A present empty state is distinct.
        if (isConstructor && !copyingAllStates &&
            !allStates.Any(source => source.Name == copyingState)) {
            copyingAllStates = true;
            copyingAllDirs = true;
            copyingAllFrames = true;
            moving = DreamValue.Null;
        }
        var selectedName = copyingAllStates ? null : icon.DMI.GetStateOrDefault(copyingState)?.Name;
        var seen = new HashSet<(string, bool)>();
        foreach (var source in allStates) {
            if ((!copyingAllStates && source.Name != selectedName) || !seen.Add((source.Name, source.Movement))) continue;
            if (!moving.IsNull && source.Movement != moving.IsTruthy()) continue;
            // A selected movement-only extraction becomes a regular animation;
            // unspecified moving keeps both source flags (BYOND constructor).
            var destinationMovement = moving.IsNull && source.Movement;
            InsertState(icon, isConstructor && !copyingAllStates ? string.Empty : source.Name,
                source, destinationMovement, copyingAllDirs ? null : copyingDirection,
                copyingAllFrames ? null : copyingFrame, forceSouth: isConstructor);
        }
    }

    private void InsertState(IconResource icon, string stateName, ParsedDMIState inserting,
        bool movement, AtomDirection? dir = null, int? frame = null, bool forceSouth = false) {
        var insertingDirections = inserting.GetFrames(dir, frame - 1, asSouth: forceSouth);
        var key = (stateName, movement);
        if (!States.TryGetValue(key, out var iconState)) iconState = new IconState();
        iconState.Movement = movement;
        iconState.Rewind = inserting.Rewind;
        foreach (var insertingPair in insertingDirections) {
            if (insertingPair.Value.Length == 0) continue;
            List<IconFrame> iconFrames = new(insertingPair.Value.Length);
            foreach (var dmiFrame in insertingPair.Value) {
                // Only explicit constructor frame extraction resets delay.
                // Copy the metadata: source resources and icon aliases share it.
                var selectedFrame = forceSouth && frame.HasValue
                    ? new ParsedDMIFrame { X = dmiFrame.X, Y = dmiFrame.Y, Delay = TimeSpan.FromMilliseconds(100) }
                    : dmiFrame;
                iconFrames.Add(new IconFrame(icon.Texture, selectedFrame, icon.DMI.Width, icon.DMI.Height));
            }
            iconState.Directions[insertingPair.Key] = iconFrames;
            iconState.Frames = Math.Max(iconState.Frames, iconFrames.Count);
        }
        if (!States.ContainsKey(key) && iconState.Frames > 0) States.Add(key, iconState);
        _cachedDMI = null;
    }

''' + text[end:]
    # BYOND grows Blend animations by repeating each shorter frame cycle.
    # The single-frame exported delay is 1, but constructors retain its original
    # delay internally until expansion; serialized file round trips lose it.
    animation_changes = [
        ('        public bool Rewind;', '        public bool Rewind;\n        public TimeSpan? SingleFrameDelay;'),
        ('Movement = Movement, Rewind = Rewind }',
         'Movement = Movement, Rewind = Rewind, SingleFrameDelay = SingleFrameDelay }'),
        ('        var current = GenerateDMI();\n        _operations.Clear();',
         '        var originalDelays = States.ToDictionary(pair => pair.Key, pair => pair.Value.SingleFrameDelay);\n        var current = GenerateDMI();\n        _operations.Clear();'),
        ('        InsertStates(current, DreamValue.Null, DreamValue.Null, DreamValue.Null);',
         '        InsertStates(current, DreamValue.Null, DreamValue.Null, DreamValue.Null);\n        foreach (var pair in States)\n            pair.Value.SingleFrameDelay = originalDelays.GetValueOrDefault(pair.Key);'),
        ('DreamValue moving = default, bool isConstructor = false, bool insertion = false) {',
         'DreamValue moving = default, bool isConstructor = false, bool insertion = false, DreamIcon? sourceIcon = null) {'),
        ('            var destinationMovement = moving.IsNull && source.Movement;',
         '            var destinationMovement = moving.IsNull && source.Movement;\n            var originalDelay = sourceIcon?.States.GetValueOrDefault((source.Name, source.Movement))?.SingleFrameDelay;'),
        ('copyingAllFrames ? null : copyingFrame, forceSouth: isConstructor);',
         'copyingAllFrames ? null : copyingFrame, forceSouth: isConstructor, singleFrameDelay: originalDelay);'),
        ('bool movement, AtomDirection? dir = null, int? frame = null, bool forceSouth = false) {',
         'bool movement, AtomDirection? dir = null, int? frame = null, bool forceSouth = false, TimeSpan? singleFrameDelay = null) {'),
        ('        iconState.Movement = movement;',
         '        iconState.SingleFrameDelay = singleFrameDelay;\n        iconState.Movement = movement;'),
        ('            foreach (var dmiFrame in insertingPair.Value) {',
         '            foreach (var dmiFrame in insertingPair.Value) {\n                if (insertingPair.Value.Length == 1 && forceSouth)\n                    iconState.SingleFrameDelay = singleFrameDelay ?? dmiFrame.Delay;'),
        ('_blendingState.Directions.Keys.Any(dir => !state.Directions.ContainsKey(dir))))',
         '_blendingState.FrameCount > state.Frames ||\n                _blendingState.Directions.Keys.Any(dir => !state.Directions.ContainsKey(dir))))'),
        ('        // TODO: We add frames too',
         """        foreach (var state in icon.States.Values) {
            if (_blendingState.FrameCount <= state.Frames)
                continue;
            if (state.Frames == 1)
                state.Rewind = _blendingState.Rewind;
            foreach (var direction in state.Directions.Keys.ToArray()) {
                var previous = state.Directions[direction];
                if (previous.Count == 0)
                    continue;
                var expanded = new List<DreamIcon.IconFrame>(_blendingState.FrameCount);
                for (int i = 0; i < _blendingState.FrameCount; i++) {
                    var original = previous[i % previous.Count];
                    var metadata = new ParsedDMIFrame {
                        X = original.DMIFrame.X,
                        Y = original.DMIFrame.Y,
                        Delay = state.SingleFrameDelay ?? original.DMIFrame.Delay
                    };
                    expanded.Add(new(original.Image, metadata, original.Width, original.Height));
                }
                state.Directions[direction] = expanded;
            }
            state.Frames = _blendingState.FrameCount;
            state.SingleFrameDelay = null;
        }"""),
        ('        if (blendingDirFrames.Length <= frame)\n            return;\n\n        var blendingFrame = blendingDirFrames[frame];',
         '        if (blendingDirFrames.Length == 0)\n            return;\n\n        var blendingFrame = blendingDirFrames[frame % blendingDirFrames.Length];'),
    ]
    for before, after in animation_changes:
        if text.count(before) != 1:
            raise RuntimeError('Blend animation source changed; review: '+before)
        text = text.replace(before, after)
    # Image Blend chooses matching source name and idle/movement variant per
    # destination state. Preserve the pre-existing absent-name fallback.
    variant_changes = [
        ('DrawFrames(pixels, firstFrame, frames, direction, exportedDirectionCount)',
         'DrawFrames(pixels, firstFrame, frames, direction, exportedDirectionCount, iconStatePair.Key.Name, iconState.Movement)'),
        ('List<IconFrame> frames, AtomDirection dir, int directionStride) {',
         'List<IconFrame> frames, AtomDirection dir, int directionStride, string stateName, bool movement) {'),
        ('                operation.Operation.ApplyToFrame(pixels, imageSpan, frameIndex, dir, bounds);',
         '                if (operation.Operation is DreamIconOperationBlendImage imageBlend)\n                    imageBlend.ApplyToFrame(pixels, imageSpan, frameIndex, dir, bounds, stateName, movement);\n                else\n                    operation.Operation.ApplyToFrame(pixels, imageSpan, frameIndex, dir, bounds);'),
        ('    private readonly ParsedDMIState? _blendingState;',
         '    private readonly ParsedDMIState? _blendingState;\n    private readonly ParsedDMIState[] _blendingStates;'),
        ('        _blendingState = blendingIcon.DMI.States.Values.FirstOrDefault();',
         '        _blendingState = blendingIcon.DMI.States.Values.FirstOrDefault();\n        _blendingStates = blendingIcon.DMI.GetAllStates().Values.ToArray();'),
    ]
    for before, after in variant_changes:
        if text.count(before) != 1:
            raise RuntimeError('Blend variant source changed; review: '+before)
        text = text.replace(before, after)
    begin = text.index('    public override void OnApply(DreamIcon icon) {', text.index('public sealed class DreamIconOperationBlendImage'))
    end = text.index('        if (_blendingState == null)\n            return;\n        if (!_blendingState.Directions.TryGetValue', begin)
    section = text[begin:end]
    section = section.replace('        if (icon.States.Values.Any(state =>\n                _blendingState.FrameCount > state.Frames ||\n                _blendingState.Directions.Keys.Any(dir => !state.Directions.ContainsKey(dir))))', '        if (icon.States.Any(pair => {\n                var source = SelectBlendingState(pair.Key.Name, pair.Value.Movement);\n                return source != null && (source.FrameCount > pair.Value.Frames ||\n                    source.Directions.Keys.Any(dir => !pair.Value.Directions.ContainsKey(dir)));\n            }))')
    section = section.replace('foreach (var state in icon.States.Values) {',
        'foreach (var pair in icon.States) {\n            var state = pair.Value;\n            var source = SelectBlendingState(pair.Key.Name, state.Movement);\n            if (source == null)\n                continue;')
    section = section.replace('_blendingState.Directions', 'source.Directions').replace('_blendingState.FrameCount', 'source.FrameCount').replace('_blendingState.Rewind', 'source.Rewind')
    section = section.replace('    public override void ApplyToFrame(Rgba32[] pixels, int imageSpan, int frame, AtomDirection dir, UIBox2i bounds) {',
        '    public override void ApplyToFrame(Rgba32[] pixels, int imageSpan, int frame, AtomDirection dir, UIBox2i bounds) {\n        ApplySelectedState(pixels, imageSpan, frame, dir, bounds, _blendingState);\n    }\n\n    public void ApplyToFrame(Rgba32[] pixels, int imageSpan, int frame, AtomDirection dir, UIBox2i bounds, string stateName, bool movement) {\n        ApplySelectedState(pixels, imageSpan, frame, dir, bounds, SelectBlendingState(stateName, movement));\n    }\n\n    private ParsedDMIState? SelectBlendingState(string name, bool movement) {\n        return _blendingStates.FirstOrDefault(state => state.Name == name && state.Movement == movement)\n            ?? _blendingStates.FirstOrDefault(state => state.Name == name)\n            ?? _blendingState;\n    }\n\n    private void ApplySelectedState(Rgba32[] pixels, int imageSpan, int frame, AtomDirection dir, UIBox2i bounds, ParsedDMIState? source) {')
    apply_end = text.index('public sealed class DreamIconOperationBlendColor', end)
    tail = text[end:apply_end].replace('_blendingState', 'source')
    text = text[:begin] + section + tail + text[apply_end:]
    start = text.index('public sealed class DreamIconOperationTurn(')
    section = text[start:]
    section = section.replace('copy[y, x] = pixels[dstPixelPosition];', 'copy[y - bounds.Top, x - bounds.Left] = pixels[dstPixelPosition];')
    section = section.replace('90 => copy[size - 1 - x, y]', '90 => copy[size - 1 - (x - bounds.Left), y - bounds.Top]')
    section = section.replace('180 => copy[size - 1 - y, size - 1 - x]', '180 => copy[size - 1 - (y - bounds.Top), size - 1 - (x - bounds.Left)]')
    section = section.replace('270 => copy[x, size - 1 - y]', '270 => copy[x - bounds.Left, size - 1 - (y - bounds.Top)]')
    section = section.replace('_ => copy[y, x]', '_ => copy[y - bounds.Top, x - bounds.Left]')
    icon_source.write_text(text[:start] + section)
    icon_object = work/'src/Objects/Types/DreamObjectIcon.cs'
    object_text = icon_object.read_text().replace('state, dir, frame, isConstructor: true)',
                                                 'state, dir, frame, moving, isConstructor: true)')
    copy_call = 'Icon.InsertStates(iconObj.Icon.GenerateDMI(), state, dir, frame, moving, isConstructor: true);'
    if object_text.count(copy_call) != 1:
        raise RuntimeError('Filtered icon-object constructor changed; review latent frame delay')
    object_text = object_text.replace(copy_call,
        'Icon.InsertStates(iconObj.Icon.GenerateDMI(), state, dir, frame, moving, isConstructor: true, sourceIcon: iconObj.Icon);')
    icon_object.write_text(object_text)
    icon_native = work/'src/Procs/Native/DreamProcNativeIcon.cs'
    native_text = icon_native.read_text()
    before = 'Icon.InsertStates(iconRsc, iconState, dir, frame);'
    if native_text.count(before) != 1:
        raise RuntimeError('Upstream Insert changed; review explicit movement destination semantics')
    native_text = native_text.replace(before, 'Icon.InsertStates(iconRsc, iconState, dir, frame, moving, insertion: true);')
    icon_native.write_text(native_text)
    native_text = root_natives.read_text().replace('iconObj.Icon.States.Keys.ToArray()',
        'iconObj.Icon.States.Keys.Select(key => key.Name).Distinct().ToArray()')
    root_natives.write_text(native_text)
    value_source = work/'src/DreamValue.cs'
    text = value_source.read_text().replace('if (_refValue is T dreamObjectValue) {', 'if (_refValue is T dreamObjectValue && !dreamObjectValue.Deleted) {')
    text = text.replace('return _refValue is T;', 'return _refValue is T obj && !obj.Deleted;')
    value_source.write_text(text)

    savefile = work/'src/Objects/Types/DreamObjectSavefile.cs'
    text = savefile.read_text().replace('public sealed class DreamObjectSavefile :',
                                      'public sealed partial class DreamObjectSavefile :')
    text = text.replace('[JsonPolymorphic]', '[JsonPolymorphic]\n'
        '    [JsonDerivedType(typeof(SfGraphReference), typeDiscriminator: "graphref")]\n'
        '    [JsonDerivedType(typeof(SfGraphTable), typeDiscriminator: "graphtable")]')
    text = text.replace('return new DreamValue(DreamResourceManager.CreateResource(Convert.FromBase64String(sfDreamFileValue.Data)));',
                        'return RestoreFileValue(sfDreamFileValue);')
    text = text.replace('Ext = dreamResource.ResourcePath!.Split(\'.\').Last(),',
                        'Ext = dreamResource is IconResource ? "dmi" : Path.GetExtension(dreamResource.ResourcePath),')
    # Native Write/Read graph fields also remain readable through F["field"].
    text = text.replace('return DeserializeJsonValue(SeekTo(index, true));',
        'if (CurrentDir.TryGetValue(GraphKey, out var graph) && graph is SfGraphTable table && _readGraph == null) {\n'
        '            _readGraph = new ReadGraph(table);\n'
        '            try { return DecodeGraphValue(SeekTo(index, true)); }\n'
        '            finally { foreach (var v in _readGraph.Values.Values) v.Dispose(); _readGraph = null; }\n'
        '        }\n'
        '        return DecodeGraphValue(SeekTo(index, true));')
    savefile.write_text(text)
    datum = work/'src/Objects/DreamObject.cs'
    text = datum.read_text()
    text = text.replace('public virtual bool IsSaved(string name) {',
        'public virtual bool IsSaved(string name) {\n'
        '        if (this is Types.DreamObjectMob && name == "client") return false;\n'
        '        if (this is Types.DreamObjectAtom && name == "appearance") return false;\n'
        '        if (this is Types.DreamObjectMovable && name == "locs") return false;')
    # Static/map tag values must enter the runtime tag index before New().
    text = text.replace('RefId = DreamRefManager.GetRef(this);',
        'RefId = DreamRefManager.GetRef(this);\n'
        '        if (objectDefinition.Variables.TryGetValue("tag", out var initialTag) && initialTag.TryGetValueAsString(out var tag))\n'
        '            Tag = tag;')
    datum.write_text(text)
    map_path = work/'src/Map/DreamMapManager.cs'
    original_map = map_path.read_text(encoding='utf-8-sig')
    start = original_map.index('                        // TODO: Use modified types during compile')
    end = original_map.index('                        obj.DecRef();', start) + len('                        obj.DecRef();')
    map_text = original_map[:start] + (
        '                        var seed = new MapSeed(objDef, blockX, blockY, block.Z);\n'
        '                        _mapSeeds.Add(seed);\n'
        '                        CreateSeedInstance(seed, turf);') + original_map[end:]
    map_path.write_text(map_text)
    shutil.copy2(ROOT/'engine/MapRepopulation.cs', work/'src/Map/MapRepopulation.cs')
    world_natives = work/'src/Procs/Native/DreamProcNativeWorld.cs'
    text = world_natives.read_text(encoding='utf-8-sig')
    text = text.replace('    [DreamProc("Reboot")]',
        '    [DreamProc("Repop")]\n'
        '    public static DreamValue NativeProc_Repop(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {\n'
        '        ((OpenDreamRuntime.Map.DreamMapManager)bundle.MapManager).Repopulate();\n'
        '        return DreamValue.Null;\n'
        '    }\n\n    [DreamProc("Reboot")]')
    text = text.replace('server.Shutdown("/world.Reboot() was called but restarting is very broken");',
        'var request = Environment.GetEnvironmentVariable("DM_REBOOT_REQUEST");\n'
        '        if (string.IsNullOrEmpty(request))\n'
        '            throw new InvalidOperationException("World reboot requires the local server supervisor");\n'
        '        File.WriteAllText(request, "reboot");\n'
        '        server.Shutdown("World reboot requested");')
    world_natives.write_text(text)
    movable = work/'src/Objects/Types/DreamObjectMovable.cs'
    original = movable.read_text()
    text = original
    for axis in 'XYZ':
        anchor = f'value.MustGetValueAsInteger() : {axis};'
        if text.count(anchor) != 1:
            raise RuntimeError('Upstream coordinate setter changed')
        text = text.replace(anchor, f'value.MustGetValueAsInteger() : Math.Max(1, {axis});')
    text = text.replace('    protected override void HandleDeletion() {',
        '    protected override void HandleDeletion() {\n        foreach (var child in OrderedContents.ToArray()) child.Delete();')
    text = text.replace('public DreamObjectAtom? Loc;',
                        'public DreamObjectAtom? Loc;\n    public readonly List<DreamObjectMovable> OrderedContents = new();')
    text = text.replace('        var oldLoc = Loc;',
        '        var oldLoc = Loc;\n'
        '        if (oldLoc is DreamObjectMovable oldOwner) oldOwner.OrderedContents.Remove(this);\n'
        '        if (loc is DreamObjectMovable newOwner) InsertContent(newOwner.OrderedContents);')
    # BYOND keeps non-mobs before mobs, arrival order within each group.
    # Same-loc assignment still removes/reinserts at that group's end.
    before_turf_add = '                turf.Cell.Movables.Add(this);'
    before_screen_loc = '    private void SetScreenLoc(string? screenLoc) {'
    if text.count(before_turf_add) != 1 or text.count(before_screen_loc) != 1:
        raise RuntimeError('Upstream contents insertion changed; review partition order')
    text = text.replace(before_turf_add, '                InsertContent(turf.Cell.Movables);')
    text = text.replace(before_screen_loc, '''    private void InsertContent(List<DreamObjectMovable> contents) {
        if (this is not DreamObjectMob) {
            int firstMob = contents.FindIndex(static item => item is DreamObjectMob);
            if (firstMob >= 0) {
                contents.Insert(firstMob, this);
                return;
            }
        }
        contents.Add(this);
    }

''' + before_screen_loc)
    movable.write_text(text)
    lists = work/'src/Objects/Types/DreamList.cs'
    list_text = lists.read_text()
    start = list_text.index('public sealed class MovableContentsList(')
    end = list_text.index('// proc args list', start)
    section = list_text[start:end]
    a = section.index('        using var childEnumerator = transform.ChildEnumerator;')
    b = section.index('    public override List<DreamValue> GetValues()', a)
    section = section[:a] + """        var child = owner.OrderedContents[index - 1];
        child.IncRef();
        return new DreamValue(child);
    }

""" + section[b:]
    a = section.index('        using var childEnumerator = transform.ChildEnumerator;')
    b = section.index('    public override void SetValue(', a)
    section = section[:a] + """        foreach (var child in owner.OrderedContents)
            yield return new DreamValue(child);
    }

    public override int FindValue(DreamValue value, int start = 1, int end = 0) {
        if (end == 0 || end > owner.OrderedContents.Count + 1) end = owner.OrderedContents.Count + 1;
        for (int i = Math.Max(start, 1); i < end; i++)
            if (new DreamValue(owner.OrderedContents[i-1]).Equals(value)) return i;
        return 0;
    }

""" + section[b:]
    section = section.replace('transform.ChildCount', 'owner.OrderedContents.Count')
    lists.write_text(list_text[:start] + section + list_text[end:])
    (ROOT/'engine/nullspace-coordinates.patch').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), text.splitlines(True), fromfile='DreamObjectMovable.cs', tofile='DreamObjectMovable.cs')))
    shutil.copy2(ROOT/'engine/DatumPersistence.cs', work/'src/Objects/Types/DatumPersistence.cs')
    shutil.copy2(ROOT/'engine/DreamProcNativeDatum.cs', work/'src/Procs/Native/DreamProcNativeDatum.cs')
    natives = work/'src/Procs/Native/DreamProcNative.cs'
    text = natives.read_text(encoding='utf-8-sig')
    text = text.replace('        objectTree.SetGlobalNativeProc(DreamProcNativeRoot.NativeProc_get_step_to);',
        '        objectTree.SetGlobalNativeProc(DreamProcNativeWander.NativeProc_get_step_rand);\n'
        '        objectTree.SetGlobalNativeProc(DreamProcNativeRoot.NativeProc_get_step_to);')
    anchor = '        objectTree.SetNativeProc(objectTree.Savefile, DreamProcNativeSavefile.NativeProc_ExportText);'
    if text.count(anchor) != 1:
        raise RuntimeError('Upstream native registration changed')
    text = text.replace('        SetOverridableNativeProc(objectTree, objectTree.World, DreamProcNativeWorld.NativeProc_Reboot);',
                        '        SetOverridableNativeProc(objectTree, objectTree.World, DreamProcNativeWorld.NativeProc_Reboot);\n'
                        '        SetOverridableNativeProc(objectTree, objectTree.World, DreamProcNativeWorld.NativeProc_Repop);')
    natives.write_text(text.replace(anchor,
        '        var oldRead = objectTree.Datum.ObjectDefinition.GetProc("Read");\n'
        '        var oldWrite = objectTree.Datum.ObjectDefinition.GetProc("Write");\n'
        '        objectTree.SetNativeProc(objectTree.Datum, DreamProcNativeDatum.NativeProc_Read);\n'
        '        objectTree.SetNativeProc(objectTree.Datum, DreamProcNativeDatum.NativeProc_Write);\n'
        '        var newRead = objectTree.Datum.ObjectDefinition.GetProc("Read");\n'
        '        var newWrite = objectTree.Datum.ObjectDefinition.GetProc("Write");\n'
        '        foreach (var proc in objectTree.Procs) {\n'
        '            if (proc != newRead && proc.SuperProc == oldRead) proc.SuperProc = newRead;\n'
        '            if (proc != newWrite && proc.SuperProc == oldWrite) proc.SuperProc = newWrite;\n'
        '        }\n'+anchor))
    connection = work/'src/DreamConnection.cs'
    text = connection.read_text()
    anchor = '        // Prune any remaining formatting\n        var message = value.Stringify();'
    if text.count(anchor) != 1:
        raise RuntimeError('Upstream output handling changed; review sound file output')
    # BYOND plays a sound file sent with << (the game's `view() << 'P1.wav'`)
    # like sound(file); upstream printed the file path into the output box.
    connection.write_text(text.replace(anchor,
        '        if (value.TryGetValueAsDreamResource(out var outputResource) && outputResource.ResourcePath is { } outputPath &&\n'
        '            (outputPath.EndsWith(".wav", StringComparison.OrdinalIgnoreCase) || outputPath.EndsWith(".ogg", StringComparison.OrdinalIgnoreCase))) {\n'
        '            Session?.Channel.SendMessage(new MsgSound {\n'
        '                ResourceId = outputResource.Id,\n'
        '                Format = outputPath.EndsWith(".ogg", StringComparison.OrdinalIgnoreCase) ? MsgSound.FormatType.Ogg : MsgSound.FormatType.Wav,\n'
        '                SoundData = new SoundData { Channel = 0, Volume = 100, Offset = 0, Repeat = 0, File = outputPath }\n'
        '            });\n'
        '            return;\n'
        '        }\n\n' + anchor))
    verbs = work/'src/ServerVerbSystem.cs'
    text = verbs.read_text(encoding='utf-8-sig')
    # A plain proc override of a verb stays that verb in BYOND (name, category,
    # hidden, src/range). The game's `client/North() ..()` overrides hid the
    # built-in `.north` name, so the arrow macros' `.north` matched nothing.
    start = text.index('    public void RegisterVerb(DreamProc verb) {')
    end = text.index('        verb.VerbId = _verbs.Count;', start)
    section = text[start:end]
    section = section.replace('            return;\n',
        '            return;\n\n        var meta = verb;\n        while (!meta.IsVerb && meta.SuperProc != null)\n            meta = meta.SuperProc;\n', 1)
    for old in ('verb.VerbSrc switch', 'Name = verb.VerbName,', 'Category = verb.VerbCategory ?? string.Empty,',
                'Invisibility = verb.Invisibility,', '(verb.Attributes & ProcAttributes.Hidden)',
                '(verb.Attributes & ProcAttributes.HidePopupMenu)', 'Range = verb.VerbRange ?? 0'):
        if section.count(old) != 1:
            raise RuntimeError('Upstream verb registration changed: ' + old)
        section = section.replace(old, old.replace('verb.', 'meta.'))
    text = text[:start] + section + text[end:]
    field = '    private readonly Dictionary<DreamConnection, List<(int, ClientObjectReference) /* verbId */>> _repeatingVerbs = new();'
    loop_return = ('                if (repeatingVerb.Value.Count == 0)\n                    return;')
    loop_skip = ('                if (src == null || !_verbIdToProc.TryGetValue(verbId, out var verb) || !CanExecute(client, src, verb))\n'
                 '                    return;\n\n                RunVerb(verb, $"repeating verb {verbId}", src, client);')
    register = ('        if (list.All(tuple => tuple.Item1 != msg.VerbId))\n            list.Add((msg.VerbId, msg.Src));')
    if any(text.count(s) != 1 for s in (field, loop_return, loop_skip, register)):
        raise RuntimeError('Upstream repeating verbs changed; review +REP key handling')
    # BYOND runs a +REP macro's command on key down and repeats it while held, so
    # a tap moves once. Upstream only ran it at the next server tick, dropping
    # taps released within one tick (arrow keys did nothing at 10 fps).
    text = text.replace(field, field + '\n    private readonly HashSet<(DreamConnection, int)> _repeatPressedThisTick = new();')
    text = text.replace(loop_return, '                if (repeatingVerb.Value.Count == 0)\n                    continue;')
    text = text.replace(loop_skip,
        '                if (_repeatPressedThisTick.Contains((client, verbId)))\n'
        '                    continue; // already ran on key down\n'
        '                if (src == null || !_verbIdToProc.TryGetValue(verbId, out var verb) || !CanExecute(client, src, verb))\n'
        '                    continue;\n\n                RunVerb(verb, $"repeating verb {verbId}", src, client);')
    text = text.replace('            foreach (var repeatingVerb in _repeatingVerbs) {',
        '            foreach (var repeatingVerb in _repeatingVerbs.ToArray()) {')
    text = text.replace('''                RunVerb(verb, $"repeating verb {verbId}", src, client);
            }
        }''', '''                RunVerb(verb, $"repeating verb {verbId}", src, client);
            }
            _repeatPressedThisTick.Clear();
        }''')
    text = text.replace(register,
        '        if (list.All(tuple => tuple.Item1 != msg.VerbId)) {\n'
        '            list.Add((msg.VerbId, msg.Src));\n'
        '            var pressed = _dreamManager.GetFromClientReference(conn, msg.Src);\n'
        '            if (pressed != null && _verbIdToProc.TryGetValue(msg.VerbId, out var pressedVerb) && CanExecute(conn, pressed, pressedVerb)) {\n'
        '                _repeatPressedThisTick.Add((conn, msg.VerbId));\n'
        '                RunVerb(pressedVerb, $"repeating verb {msg.VerbId}", pressed, conn);\n'
        '            }\n'
        '        }')
    verbs.write_text(text)
    mouse = work/'src/Input/MouseInputSystem.cs'
    text = mouse.read_text(encoding='utf-8-sig')
    old_delay = 'private readonly TimeSpan _doubleClickDelay = TimeSpan.FromMilliseconds(250);'
    old_check = ('        // Double click fires before the second Click() fires\n'
                 '        if (_timing.RealTime - connection.LastClickTime <= _doubleClickDelay) {')
    if text.count(old_delay) != 1 or text.count(old_check) != 1:
        raise RuntimeError('Upstream double-click handling changed')
    # Dream Seeker takes double-clicks from Windows: the second click within the
    # default 500 ms on the same spot and button, and a third click starts over.
    # Upstream paired any two clicks 250 ms apart by server receipt, so tick lag
    # dropped real double-clicks (item pickup, unit selection).
    text = text.replace(old_delay,
        'private readonly TimeSpan _doubleClickDelay = TimeSpan.FromMilliseconds(500);\n'
        '    private readonly Dictionary<DreamConnection, (DreamObjectAtom Atom, int Button, TimeSpan Time, bool Paired)> _lastClicks = new();')
    text = text.replace(old_check,
        '        // Double click fires before the second Click() fires\n'
        '        var button = e.Params.Right ? 2 : e.Params.Middle ? 3 : 1;\n'
        '        var now = _timing.RealTime;\n'
        '        var isDouble = _lastClicks.TryGetValue(connection, out var last) && !last.Paired &&\n'
        '                       last.Atom == atom && last.Button == button && now - last.Time <= _doubleClickDelay;\n'
        '        _lastClicks[connection] = (atom, button, now, isDouble);\n'
        '        if (isDouble) {')
    mouse.write_text(text)
    patches = []
    for changed in sorted((work/'src').rglob('*.cs')):
        relative = changed.relative_to(work/'src')
        original_file = upstream/relative
        old = original_file.read_text(encoding='utf-8-sig') if original_file.exists() else ''
        new = changed.read_text(encoding='utf-8-sig')
        if old != new:
            patches.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                           fromfile='a/OpenDreamRuntime/'+str(relative), tofile='b/OpenDreamRuntime/'+str(relative)))
    (ROOT/'engine/runtime-compatibility.patch').write_text(''.join(patches))
    project = ET.Element('Project', Sdk='Microsoft.NET.Sdk')
    props = ET.SubElement(project, 'PropertyGroup')
    for key, value in {'TargetFramework': 'net10.0', 'AssemblyName': 'OpenDreamRuntime',
                       'Nullable': 'enable', 'AllowUnsafeBlocks': 'true',
                       'EnableDefaultCompileItems': 'false', 'RestoreSources': ''}.items():
        ET.SubElement(props, key).text = value
    items = ET.SubElement(project, 'ItemGroup')
    ET.SubElement(items, 'Compile', Include='src/**/*.cs', Exclude='src/**/obj/**;src/**/bin/**')
    ET.SubElement(items, 'Analyzer', Include=str(generator_dir/'bin/Release/net10.0/Robust.Serialization.Generator.dll'))
    server = args.server.resolve()
    refs = {p.name: p for p in server.glob('*.dll')}
    refs.update({p.name: p for p in (server/'Resources/Assemblies').glob('*.dll')})
    refs.pop('OpenDreamRuntime.dll', None)
    refs['JetBrains.Annotations.dll'] = args.annotations.resolve()
    if args.shared_assembly:
        refs['OpenDreamShared.dll'] = args.shared_assembly.resolve()
    for name, path in sorted(refs.items()):
        ref = ET.SubElement(items, 'Reference', Include=name[:-4])
        ET.SubElement(ref, 'HintPath').text = str(path)
        ET.SubElement(ref, 'Private').text = 'false'
    project_path = work/'OpenDreamRuntime.csproj'
    ET.ElementTree(project).write(project_path, encoding='unicode')
    with (ROOT/'reports/engine-build.log').open('w') as log:
        subprocess.run([str(args.sdk.resolve()), 'build', str(project_path), '-c', 'Release',
                        '--ignore-failed-sources'], env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    built = work/'bin/Release/net10.0/OpenDreamRuntime.dll'
    output = args.output.resolve() if args.output else ROOT/'engine/OpenDreamRuntime.dll'
    output.parent.mkdir(exist_ok=True)
    staged_output = output.with_suffix('.dll.pending')
    shutil.copy2(built, staged_output)
    staged_output.replace(output)
    original = server/'Resources/Assemblies/OpenDreamRuntime.dll'
    if args.install:
        backup = original.with_suffix('.dll.upstream')
        if not backup.exists():
            shutil.copy2(original, backup)
        staged_runtime = original.with_suffix('.dll.pending')
        shutil.copy2(built, staged_runtime)
        staged_runtime.replace(original)
    report = {'patches': ['BYOND mob.New usr context', 'FIFO ordering of equal-tick delays', 'Route unnamed browse() to skin default browser', 'Native datum Read/Write with object graph persistence and built-in field exclusions', 'Restore coordinates from nullspace using BYOND axis defaults', 'Index static and map tags before constructors', 'Repopulate deleted original map objects with original definitions and positions', 'Explicit world reboot handoff to local server supervisor', 'Text file append/newline semantics and fresh file reads', 'BYOND MT19937 random sequence and pick projections', 'Independent wandering randomness and measured open-terrain forward bias; edge-following still open', 'Implicit self-call argument forwarding', 'Stable ordered movable contents and container deletion', 'Deleted object type checks', 'No-op text recipients', 'Opt-in packaged host save before shutdown using original SaveUnits', 'Resource icon rotation and local atlas frame indexing', 'Generated DMI frame-major direction interleaving for stable composed sprite facing', 'Dream Seeker double-click pairing: same atom and button within 500 ms; a third click starts over', 'Sound files sent with << play as sounds instead of printing their path', '+REP macros run on key down then repeat while held, so a key tap moves once', 'Proc overrides of verbs keep the verb name and settings (client/North() keeps .north)', 'Stat panels list statpanel(panel, list) items and show object suffixes'], 'game_source_modified': False,
              'upstream_file_sha256': hashlib.sha256((upstream/'Procs/InitDreamObject.cs').read_bytes()).hexdigest(),
              'runtime_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
              'installed': args.install, 'installed_path': str(original) if args.install else None,
              'output_path': str(output)}
    report['patches'].append('Preserve movement-only animation metadata through icon generation and copy')
    report['patches'].append('Preserve same-name idle/walking variants; BYOND constructor filters and explicit Insert movement destinations')
    report['patches'].append('Only world for-loops opt in to exact /atom/movable inclusion of the separate mob registry; locate and existing helper ABI stay unchanged')
    report['patches'].append('Turf and movable contents keep non-mobs before mobs with stable arrival order in each group')
    report['shared_sha256'] = hashlib.sha256(refs['OpenDreamShared.dll'].read_bytes()).hexdigest()
    (ROOT/'reports/engine-build.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
