#!/usr/bin/env python3
"""Build a reviewable character rig without modifying the approved Elf.

Existing profile: --profile character.json --assets assets/ --output new-folder
Zoned sheet: --inputs inputs/ --race Human --name 'Human male' --output new-folder
Batch: --batch jobs.json (list of objects with the same option names).
Requires Python 3; zoned-sheet cutting additionally requires Pillow and numpy.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_MASTER = HERE.parents[2] / 'Dungeon Master Sample/GOA Reusable Animation Rig v1'
PARTS = ['head', 'torso', 'pelvis'] + [s + p for s in ['right', 'left']
         for p in ['UpperArm', 'Forearm', 'Hand', 'Thigh', 'Shin', 'Foot']]
BOW = [dict(bow=[38,32],nock=[32,32],cheek=[28,29],flung=[26,28]),
       dict(bow=[26,31],nock=[31,31],cheek=[36,30],flung=[38,29]),
       dict(bow=[54,28],nock=[45,28],cheek=[36,27],flung=[32,26]),
       dict(bow=[9,28],nock=[18,28],cheek=[27,27],flung=[29,28])]

def read(path):
    return json.loads(Path(path).read_text())

def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2))

def length(chain):
    return sum(math.dist(a, b) for a, b in zip(chain, chain[1:]))

def point(p):
    if not isinstance(p, list) or len(p) != 2 or not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and 0 <= v < 64 for v in p):
        raise ValueError('Joint coordinates must be finite [x,y] values within the native 64px canvas: '+str(p))

def audit(profile, assets):
    warnings, refs = [], set()
    if len(profile['views']) != 4 or len(profile['grips']) != 4:
        raise ValueError('Exactly four S/N/E/W views and grip records are required')
    for d, v in enumerate(profile['views']):
        if v['name'] != ['South','North','East','West'][d]:
            raise ValueError('View order must be South, North, East, West')
        for k in ['neck', 'waist']: point(v[k])
        if v['waist'][1] <= v['neck'][1]: raise ValueError('Waist must be below neck')
        for group in ['arms', 'legs']:
            for side in ['right','left']:
                chain = v[group][side]
                if len(chain) != 3: raise ValueError('Each limb requires three joints')
                for p in chain: point(p)
                if any(math.dist(a,b)<1 for a,b in zip(chain,chain[1:])):
                    raise ValueError('Degenerate limb: '+v['name']+' '+side+' '+group)
            ratio = min(length(c) for c in v[group].values()) / max(length(c) for c in v[group].values())
            if d < 2 and ratio < .75:
                warnings.append(f"{v['name']} {group}: left/right reach ratio {ratio:.2f}; inspect joint placement and projection before approval.")
        for side in ['right','left']: point(profile['grips'][d][side])
        if set(v['parts']) != set(PARTS): raise ValueError('Expected all 15 named body parts')
        refs.update(v['parts'].values())
        if len(v['walk']) != 3: raise ValueError('Need idle/walk A/walk B images')
        for row in v['walk']:
            refs.update([row['refined-torso'],row['render-head']])
    for ref in refs:
        p = (assets / ref).resolve()
        if not p.is_relative_to(assets.resolve()): raise ValueError('Asset path escapes asset folder')
        if not p.is_file(): raise ValueError('Missing asset: '+ref)
        raw = p.read_bytes()
        if raw[:8] != b'\x89PNG\r\n\x1a\n' or tuple(int.from_bytes(raw[i:i+4],'big') for i in [16,20]) != (64,64):
            raise ValueError('Body images must be native 64x64 PNG: '+ref)
    return warnings, refs

def fit(profile, reference):
    """Map Elf landmarks relative to neck/torso/shoulder span; retain editable targets."""
    result = copy.deepcopy(profile)
    targets = []
    for d in range(4):
        # West bow uses South anatomy; East is its complete mirrored render.
        bd = 0 if d >= 2 else d
        a, b = reference['views'][bd], profile['views'][bd]
        span = lambda v: abs(v['arms']['right'][0][0]-v['arms']['left'][0][0])
        sx = span(b) / max(1, span(a))
        sy = (b['waist'][1]-b['neck'][1]) / (a['waist'][1]-a['neck'][1])
        targets.append({k: [round(b['neck'][0]+(p[0]-a['neck'][0])*sx,3),
                            round(b['neck'][1]+(p[1]-a['neck'][1])*sy,3)] for k,p in BOW[d].items()})
    result.setdefault('poseTargets', {})['bow'] = result.get('poseTargets',{}).get('bow', targets)
    # Apply the reference guard as a proportion of that character's calibrated reach.
    if not result.get('keepGrips', False):
        for d in range(4):
            for side in ['right','left']:
                old, new = reference['views'][d]['arms'][side], profile['views'][d]['arms'][side]
                scale = length(new)/length(old)
                offset = [reference['grips'][d][side][i]-old[0][i] for i in range(2)]
                reach = length(new)*.95
                n = math.hypot(*offset)*scale
                scale *= min(1, reach/max(n,.001))
                result['grips'][d][side] = [round(new[0][i]+offset[i]*scale,3) for i in range(2)]
    return result

def build(job):
    master = Path(job.get('master') or DEFAULT_MASTER).resolve()
    out = Path(job['output']).resolve()
    if out.exists(): raise ValueError('Refusing to overwrite existing folder: '+str(out))
    if not (master/'source/engine.js').is_file(): raise ValueError('Missing master rig package')
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.retarget-', dir=out.parent) as temp:
        stage = Path(temp)
        warnings = []
        if job.get('inputs'):
            inputs = Path(job['inputs']).resolve()
            race = job.get('race')
            if not race or not re.fullmatch(r'[A-Za-z0-9_-]+',race): raise ValueError('Provide a simple race ID')
            for f in ['sprites.png','fine.png','fine.json',race+'.json']:
                if not (inputs/f).is_file(): raise ValueError('Missing input: '+f)
            shutil.copytree(inputs, stage/'inputs')
            (stage/'preview/assets').mkdir(parents=True)
            (stage/'profiles').mkdir()
            spec = importlib.util.spec_from_file_location('zone_cutter',HERE/'zone_cutter.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            module.RIG = str(stage)
            module.cut(race, 'character', job.get('name') or race)
            profile = read(stage/'profiles/character.json')
            assets = stage/'preview/assets'
            warnings += ['Zone cutter creates provisional flat fillers and synthetic far arms; hidden anatomy needs art review.']
            zone_names = read(inputs/'fine.json')['zones']
            from PIL import Image
            occupied = set(Image.open(inputs/'fine.png').getdata())
            extras = [n for i,n in enumerate(zone_names) if i in occupied and n in ['wings','tail']]
            if extras: warnings.append('Extra anatomy needs separate rig layers: '+', '.join(extras)+'. Do not approve this humanoid-only output until those layers are added.')
        else:
            if not job.get('profile') or not job.get('assets'): raise ValueError('Provide --profile and --assets, or --inputs and --race')
            profile, assets = read(job['profile']), Path(job['assets']).resolve()
        if job.get('name'): profile['name'] = job['name']
        # Optional full calibrated profile fields override guesses, never executable instructions.
        if job.get('overrides'): profile.update(read(job['overrides']))
        found, refs = audit(profile, assets); warnings += found
        reference = read(master/'profiles/elf-male.json')
        profile = fit(profile, reference)
        package = stage/'result'
        (package/'profiles').mkdir(parents=True)
        shutil.copytree(master/'source', package/'source')
        shutil.copytree(master/'preview/assets', package/'preview/assets')
        # Namespace character files so their names cannot replace shared gear artwork.
        mapping = {}
        for i, ref in enumerate(sorted(refs)):
            name = f'character-{i:03}.png'
            shutil.copyfile(assets/ref,package/'preview/assets'/name); mapping[ref] = name
        for v in profile['views']:
            v['parts'] = {k:mapping[r] for k,r in v['parts'].items()}
            v['walk'] = [{k:mapping[r] for k,r in row.items()} for row in v['walk']]
        write(package/'profiles/character.json', profile)
        engine = (package/'source/engine.js').read_text()
        if engine.count('const targets=[') != 1: raise ValueError('Master engine changed; inspect pose-target adapter')
        engine = engine.replace('const targets=[','const targets=this.data.poseTargets?.bow?.[p.d]||[')
        old_rigid = "const rigid=(name,srcRoot,srcTip,toRoot,toTip)=>result.parts[name]={srcRoot,srcTip,root:toRoot,tip:toTip};"
        new_rigid = "const rigid=(name,srcRoot,srcTip,toRoot,toTip)=>{const ps=view.partSource?.[name];result.parts[name]={srcRoot:ps?ps[0]:srcRoot,srcTip:ps?ps[1]:srcTip,root:toRoot,tip:toTip,foreshortened:ps?.[2]==='fit'};};"
        if old_rigid not in engine: raise ValueError('Master rigid adapter changed; inspect partSource handling')
        engine = engine.replace(old_rigid,new_rigid)
        engine = engine.replace("const leadSide=d<2?'right':Object.entries(view.legs).sort((a,b)=>(b[1][0][0]-a[1][0][0])*side)[0][0];", "const leadSide=view.leadLeg||(d<2?'right':Object.entries(view.legs).sort((a,b)=>(b[1][0][0]-a[1][0][0])*side)[0][0]);")
        (package/'source/engine.js').write_text(engine)
        rebuild = (master/'rebuild.py').read_text().replace("profiles/elf-male.json", "profiles/character.json")
        rebuild = rebuild.replace("data.update(views=p['views'],grips=p['grips'])", "data.update(views=p['views'],grips=p['grips'],poseTargets=p['poseTargets'])")
        (package/'rebuild.py').write_text(rebuild)
        # No Elf exports/reports are copied and mislabeled as this character's validation.
        template = package/'source/viewer.html'
        html = template.read_text().replace('<a id="baked" href="exports/slash.png">Baked sheet</a>', '<a id="baked" hidden>Not baked</a>')
        template.write_text(html)
        app = package/'source/app.js'
        app.write_text(app.read_text().replace("'Elf-'+", "(DATA.character||'Character')+'-'+").replace('Elf male · ranged polish','Character retarget · needs visual review'))
        write(package/'fit-report.json', {'status':'needs_visual_review','character':profile['name'],
            'warnings':warnings,'automated':['input validation','guard reach adaptation','neck-relative bow target fitting','asset packaging'],
            'not_automatic':['hidden-anatomy redraw','extra appendage rigging','throw-specific pixel cleanup','visual approval'],
            'baseline':str(master),'bakedExports':False})
        (package/'README.md').write_text(f'''# {profile['name']} — retarget review candidate

Generated from the approved Elf renderer. This is not a claim of perfect art or completed validation.
Read `fit-report.json` first. Open `preview/index.html` to review.

Rebuild: `python3 rebuild.py`. Optional server: `python3 -m http.server 8881 --bind 127.0.0.1`, then open `/preview/`.

Edit `profiles/character.json` joints/grips and `poseTargets.bow` to refine the fit. Bow targets are mapped relative to this body's neck and shoulder span; East mirrors West. Set `keepGrips: true` when reusing an explicitly calibrated profile through the retarget tool.

Review idle, walk, slash, thrust, bow and throw in all four directions. Bow: 0.32, 0.72, 0.90, 1.15, 1.40, 1.75 seconds. Throw: 0.26, 0.38, 0.52, 0.75 seconds. Check seams, hand contact, reach, foot contact and recovery at native scale. Fixed Elf throw offsets and other special cases still require character-specific review.

No Elf baked sheets or pass reports are included. Use viewer export buttons after visual review. Other races and hybrids use the same input schema; wings/tails and non-humanoid anatomy require additional layers. Never hide those limitations behind a passing build.

Warnings:\n'''+''.join('- '+w+'\n' for w in warnings))
        subprocess.run([sys.executable,str(package/'rebuild.py')],check=True)
        shutil.copyfile(package/'README.md',package/'preview/README.md')
        write(package/'manifest.json', {str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in sorted(package.rglob('*')) if p.is_file()})
        package.rename(out)
        return {'output':str(out),'warnings':warnings,'status':'needs_visual_review'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ['profile','assets','inputs','race','name','output','master','overrides','batch']:
        parser.add_argument('--'+arg)
    args = vars(parser.parse_args())
    if args['batch']:
        jobs = read(args['batch'])
        if not isinstance(jobs,list): parser.error('Batch must be a JSON list of job objects')
    else:
        if not args['output']: parser.error('--output is required')
        jobs = [args]
    results = []
    for job in jobs:
        try: results.append(build(job))
        except (ValueError,KeyError,OSError,subprocess.CalledProcessError) as exc:
            results.append({'status':'failed','output':job.get('output'),'error':str(exc)})
    print(json.dumps(results,indent=2))
    return int(any(r['status']=='failed' for r in results))

if __name__ == '__main__': sys.exit(main())
