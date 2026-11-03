#!/usr/bin/env python3
"""Read-only original-art audit of missing icon-state constructors and corpses.

Runs the same copied real-game MakeBody code in private BYOND/OpenDream worlds.
No clients, input, normal saves, installs, production edits, or invented artwork.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

from PIL import Image
from audit_dmi_edge_cases import run_byond, run_replacement, metadata
from check_generated_icons import pixel_hash

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT.parent / 'remastered/game'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


FIXTURE = '''var/parity_race
world
    maxx = 10
    maxy = 10
    maxz = 1
    turf = /turf/grounds/grass
proc/AuditIconRun()
    var/Player/P = new(locate(2,2,1))
    usr = P
    var/list/equipment = list()
    for(var/kind in typesof(/obj/Items/Equipment))
        var/obj/Items/Equipment/E = new kind()
        if(E.icon)
            var/list/states = icon_states(E.icon)
            equipment += list(list("type"="[kind]", "source"="[E.icon]", "state"=E.icon_state, "exact_state_present"=(E.icon_state in states)))
        del(E)
    text2file(json_encode(equipment), "outputs/equipment.json")
    var/list/cases = list(
        list("human-male", /mob/Monsters/Human, 1, 'Human.dmi'),
        list("human-female", /mob/Monsters/Human, 0, 'Human.dmi'),
        list("human-black-female", /mob/Monsters/Human, 0, 'HumanBlack.dmi'),
        list("elf-female", /mob/Monsters/Elf, 0, 'Human.dmi'),
        list("dwarf-male", /mob/Monsters/Dwarf, 1, 'Human.dmi'),
        list("orc-male", /mob/Monsters/Orc, 1, 'Orc.dmi'),
        list("orc-female", /mob/Monsters/Orc, 0, 'Orc.dmi'))
    var/list/observations = list()
    for(var/list/C in cases)
        var/name = C[1]
        var/kind = C[2]
        var/mob/Monsters/M = new kind(locate(5,5,1), C[3])
        // Select genuine possible constructor branches deterministically so
        // independent engines receive identical inputs despite their RNGs.
        M.icon = C[4]
        M.Black = (name == "human-black-female")
        if(M.Race == "Human" && M.Gender == "Female") M.Hair = "HumanBrown"
        if(M.Race == "Dwarf") M.Beard = "Brown"
        M.CantKill = 1
        M.CanBeSlaved = 0
        M.OnFire = 0
        M.Werepowers = 0
        fcopy(M.icon, "outputs/[name]-source.dmi")
        var/icon/selected = icon(M.icon,M.icon_state)
        fcopy(selected, "outputs/[name]-selected.dmi")
        M.MakeBody(locate(5,5,1))
        for(var/mob/Body/B in world)
            fcopy(B.icon, "outputs/[name]-body.dmi")
            observations += list(list("case"=name, "type"="[M.type]", "state"=M.icon_state, "gender"=M.Gender, "black"=M.Black, "hair"=M.Hair, "beard"=M.Beard, "body_state"=B.icon_state, "body_dir"=B.dir))
            del(B)
        del(M)
    text2file(json_encode(observations), "outputs/observations.json")
    var/icon/H = icon('Female.dmi',"Hair")
    fcopy(H,"outputs/female-missing-hair.dmi")
    var/icon/HB = icon('Female.dmi',"BlackHair")
    fcopy(HB,"outputs/female-missing-blackhair.dmi")
    var/icon/P0 = icon('Human.dmi',"Normal",SOUTH,1,0)
    fcopy(P0,"outputs/human-missing-filtered-idle.dmi")
    var/icon/P1 = icon('Human.dmi',"Normal",SOUTH,1,1)
    fcopy(P1,"outputs/human-missing-filtered-walk.dmi")
    world.log << "DMI_AUDIT|complete"
    shutdown()
'''


def comparable(path):
    states = metadata(path)
    with Image.open(path) as image:
        return dict(size=list(image.size), states=states,
                    visible_sheet_hash=pixel_hash(image))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server', type=Path, default=Path('/tmp/dm-runtime-audit/dmi-rewind-server'))
    parser.add_argument('--port', type=int, default=12191)
    parser.add_argument('--label', default='initial')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.label): parser.error('Invalid label')
    out = ROOT / 'reference/icon-fallback-audit' / args.label
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((ROOT.parent/'remastered/assets/sprites/manifest.json').read_text())
    tracked = {str(p.relative_to(GAME)): sha(p) for p in GAME.rglob('*.dm')}
    art = {a['source']: sha(GAME/a['source']) for a in manifest['assets']}
    runtime = args.server/'Resources/Assemblies/OpenDreamRuntime.dll'
    runtime_hash = sha(runtime)
    for engine in ('byond', 'replacement'):
        target = out/engine
        target.mkdir()
        with tempfile.TemporaryDirectory(prefix='dm-icon-fallback-') as temp:
            arena = Path(temp)/'world'
            shutil.copytree(GAME, arena, ignore=shutil.ignore_patterns('Cave Crawlers.json', '*.sav', '*.dmm', 'units', 'saves', 'ErrorLog.txt'))
            (arena/'outputs').mkdir()
            source = arena/'Code/World.dm'
            text = source.read_text(encoding='latin-1')
            start, end = text.index('\tNew()'), text.index('\nvar/Season')
            source.write_text(text[:start]+'\tNew()\n\t\tspawn(0) AuditIconRun()\n'+text[end:], encoding='latin-1')
            # The replacement compiler permits this duplicate legacy verb;
            # BYOND rejects it. It is never called in this no-input fixture.
            # Rename the older definition identically in both private worlds;
            # all icon/constructor/MakeBody code stays byte-for-byte original.
            verbs = arena/'Code/Verbs.dm'
            verbs.write_text(verbs.read_text(encoding='latin-1').replace('mob/verb/StopAll()', 'mob/verb/AuditUnusedLegacyStopAll()'), encoding='latin-1')
            dme = re.sub(r'^#include .*\.dmm"\s*$', '', (arena/'Cave Crawlers.dme').read_text(encoding='latin-1'), flags=re.M)
            (arena/'icon_fallback.dm').write_text(FIXTURE)
            (arena/'audit.dme').write_text(dme+'\n#include "icon_fallback.dm"\n', encoding='latin-1')
            # Keep a reproducible fixture and exact source hashes, without
            # retaining redundant copies of the whole game/artwork tree.
            shutil.copy2(arena/'icon_fallback.dm', target/'icon_fallback.dm')
            shutil.copy2(arena/'audit.dme', target/'audit.dme')
            shutil.copy2(source, target/'World.dm')
            shutil.copy2(verbs, target/'Verbs.dm')
            try:
                if engine == 'byond': run_byond(arena)
                else: run_replacement(arena, args.server, args.port)
            finally:
                for name in ('compile.log', 'server.log', 'ErrorLog.txt'):
                    if (arena/name).exists(): shutil.copy2(arena/name, target/name)
                shutil.copytree(arena/'outputs', target/'outputs')
    report = dict(scope=__doc__, fixture_sha256=sha(out/'byond/icon_fallback.dm'), runtime_sha256=runtime_hash,
                  source_sha256=tracked, art_sha256=art, cases=[])
    for path in sorted((out/'byond/outputs').glob('*.dmi')):
        other=out/'replacement/outputs'/path.name
        ref, actual = comparable(path), comparable(other)
        report['cases'].append(dict(name=path.name, reference=ref, replacement=actual,
                                   all_state_cells_match=ref['states']==actual['states']))
    report['observations']={engine:json.loads((out/engine/'outputs/observations.json').read_text()) for engine in ('byond','replacement')}
    report['equipment']={engine:json.loads((out/engine/'outputs/equipment.json').read_text()) for engine in ('byond','replacement')}
    report['errors']={}
    for engine in ('byond','replacement'):
        logs='\n'.join((out/engine/name).read_text(errors='replace') for name in ('server.log','ErrorLog.txt') if (out/engine/name).exists())
        report['errors'][engine]=re.findall(r'(?im)^.*(?:\[(?:ERRO|FATL)\]|\bruntime error\b|\bexception\b).*$',logs)
    report['source_unchanged']=tracked=={str(p.relative_to(GAME)):sha(p) for p in GAME.rglob('*.dm')}
    report['art_unchanged']=art=={key:sha(GAME/key) for key in art}
    report['runtime_unchanged']=runtime_hash==sha(runtime)
    report['audit_completed']=all(report[k]for k in ('source_unchanged','art_unchanged','runtime_unchanged')) and not any(report['errors'].values())
    dest=ROOT/'reports'/('icon-fallback-'+args.label+'.json')
    dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(dest),audit_completed=report['audit_completed'], errors=report['errors'],
        equipment_missing={k:[e for e in rows if not e['exact_state_present']]for k,rows in report['equipment'].items()},
        cases=[dict(name=c['name'],matches=c['all_state_cells_match'], reference_states=len(c['reference']['states']),replacement_states=len(c['replacement']['states'])) for c in report['cases']]),indent=2))
    return 0 if report['audit_completed'] else 1


if __name__ == '__main__': raise SystemExit(main())
