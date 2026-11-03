#!/usr/bin/env python3
"""Apply measured movement fixes to the replacement engine's DM standard library."""
import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    standard = ROOT/'runtime/macos-x64/compiler/DMStandard/Types/Atoms'
    patches = []
    for name in ('Movable.dm', 'Turf.dm'):
        path = standard/name
        backup = path.with_suffix('.dm.upstream')
        if not backup.exists(): backup.write_bytes(path.read_bytes())
        original = backup.read_text(encoding='utf-8-sig')
        text = original
        if name == 'Movable.dm':
            text = text.replace('if (isnull(NewLoc) || loc == NewLoc)', 'if (!NewLoc || loc == NewLoc)')
            text = text.replace('/atom/movable\n', '/atom/movable\n\tvar/tmp/atom/__od_collision_target\n', 1)
            text = text.replace('\t\tvar/loc_entered = NewLoc.Enter(src, loc)',
                '\t\t__od_collision_target = NewLoc\n\t\tvar/loc_entered = NewLoc.Enter(src, loc)')
            old = '\t\t\t\tfor (var/atom/content in NewLoc.contents)\n\t\t\t\t\tsrc.Bump(content)'
            if old not in text: raise RuntimeError('Movement implementation changed')
            # An Enter() override that refuses without ..() leaves the turf as the
            # target; BYOND then bumps a non-dense turf's first dense content
            # (reference/fixtures/bump_target.dm). The game's turf/grounds does this.
            text = text.replace(old, '\t\t\t\tvar/atom/blocked_by = __od_collision_target\n'
                '\t\t\t\t__od_collision_target = null\n'
                '\t\t\t\tif (blocked_by == NewLoc && isturf(NewLoc) && !NewLoc.density)\n'
                '\t\t\t\t\tfor (var/atom/movable/content in NewLoc)\n'
                '\t\t\t\t\t\tif (content.density)\n'
                '\t\t\t\t\t\t\tblocked_by = content\n'
                '\t\t\t\t\t\t\tbreak\n'
                '\t\t\t\tsrc.Bump(blocked_by)')
            text = text.replace('\t\t\tvar/atom/oldloc = loc',
                '\t\t\t__od_collision_target = null\n\t\t\tvar/atom/oldloc = loc')
            text = text.replace('\t\t\treturn TRUE',
                '\t\t\treturn (isturf(oldloc) && isturf(NewLoc) && get_dist(oldloc,NewLoc)==1) ? world.icon_size : TRUE')
        else:
            text = text.replace('\t\tif (!src.Cross(O))',
                '\t\tO.__od_collision_target = src\n\t\tif (!src.Cross(O))')
            text = text.replace('\t\t\tif (!content.Cross(O))',
                '\t\t\tO.__od_collision_target = content\n\t\t\tif (!content.Cross(O))')
            text = text.replace('\t\treturn TRUE', '\t\tO.__od_collision_target = src\n\t\treturn TRUE', 1)
        path.write_text(text)
        patches.extend(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
                       fromfile=f'DMStandard/Types/Atoms/{name}', tofile=f'DMStandard/Types/Atoms/{name}'))
    (ROOT/'engine/movement-callbacks.patch').write_text(''.join(patches))
    root_standard = standard.parents[1]/'_Standard.dm'
    backup = root_standard.with_suffix('.dm.upstream')
    if not backup.exists(): backup.write_bytes(root_standard.read_bytes())
    original = backup.read_text(encoding='utf-8-sig')
    start = original.index('proc/get_step_rand(')
    end = original.index('proc/step_towards(', start)
    section = original[start:end]
    section = section.replace('return get_step(Ref, dir)', """var/turf/target = get_step(Ref, dir)
	if (!target) return 0
	if (Ref.density)
		if (target.density) return 0
		for (var/atom/A in target) if (A.density) return 0
	return target""")
    text = original[:start] + section + original[end:]
    random_step_text = text
    # BYOND 516.1655 measures tile (Chebyshev) distance, ignoring z.
    # Equal references are -1; invalid/unlocated distinct endpoints are +inf.
    old_distance = """proc/get_dist(atom/Loc1, atom/Loc2) as num
	if (!istype(Loc1) || !istype(Loc2)) return 127
	if (Loc1 == Loc2) return -1

	var/distX = Loc2.x - Loc1.x
	var/distY = Loc2.y - Loc1.y
	return round(sqrt(distX ** 2 + distY ** 2))"""
    new_distance = """proc/get_dist(atom/Loc1, atom/Loc2) as num
	if (Loc1 == Loc2) return -1
	if (!istype(Loc1) || !istype(Loc2) || isarea(Loc1) || isarea(Loc2)) return 1.#INF
	if (!Loc1.x || !Loc1.y || !Loc2.x || !Loc2.y) return 1.#INF
	return max(abs(Loc2.x - Loc1.x), abs(Loc2.y - Loc1.y))"""
    if text.count(old_distance) != 1:
        raise RuntimeError('Upstream get_dist implementation changed; review distance compatibility')
    text = text.replace(old_distance, new_distance)
    root_standard.write_text(text)
    (ROOT/'engine/random-step-obstacles.patch').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), random_step_text.splitlines(True), fromfile='_Standard.dm', tofile='_Standard.dm')))
    (ROOT/'engine/distance-standard.patch').write_text(''.join(difflib.unified_diff(
        random_step_text.splitlines(True), text.splitlines(True),
        fromfile='DMStandard/_Standard.dm', tofile='DMStandard/_Standard.dm')))
    world = ROOT/'runtime/macos-x64/compiler/DMStandard/Types/World.dm'
    backup = world.with_suffix('.dm.upstream')
    if not backup.exists(): backup.write_bytes(world.read_bytes())
    original = backup.read_text(encoding='utf-8-sig')
    text = original
    for proc in ('Repop', 'Reboot'):
        old = f'\tproc/{proc}()\n\t\tset opendream_unimplemented = TRUE'
        if old not in text: raise RuntimeError(f'World {proc} definition changed')
        text = text.replace(old, f'\tproc/{proc}()')
    world.write_text(text)
    (ROOT/'engine/world-lifecycle-standard.patch').write_text(''.join(difflib.unified_diff(
        original.splitlines(True), text.splitlines(True), fromfile='World.dm', tofile='World.dm')))



if __name__ == '__main__': main()
