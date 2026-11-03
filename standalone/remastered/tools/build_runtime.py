#!/usr/bin/env python3
"""Build Remastered's own OpenDream runtime: the Classic engine fixes, the game clock (pause and speed,
engine/clock/RemasterClock.cs) and the native procs (engine/core/ + engine/game-botd/, planning/ENGINE_PLAN.md).

The Classic build script and its patches are copied into a staging folder and run
there, so nothing in ../replica is written. The result is engine/server/OpenDreamRuntime.dll,
which tools/build_app.py puts into the app's server.
"""
import argparse, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPLICA = ROOT.parent/'replica'
A = '/private/tmp/dm-runtime-audit'
# The main engine since 2026-10-24 (planning/ENGINE_PLAN.md): the in-repo OpenDream checkout at upstream 2e58532 (the
# 2026-10-18 "latest", with upstream #2723 and #2734 over the 5b186c2 the earlier engine was built from), our patches,
# the clock and the native procs. Only the .NET 10 SDK lives outside the repo (dotnet-install.sh, 10.0.402): in ~/.dotnet10
# since 2026-10-28 (the owner: "Yes, keep them"), which a reboot doesn't wipe.
OPENDREAM = ROOT.parent/'opendream'
SOURCE_COMMIT = '2e58532'
DEFAULTS = dict(source=str(OPENDREAM), robust_source=str(OPENDREAM/'RobustToolbox'),
                server=str(REPLICA/'runtime/macos-x64/server'), sdk=str(Path.home()/'.dotnet10/dotnet'), annotations=str(ROOT.parent/'opendream-3d/bin/Content.Server/JetBrains.Annotations.dll'),
                build_dir=f'{A}/remastered-runtime-build')

CLOCK = r'''
    # --- Remastered: the game clock (pause / speed) ---
    shutil.copy2(Path(os.environ['RM_CLOCK_CS']), work/'src/RemasterClock.cs')
    d = work/'src/Procs/ProcScheduler.Delays.cs'; t = d.read_text(encoding='utf-8-sig')
    n = t.count('_gameTiming.CurTick.Value')
    if n < 2: raise RuntimeError('scheduler changed; review the clock patch')
    d.write_text(t.replace('_gameTiming.CurTick.Value', 'RemasterClock.Now'))
    m = work/'src/DreamManager.cs'; t = m.read_text(encoding='utf-8-sig')
    if t.count('_procScheduler.Process();') != 1: raise RuntimeError('DreamManager.Update changed; review the clock patch')
    m.write_text(t.replace('_procScheduler.Process();', 'RemasterClock.Run(_procScheduler.Process);'))
    w = work/'src/Objects/Types/DreamObjectWorld.cs'; t = w.read_text(encoding='utf-8-sig')
    a = 'value = new DreamValue((_gameTiming.CurTick.Value - DreamManager.InitializedTick.Value) * TickLag);'
    if t.count(a) != 1: raise RuntimeError('world.time changed; review the clock patch')
    t = t.replace(a, 'value = new DreamValue((RemasterClock.Now - DreamManager.InitializedTick.Value) * TickLag);')
    # world.game_state (a hub setting this engine never uses) carries the speed
    b = 'case "game_state":\n'
    if t.count(b) != 1: raise RuntimeError('world SetVar changed; review the clock patch')
    t = t.replace(b, 'case "game_state" when value.TryGetValueAsInteger(out var rmSpeed) && (RemasterClock.Speed = Math.Clamp(rmSpeed, 0, RemasterClock.MaxSpeed)) >= 0:\n', 1)
    w.write_text(t)
'''

NATIVE = r'''
    # --- Remastered: native procs (engine/native/*.cs, planning/ENGINE_PLAN.md), unless --no-native ---
    if os.environ.get('RM_NATIVE_DIR'):
        for cs in sorted(Path(os.environ['RM_NATIVE_DIR']).glob('*.cs')):
            shutil.copy2(cs, work/'src/Procs/Native'/cs.name)
        nat = work/'src/Procs/Native/DreamProcNative.cs'; t = nat.read_text(encoding='utf-8-sig')
        anchor = '        objectTree.SetGlobalNativeProc(DreamProcNativeRoot.NativeProc_get_step_to);'
        if t.count(anchor) != 1: raise RuntimeError('native proc setup changed; review the native patch')
        nat.write_text(t.replace(anchor, anchor + '\n        RmNative.Register(objectTree);', 1))
'''

MEMORY = r'''
    # --- Remastered: memory (planning/ENGINE_PLAN.md, memory), unless --no-memory ---
    # A turf's contents list is made when DM code asks for turf.contents, not for each of the map's 4 million tiles at
    # load (it was ~150 of the ~560 bytes a tile took). The engine's own readers of a tile's things (DM for-in over a
    # turf, "x in turf", locate(type) in turf, view/range, area contents) read the tile's cell directly, as the list did.
    if os.environ.get('RM_MEMORY') == '1':
        def rm_edit(rel, pairs):
            f = work/'src'/rel; t = f.read_text(encoding='utf-8-sig')
            for a, b, n in pairs:
                if t.count(a) != n: raise RuntimeError(f'{rel} changed; review the memory patch: {a[:70]!r} ({t.count(a)} found, {n} expected)')
                t = t.replace(a, b)
            f.write_text(t)
        rm_edit('Objects/Types/DreamObjectTurf.cs', [
            ('    public readonly TurfContentsList Contents;\n',
             '    private TurfContentsList? _rmContents;   // Remastered: made when DM code asks for it\n'
             '    public TurfContentsList Contents => _rmContents ??= new TurfContentsList(ObjectTree.List.ObjectDefinition, this);\n'
             '    public IEnumerable<DreamValue> EnumerateContents() { foreach (var movable in Cell.Movables) yield return new(movable); }\n', 1),
            ('        Contents = new TurfContentsList(ObjectTree.List.ObjectDefinition, this);\n', '', 1),
        ])
        rm_edit('Procs/Native/DreamProcNativeHelpers.cs', [
            ('turf.Contents.EnumerateValues()', 'turf.EnumerateContents()', 2),
            ('turfCenter.Contents.EnumerateValues()', 'turfCenter.EnumerateContents()', 1),
        ])
        rm_edit('Objects/Types/DreamList.cs', [
            ('            int contentsLength = turf.Contents.GetLength();', '            int contentsLength = turf.Cell.Movables.Count;', 1),
            ('                var contentsItem = turf.Contents.GetValue(new(index));',
             '                var rmMovable = turf.Cell.Movables[index - 1];\n                rmMovable.IncRef();\n                var contentsItem = new DreamValue(rmMovable);', 1),
            ('            foreach (var content in turf.Contents.EnumerateValues())', '            foreach (var content in turf.EnumerateContents())', 1),
            ('            length += turf.Contents.GetLength();', '            length += turf.Cell.Movables.Count;', 1),
        ])
        rm_edit('Procs/DMOpcodeHandlers.cs', [
            ('                    if (dreamObject is DreamObjectAtom) {\n                        using var contents = dreamObject.GetVariable("contents");',
             '                    if (dreamObject is DreamObjectTurf rmTurf) {   // Remastered: its things, without making its contents list\n'
             '                        var rmMovables = rmTurf.Cell.Movables;\n'
             '                        var rmValues = new DreamValue[rmMovables.Count];\n'
             '                        for (var rmI = 0; rmI < rmValues.Length; rmI++) {\n'
             '                            rmValues[rmI] = new DreamValue(rmMovables[rmI]);\n'
             '                            rmValues[rmI].IncRef();\n'
             '                        }\n'
             '                        return filterType == null ? new DreamValueArrayEnumerator(rmValues, null) : new FilteredDreamValueArrayEnumerator(rmValues, null, filterType);\n'
             '                    }\n\n'
             '                    if (dreamObject is DreamObjectAtom) {\n                        using var contents = dreamObject.GetVariable("contents");', 1),
            ('                    case DreamObjectAtom or DreamObjectWorld:\n                        using (var contents = listObject.GetVariable("contents"))',
             '                    case DreamObjectTurf rmTurf:   // Remastered: on this tile, without making its contents list\n'
             '                        state.Push(new DreamValue(value.TryGetValueAsDreamObject<DreamObjectMovable>(out var rmInMovable) && rmInMovable.Loc == rmTurf ? 1 : 0));\n'
             '                        return ProcStatus.Continue;\n'
             '                    case DreamObjectAtom or DreamObjectWorld:\n                        using (var contents = listObject.GetVariable("contents"))', 1),
            ('            DreamList? containerList;\n            if (container is DreamObjectAtom) {\n                using var contents = container.GetVariable("contents");',
             '            if (container is DreamObjectTurf rmTurf) {   // Remastered: a tile\'s things, without making its contents list\n'
             '                if (value.TryGetValueAsString(out var rmRefString)) {\n'
             '                    using var rmRefValue = state.Proc.RefManager.LocateRef(rmRefString);\n'
             '                    state.Push(rmRefValue.TryGetValueAsDreamObject<DreamObjectMovable>(out var rmRefMovable) && rmRefMovable.Loc == rmTurf ? rmRefValue : DreamValue.Null);\n'
             '                } else if (value.TryGetValueAsType(out var rmAncestor)) {\n'
             '                    var rmFound = DreamValue.Null;\n'
             '                    foreach (var rmMovable in rmTurf.Cell.Movables) {\n'
             '                        if (rmMovable.ObjectDefinition.IsSubtypeOf(rmAncestor)) {\n'
             '                            rmFound = new DreamValue(rmMovable);\n'
             '                            break;\n'
             '                        }\n'
             '                    }\n'
             '                    state.Push(rmFound);\n'
             '                } else {\n'
             '                    state.Push(value.TryGetValueAsDreamObject<DreamObjectMovable>(out var rmValueMovable) && rmValueMovable.Loc == rmTurf ? value : DreamValue.Null);\n'
             '                }\n'
             '                return ProcStatus.Continue;\n'
             '            }\n\n'
             '            DreamList? containerList;\n            if (container is DreamObjectAtom) {\n                using var contents = container.GetVariable("contents");', 1),
        ])
'''

VER = r'''
    # --- Remastered: change counters (engine/native/RmVer.cs: rm_chunk_ver, rm_ver; the 3D view's sends of what
    # changed), with the native procs, unless --no-ver. Every DM var write, animate(), a turf replaced on the map, a
    # movable's move and an atom's look set tell RmVer.
    # (only when the native procs include RmVer.cs, so a build from an engine/native without it still builds)
    if os.environ.get('RM_NATIVE_DIR') and os.environ.get('RM_VER') == '1' and (Path(os.environ['RM_NATIVE_DIR'])/'RmVer.cs').exists():
        def rm_ver_edit(rel, pairs):
            f = work/'src'/rel; t = f.read_text(encoding='utf-8-sig')
            for a, b in pairs:
                if t.count(a) != 1: raise RuntimeError(f'{rel} changed; review the change-counter patch: {a[:70]!r} ({t.count(a)} found)')
                t = t.replace(a, b)
            f.write_text(t)
        tell = 'global::OpenDreamRuntime.Procs.Native.RmVer'
        # engine M2 (load-asleep-1030): a write of exactly the default to a name with no own entry stores nothing
        # (engine/compact SetVariableValue, RmSkipped): that is the same value, so no change, as when the entry was there
        rm_cp_text = Path(os.environ['RM_COMPACT_PATCH']).read_text() if os.environ.get('RM_COMPACT_PATCH') else ''
        rm_skip = 'RmSkippedName' in rm_cp_text
        rm_skip_reset = '        RmSkipped = null;   // Remastered (engine M2): set by SetVariableValue when it stores nothing\n' if rm_skip else ''
        rm_skip_check = '        if (ReferenceEquals(RmSkipped, this) && RmSkippedName == name) rmSame = true;   // Remastered (engine M2): the default, no entry: no change\n' if rm_skip else ''
        rm_ver_edit('Objects/DreamObject.cs', [
            # a number, text or object (not a list) written again with the same value is no change (lists always count: one
            # changed in place and written back is seen as before). The same object again (a walk setting its destination
            # each step, ~1,500 writes a second with 2,000 units walking) is the same value: v31, the owner, 10-31
            ('        SetVar(name, value);\n    }\n', f'        var rmSame = (value.Type == DreamValue.DreamValueType.Float || value.Type == DreamValue.DreamValueType.String || (value.TryGetValueAsDreamObject(out var rmObj) && rmObj is not DreamList)) && Variables != null && Variables.TryGetValue(name, out var rmOld) && rmOld.Equals(value);\n'
             f'        var rmWas = {tell}.Writing;\n        {tell}.Writing = this;   // Remastered: a look this write changes is the write\'s (RmVer.cs Looked, v31)\n'
             + rm_skip_reset +
             f'        try {{ SetVar(name, value); }} finally {{ {tell}.Writing = rmWas; }}\n'
             + rm_skip_check +
             f'        if (!rmSame) {tell}.Written(this, name);   // Remastered: change counters (a quiet name, or the same value: none; RmVer.cs)\n    }}\n'),
        ])
        rm_ver_edit('Objects/Types/DreamObjectMovable.cs', [
            ('    public DreamObjectAtom? Loc;\n',
             f'    public DreamObjectAtom? Loc;\n    public int RmChanges = {tell}.NextFresh();   // Remastered: moves when it or anything in it changes (RmVer.cs)\n'
             f'    public int RmState = {tell}.NextFresh();   // Remastered: the same less its own steps and the names a game calls motion (RmVer.cs, v31)\n'
             f'    public int RmShown = {tell}.NextFresh();   // Remastered: the state less the names a game\'s views don\'t draw (RmVer.cs, v35)\n'
             '    public object? RmKept;   // Remastered: what natives read of it, kept while RmChanges stands (RmKept.cs, v23)\n'),
            ('    public void SetLoc(DreamObjectAtom? loc) {\n        var oldLoc = Loc;\n',
             f'    public void SetLoc(DreamObjectAtom? loc) {{\n        {tell}.Moved(this, loc);   // Remastered: change counters\n        var oldLoc = Loc;\n'),
        ])
        rm_ver_edit('Map/DreamMapManager.cs', [
            ('        cell.Turf.SetTurfType(type);\n', f'        cell.Turf.SetTurfType(type);\n        {tell}.TurfReplaced(cell.Turf);   // Remastered: change counters\n'),
        ])
        rm_ver_edit('AtomManager.cs', [
            ('    public void SetAtomAppearance(DreamObject atom, MutableAppearance appearance) {\n',
             f'    public void SetAtomAppearance(DreamObject atom, MutableAppearance appearance) {{\n        {tell}.Looked(atom);   // Remastered: change counters\n'),
            ('    public void AnimateAppearance(DreamObject atom, TimeSpan duration, AnimationEasing easing, int loop, AnimationFlags flags, int delay, bool chainAnim, Action<MutableAppearance> animate) {\n',
             f'    public void AnimateAppearance(DreamObject atom, TimeSpan duration, AnimationEasing easing, int loop, AnimationFlags flags, int delay, bool chainAnim, Action<MutableAppearance> animate) {{\n        {tell}.Written(atom);   // Remastered: change counters\n'),
        ])
'''

TICKGC = r'''
    # --- Remastered: garbage collection between ticks (engine/gc/RemasterTickGC.cs, engine v6), with --tick-gc ---
    # Each tick runs in a no-GC region; at the end of a tick (the frame update after it) the region ends, gen0 is collected
    # if the time before the next tick covers it, and the next tick's region opens. RM_TICK_GC=0 turns it off at run time.
    if os.environ.get('RM_TICK_GC_CS'):
        shutil.copy2(Path(os.environ['RM_TICK_GC_CS']), work/'src/RemasterTickGC.cs')
        e = work/'src/EntryPoint.cs'; t = e.read_text(encoding='utf-8-sig')
        a = '            if (level == ModUpdateLevel.PostEngine) {\n'
        if t.count(a) != 1: raise RuntimeError('EntryPoint.Update changed; review the tick GC patch')
        t = t.replace(a, '            if (level == ModUpdateLevel.FramePostEngine) RemasterTickGC.AfterTick();   // Remastered: GC between ticks\n' + a, 1)
        b = '            _dreamManager.Shutdown();\n'
        if t.count(b) != 1: raise RuntimeError('EntryPoint.Shutdown changed; review the tick GC patch')
        e.write_text(t.replace(b, '            RemasterTickGC.Stop();\n' + b, 1))
'''

ASSOC = r'''
    # --- Remastered: a membership index for lists (engine/assoc/dreamlist_index.py, engine v6), with --assoc-index ---
    # `x in L`, `L[x] = v`, Find and removing a missing element stop scanning big lists. RM_ASSOC_INDEX=0 turns it off.
    if os.environ.get('RM_ASSOC_PATCH'):
        rm_patch = {}
        exec(Path(os.environ['RM_ASSOC_PATCH']).read_text(), rm_patch)
        f = work/'src/Objects/Types/DreamList.cs'; t = f.read_text(encoding='utf-8-sig')
        for a, b, n in rm_patch['PAIRS']:
            if t.count(a) != n: raise RuntimeError(f'DreamList.cs changed; review the list index patch: {a[:70]!r} ({t.count(a)} found, {n} expected)')
            t = t.replace(a, b)
        f.write_text(t)
'''

MAPTRIM = r'''
    # --- Remastered: the areas' turf sets trimmed once the map has loaded (v7 candidate; map-memory's finding), with --map-trim ---
    # While the levels are made every turf is in the world's default area, and its HashSet keeps that room after the map's
    # own areas take their turfs: room for 8.5 million turfs for 4 million on the user's world. TrimExcess on each area's
    # set at the end of LoadMaps gives it back (-75 MB of heap with every tile awake, planning/MAP_MEMORY.md 8). Sets only
    # lose spare room; what they hold and every lookup are unchanged.
    if os.environ.get('RM_MAP_TRIM') == '1':
        f = work/'src/Map/DreamMapManager.cs'; t = f.read_text(encoding='utf-8-sig')
        a = '                    LoadMapAreasAndTurfs(block, map.CellDefinitions);\n                }\n            }\n        }\n    }\n'
        if t.count(a) != 1: raise RuntimeError(f'DreamMapManager.LoadMaps changed; review the map trim patch ({t.count(a)} found)')
        b = ('                    LoadMapAreasAndTurfs(block, map.CellDefinitions);\n                }\n            }\n        }\n\n'
             '        // Remastered (v7): the areas\' turf sets keep the room the default area had while the levels were made; give it back\n'
             '        foreach (var atom in _atomManager.EnumerateAtoms(_objectTree.Area))\n'
             '            if (atom is DreamObjectArea area) area.Turfs.TrimExcess();\n    }\n')
        f.write_text(t.replace(a, b, 1))
'''

WATCH = r'''
    # --- Remastered: watched variables (RmWatch.cs: rm_watch, rm_watch_take; v7 candidate, server cost), with --watch ---
    # Every DM var write tells RmWatch which object and which name (a length mask first, then the names): one line in
    # DreamObject.SetVariable, right after RmVer's Written(this) when the change counters are in. RM_WATCH=0 at run time:
    # rm_watch watches nothing and the game keeps polling.
    if os.environ.get('RM_WATCH_BUILD') == '1' and os.environ.get('RM_NATIVE_DIR') and (Path(os.environ['RM_NATIVE_DIR'])/'RmWatch.cs').exists():
        f = work/'src/Objects/DreamObject.cs'; t = f.read_text(encoding='utf-8-sig')
        ver = '        if (!rmSame) global::OpenDreamRuntime.Procs.Native.RmVer.Written(this, name);   // Remastered: change counters (a quiet name, or the same value: none; RmVer.cs)\n'
        plain = '        SetVar(name, value);\n'
        a = ver if ver in t else plain
        if t.count(a) != 1: raise RuntimeError(f'DreamObject.SetVariable changed; review the watch patch ({t.count(a)} found)')
        f.write_text(t.replace(a, a + '        global::OpenDreamRuntime.Procs.Native.RmWatch.Written(this, name);   // Remastered: watched vars\n', 1))
'''

CHAT = r'''
    # --- Remastered: the chat route (RmChat.cs; v11, server cost, 2026-10-25), with --chat ---
    # Text sent to a player goes to the HUD's chat (mapwindow.hud:remasterChatLine) by the game's keep/drop list
    # (Chat.dm RemasterChatKeep), not to the hidden 2D output box. RM_CHAT_ROUTE=0 at run time: the old path.
    if os.environ.get('RM_CHAT_BUILD') == '1':
        f = work/'src/DreamConnection.cs'; t = f.read_text(encoding='utf-8-sig')
        a = '        message = StringFormatDecoder.RemoveFormatting(message);\n\n        OutputControl(message, null);\n'
        if t.count(a) != 1: raise RuntimeError('DreamConnection.OutputDreamValue changed; review the chat patch')
        f.write_text(t.replace(a, '        message = StringFormatDecoder.RemoveFormatting(message);\n\n'
            '        if (global::OpenDreamRuntime.Procs.Native.RmChat.Route(this, message, _objectTree, _dreamManager.WorldInstance)) return;   // Remastered: chat by the HUD\n'
            '        OutputControl(message, null);\n', 1))
'''

COMPACT = r'''
    # --- Remastered: sleeping tiles (map memory, planning/MAP_MEMORY.md; v10 candidate), with --compact ---
    # A tile whose turf only its cell holds (no things on it, no tag, only plain values of its own) can sleep as a packed
    # record in a 128x128 block of its level; any read of it (locate, block, range, view, a step, the route search, a ref,
    # the world's or an area's turfs) wakes it first with the same ref, type, appearance, density, area and values, so DM
    # code can't tell. The edits are in engine/compact/compact_patch.py (exact-match, after the memory patch), the map
    # manager's part in engine/compact/DreamMapManager.RmTiles.cs; DM puts tiles to sleep through RmTiles.cs (native
    # version 10). RM_COMPACT_TILES=0 at run time: nothing sleeps (rm_tiles_sleep only counts).
    if os.environ.get('RM_COMPACT_PATCH'):
        rm_cp = {}
        cp = Path(os.environ['RM_COMPACT_PATCH'])
        exec(cp.read_text(), rm_cp)
        for rel, pairs in rm_cp['FILES'].items():
            f = work/'src'/rel; t = f.read_text(encoding='utf-8-sig')
            for a, b, n in pairs:
                if t.count(a) != n: raise RuntimeError(f'{rel} changed; review the sleeping tiles patch: {a[:70]!r} ({t.count(a)} found, {n} expected)')
                t = t.replace(a, b)
            f.write_text(t)
        for rel, name in rm_cp['NEW'].items():
            shutil.copy2(cp.parent/name, work/'src'/rel)
'''
SAVE = r'''
    # --- Remastered: packaged icons saved by name (engine/save/save_patch.py; map memory, 2026-10-25), with --save-icons ---
    # An atom's icon that is one of the game's own files is saved as its path instead of a copy of the file, and a
    # nameless copy in an older save that is a known earlier version of a packaged icon (game/icon-history.txt) loads as
    # that icon. The edits are exact-match, on the build's copies of the replica's DatumPersistence.cs and OpenDream's
    # DreamResourceManager.cs; replica/ itself is never touched. Saves it writes load on an engine without it unchanged.
    if os.environ.get('RM_SAVE_PATCH'):
        rm_sp = {}
        sp = Path(os.environ['RM_SAVE_PATCH'])
        exec(sp.read_text(), rm_sp)
        for rel, pairs in rm_sp['FILES'].items():
            f = work/'src'/rel; t = f.read_text(encoding='utf-8-sig')
            for a, b, n in pairs:
                if t.count(a) != n: raise RuntimeError(f'{rel} changed; review the save patch: {a[:70]!r} ({t.count(a)} found, {n} expected)')
                t = t.replace(a, b)
            f.write_text(t)
        for rel, name in rm_sp.get('NEW', {}).items():
            shutil.copy2(sp.parent/name, work/'src'/rel)
'''

GRID = r'''
    # --- Remastered: the unit grid (RmGrid.cs; v12 candidate, server cost, planning/ONE_SIGHT_GRID.md B2), with --grid ---
    # The units on the map in 16x16 cells, kept as they move: SetLoc tells the grid at each place a tile's list of things
    # changes (onto a turf, into another movable, off the map; a deletion goes through SetLoc(null)), and each unit keeps
    # its own cell in a field. Off until the game calls rm_grid_on (Native.dm); RM_GRID=0 at run time: never on.
    if os.environ.get('RM_GRID_BUILD') == '1':
        f = work/'src/Objects/Types/DreamObjectMovable.cs'; t = f.read_text(encoding='utf-8-sig')
        g = 'global::OpenDreamRuntime.Procs.Native.RmGrid'
        for a, b in [
            ('    public DreamObjectAtom? Loc;\n',
             '    public DreamObjectAtom? Loc;\n    public int RmGridCell = -1;   // Remastered: the unit grid\'s cell for it (RmGrid.cs): -1 none, -2 inside another movable\n'),
            ('                InsertContent(turf.Cell.Movables);\n',   # (the replica's compatibility patch: mobs after other things)
             '                InsertContent(turf.Cell.Movables);\n                ' + g + '.OnTurf(this, turf);   // Remastered: the unit grid\n'),
            ('            case DreamObjectMovable movable:\n                TransformSystem.SetParent(Entity, movable.Entity);\n',
             '            case DreamObjectMovable movable:\n                TransformSystem.SetParent(Entity, movable.Entity);\n                ' + g + '.Held(this);   // Remastered: the unit grid\n'),
            ('            case null:\n                TransformSystem.SetParent(Entity, MapManager.GetMapOrInvalid(MapId.Nullspace));\n',
             '            case null:\n                TransformSystem.SetParent(Entity, MapManager.GetMapOrInvalid(MapId.Nullspace));\n                ' + g + '.Off(this);   // Remastered: the unit grid\n'),
        ]:
            if t.count(a) != 1: raise RuntimeError('DreamObjectMovable.SetLoc changed; review the grid patch: ' + repr(a[:60]))
            t = t.replace(a, b, 1)
        f.write_text(t)
    # --- Remastered: refs not given out again at once (the death loop; the owner, 10-31: "death keeps replaying", "the body
    # doesnt fall all the time"). A deleted object's slot was the very next new object's, and the page keys units by ref
    # (\ref), so a new Orc took over the dead one's fall and death (an arena: 61 Orcs spawned, 45 refs). A freed slot is
    # given out again only once RmReuseAfter more are free, the oldest first: a ref comes back only after that many others
    # of its kind went (each kind's table up to that many slots bigger) ---
    f = work/'src'/'Objects/DreamRefManager.cs'
    t = f.read_text(encoding='utf-8-sig')
    for a, b in [
        ('        private readonly Queue<int> _emptySlots = new();\n',
         '        private readonly Queue<int> _emptySlots = new();\n'
         '        private const int RmReuseAfter = 65536;   // Remastered: a freed ref waits for this many more (the death loop, 10-31)\n'),
        ('            if (_emptySlots.TryDequeue(out var refId)) {\n',
         '            if (_emptySlots.Count > RmReuseAfter && _emptySlots.TryDequeue(out var refId)) {\n'),
    ]:
        if t.count(a) != 1: raise RuntimeError('DreamRefManager.Bucket changed; review the ref-reuse patch: ' + repr(a[:60]))
        t = t.replace(a, b, 1)
    f.write_text(t)
    # --- Remastered: an overlay or underlay taken off that isn't there is no change (the owner, 10-31: "Yes, build them").
    # The 2006 Births() takes the dodge, miss and block marks off every unit each minute, and the look was set again each
    # time, so every unit counted as changed (RmVer.cs): 44% of the 3D entries made again for nothing at 100 players
    # (reports/u5-hud-1031 section 14). The look is left as it was, as the removal leaves it ---
    f = work/'src'/'Objects/Types/DreamList.cs'
    t = f.read_text(encoding='utf-8-sig')
    a = ('        AtomManager.UpdateAppearance(owner, appearance => {\n'
         '            GetOverlaysList(appearance).Remove(appearanceSystem.AddAppearance(overlayAppearance, registerAppearance:false));\n'
         '            overlayAppearance.Dispose();\n'
         '        });\n')
    b = ('        var rmOverlay = appearanceSystem.AddAppearance(overlayAppearance, registerAppearance:false);\n'
         '        if (System.Array.IndexOf(GetOverlaysArray(AtomManager.MustGetAppearance(owner)), rmOverlay) < 0) {   // Remastered: not there, no change\n'
         '            overlayAppearance.Dispose();\n'
         '            return;\n'
         '        }\n'
         '        AtomManager.UpdateAppearance(owner, appearance => {\n'
         '            GetOverlaysList(appearance).Remove(rmOverlay);\n'
         '            overlayAppearance.Dispose();\n'
         '        });\n')
    if t.count(a) != 1: raise RuntimeError('DreamOverlaysList.RemoveValue changed; review the overlay patch: ' + repr(a[:60]))
    t = t.replace(a, b, 1)
    f.write_text(t)
'''

WEB = r'''
    # --- Remastered: browsers play on the server directly (engine/web/, U4 of planning/SERVER_UPGRADES_PLAN_2026-10-30.md),
    # with --web (on since installed 2026-10-30) ---
    # Every message a connection sends goes through DreamConnection.RmSend: a native player's to its Robust session, a
    # browser's to its web link, which serves the page and its files over HTTP and the game's output() calls over a
    # WebSocket. RM_WEB_PORT unset at run time: nothing listens. The edits are exact-match (engine/web/web_patch.py).
    if os.environ.get('RM_WEB_PATCH'):
        rm_wp = {}
        wp = Path(os.environ['RM_WEB_PATCH'])
        exec(wp.read_text(), rm_wp)
        for rel, pairs in rm_wp['FILES'].items():
            f = work/'src'/rel; t = f.read_text(encoding='utf-8-sig')
            for a, b, n in pairs:
                if t.count(a) != n: raise RuntimeError(f'{rel} changed; review the web patch: {a[:70]!r} ({t.count(a)} found, {n} expected)')
                t = t.replace(a, b)
            f.write_text(t)
        for rel, name in rm_wp['NEW'].items():
            shutil.copy2(wp.parent/name, work/'src'/rel)
        rm_wp['generate'](wp.parent, work/'src')
'''

ICON = r'''
    # --- Remastered: icon.Crop() as BYOND's (engine/icon/icon_patch.py; upstream's was a stub), with --icon-crop (on by
    # default since 2026-10-30): the operations so far are baked in, then every frame is cut to the box. The game called
    # Crop nowhere before; the race portraits use it (HUD.dm). ---
    if os.environ.get('RM_ICON_PATCH'):
        rm_ip = {}
        exec(Path(os.environ['RM_ICON_PATCH']).read_text(), rm_ip)
        for rel, pairs in rm_ip['FILES'].items():
            f = work/'src'/rel; t = f.read_text(encoding='utf-8-sig')
            for a, b, n in pairs:
                if t.count(a) != n: raise RuntimeError(f'{rel} changed; review the icon patch: {a[:70]!r} ({t.count(a)} found, {n} expected)')
                t = t.replace(a, b)
            f.write_text(t)
'''

# The native procs live in two folders since U3 (planning/SERVER_UPGRADES_PLAN_2026-10-30.md, 2026-10-30): engine/core
# holds what any DM game could use, engine/game-botd what knows Banners of the Deep's types, vars and rules
# (tools/engine_boundary_audit.py keeps core clean). The build takes them as one folder, as it took engine/native.
def merged_natives(build_dir):
    stale = sorted((ROOT/'engine/native').glob('*.cs'))
    if stale: raise SystemExit(f'engine/native/ moved to engine/core/ and engine/game-botd/ (U3, 2026-10-30): move {", ".join(f.name for f in stale)} into one of them')
    out = Path(build_dir)/'native-merged'
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True)
    for d in (ROOT/'engine/core', ROOT/'engine/game-botd'):
        for cs in sorted(d.glob('*.cs')):
            if (out/cs.name).exists(): raise SystemExit(f'{cs.name} is in both engine/core and engine/game-botd')
            shutil.copy2(cs, out/cs.name)
    if not any(out.glob('*.cs')): raise SystemExit('no native procs in engine/core or engine/game-botd')
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k, v in DEFAULTS.items(): p.add_argument('--' + k.replace('_', '-'), default=v)
    p.add_argument('--no-native', dest='native', action='store_false', help='leave out the Remastered native procs (engine/core + engine/game-botd, in by default)')
    p.add_argument('--no-memory', dest='memory', action='store_false', help='leave out the memory patch (turf contents lists made when asked for, in by default)')
    p.add_argument('--no-ver', dest='ver', action='store_false', help='leave out the change counters (rm_chunk_ver, rm_ver; in by default when the native procs include RmVer.cs)')
    p.add_argument('--assoc-index', action=argparse.BooleanOptionalAction, default=True, help='build in the lists\' membership index (engine/assoc/dreamlist_index.py, v6; on since v6 was installed, 2026-10-24)')
    p.add_argument('--tick-gc', action=argparse.BooleanOptionalAction, default=True, help='build in the GC between ticks (engine/gc/RemasterTickGC.cs, v6; on since v6 was installed, 2026-10-24)')
    p.add_argument('--map-trim', action=argparse.BooleanOptionalAction, default=True, help='trim the areas\' turf sets once the map has loaded (v7; on since v7f was installed, 2026-10-25)')
    p.add_argument('--watch', action=argparse.BooleanOptionalAction, default=True, help='build in the watched variables (RmWatch.cs, v7; on since v7f was installed, 2026-10-25; the game calls rm_watch only once a write costs ~0)')
    p.add_argument('--compact', action=argparse.BooleanOptionalAction, default=True, help='build in the sleeping tiles (engine/compact/, v10; on since v10 was installed, 2026-10-25; needs RmTiles.cs in the native procs)')
    p.add_argument('--compact-dir', default=str(ROOT/'engine/compact'), help='the sleeping tiles patch (compact_patch.py and DreamMapManager.RmTiles.cs)')
    p.add_argument('--chat', action=argparse.BooleanOptionalAction, default=True, help='build in the chat route (RmChat.cs, v11; on since v11 was installed, 2026-10-25; needs RmChat.cs in the native procs)')
    p.add_argument('--save-icons', action=argparse.BooleanOptionalAction, default=True, help='build in packaged icons saved by name (engine/save/save_patch.py, landed 2026-10-25; reads game/icon-history.txt)')
    p.add_argument('--grid', action=argparse.BooleanOptionalAction, default=True, help='build in the unit grid (RmGrid.cs and the GRID patch, the v12 candidate; off until installed; needs RmGrid.cs in the native procs)')
    p.add_argument('--save-dir', default=str(ROOT/'engine/save'), help='the save patch (save_patch.py)')
    p.add_argument('--web', action=argparse.BooleanOptionalAction, default=True, help='build in browsers on the server (engine/web/, U4; on since installed 2026-10-30, the owner: "Install it"; nothing listens until the server has RM_WEB_PORT)')
    p.add_argument('--web-dir', default=str(ROOT/'engine/web'), help='the web patch (web_patch.py and its files)')
    p.add_argument('--icon-crop', action=argparse.BooleanOptionalAction, default=True, help='build in icon.Crop() as BYOND\'s (engine/icon/icon_patch.py; on by default since 2026-10-30)')
    p.add_argument('--tick-gc-cs', default=str(ROOT/'engine/gc/RemasterTickGC.cs'), help='the GC between ticks to build in (default engine/gc/RemasterTickGC.cs; a scratch copy for test builds)')
    p.add_argument('--native-dir', default='', help='the native procs to build in: one folder holding all of them (a scratch copy for test builds); default engine/core + engine/game-botd, merged')
    p.add_argument('--skip-boundary-audit', action='store_true', help='build the installed engine even when tools/engine_boundary_audit.py fails')
    p.add_argument('--clock-cs', default=str(ROOT/'engine/clock/RemasterClock.cs'), help='the game clock to build in (default engine/clock/RemasterClock.cs; a scratch copy for test builds)')
    p.add_argument('--output', default=str(ROOT/'engine/server/OpenDreamRuntime.dll'), help='where the built DLL goes (a scratch path for test builds)')
    a = p.parse_args()
    if not a.native_dir: a.native_dir = str(merged_natives(a.build_dir))   # also with --no-native: the checks below read it, as they read engine/native
    if Path(a.output).resolve() == (ROOT/'engine/server/OpenDreamRuntime.dll').resolve() and not a.skip_boundary_audit:
        # the build that is installed: engine/core must hold nothing new of the game's (planning/ENGINE_PLAN.md, "Core or game")
        audit = subprocess.run([sys.executable, '-I', str(ROOT/'tools/engine_boundary_audit.py')], capture_output=True, text=True)
        if audit.returncode: raise SystemExit(audit.stdout + '\nengine/core names the game (above): move that code to engine/game-botd, or take the names from the game; --skip-boundary-audit to build anyway')
    if Path(a.source).resolve() == OPENDREAM.resolve():
        head = subprocess.run(['git', '-C', str(OPENDREAM), 'rev-parse', '--short=7', 'HEAD'], capture_output=True, text=True).stdout.strip()
        if head != SOURCE_COMMIT: raise SystemExit(f'standalone/opendream is at {head}, not {SOURCE_COMMIT} (the engine was proven on that); check it out or pass --source')
    stage = Path(a.build_dir)/'stage'
    if stage.exists(): shutil.rmtree(stage)
    (stage/'tools').mkdir(parents=True); (stage/'reports').mkdir()
    shutil.copytree(REPLICA/'engine', stage/'engine')
    script = (REPLICA/'tools/build_compat_runtime.py').read_text()
    hook = "    project = ET.Element('Project', Sdk='Microsoft.NET.Sdk')\n    props = ET.SubElement(project, 'PropertyGroup')"
    if script.count(hook) != 1: raise SystemExit('build script changed; review tools/build_runtime.py')
    script = script.replace(hook, CLOCK + NATIVE + MEMORY + VER + WATCH + MAPTRIM + TICKGC + ASSOC + COMPACT + CHAT + SAVE + GRID + WEB + ICON + hook, 1)
    (stage/'tools/build_compat_runtime.py').write_text(script)
    out = Path(a.output).resolve(); out.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, RM_CLOCK_CS=str(Path(a.clock_cs)))
    env.pop('RM_NATIVE_DIR', None)
    if a.native: env['RM_NATIVE_DIR'] = str(Path(a.native_dir))
    env['RM_MEMORY'] = '1' if a.memory else '0'
    env['RM_VER'] = '1' if a.ver else '0'
    env.pop('RM_TICK_GC_CS', None)
    if a.tick_gc: env['RM_TICK_GC_CS'] = str(Path(a.tick_gc_cs))
    env['RM_WATCH_BUILD'] = '1' if a.watch else '0'
    if a.chat and a.native and not (Path(a.native_dir)/'RmChat.cs').exists(): raise SystemExit('--chat needs RmChat.cs in the native procs (or --no-chat)')
    env['RM_CHAT_BUILD'] = '1' if (a.chat and a.native) else '0'
    if a.grid and (not a.native or not (Path(a.native_dir)/'RmGrid.cs').exists()): raise SystemExit('--grid needs RmGrid.cs in the native procs')
    env['RM_GRID_BUILD'] = '1' if (a.grid and a.native) else '0'
    env['RM_MAP_TRIM'] = '1' if a.map_trim else '0'
    env.pop('RM_COMPACT_PATCH', None)
    if a.compact:
        if not a.memory or not (Path(a.native_dir)/'RmTiles.cs').exists(): raise SystemExit('--compact needs the memory patch and RmTiles.cs in the native procs')
        env['RM_COMPACT_PATCH'] = str(Path(a.compact_dir)/'compact_patch.py')
    env.pop('RM_SAVE_PATCH', None)
    if a.save_icons: env['RM_SAVE_PATCH'] = str(Path(a.save_dir)/'save_patch.py')
    env.pop('RM_ASSOC_PATCH', None)
    if a.assoc_index: env['RM_ASSOC_PATCH'] = str(ROOT/'engine/assoc/dreamlist_index.py')
    env.pop('RM_WEB_PATCH', None)
    if a.web: env['RM_WEB_PATCH'] = str(Path(a.web_dir)/'web_patch.py')
    env.pop('RM_ICON_PATCH', None)
    if a.icon_crop: env['RM_ICON_PATCH'] = str(ROOT/'engine/icon/icon_patch.py')
    r = subprocess.run([sys.executable, str(stage/'tools/build_compat_runtime.py'), '--source', a.source, '--robust-source', a.robust_source,
                        '--server', a.server, '--sdk', a.sdk, '--annotations', a.annotations, '--build-dir', str(Path(a.build_dir)/'work'),
                        '--output', str(out)], env=env, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-3000:]); log = stage/'reports/engine-build.log'
        if log.exists(): print(log.read_text()[-4000:])
        raise SystemExit('runtime build failed')
    print('Built', out)

if __name__ == '__main__':
    main()
