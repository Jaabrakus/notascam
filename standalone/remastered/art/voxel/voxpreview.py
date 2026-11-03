# No-window preview of the voxel gear (python3 voxpreview.py OUTDIR MODELDIR [tag]): the game's real 3D page in
# headless Chrome (tools/worldlook_replay.py's replay script), in a private folder, given a lineup of units of
# several races holding each kind of gear in different tiers, with MODELDIR's models (the game's own, or the
# voxel copies). Writes stills from the game's corner cameras. Nothing in game/ is touched.
import json, os, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import worldlook_replay as wr
import voxgear

SRC = ROOT/'tests/worldlook-replay'          # the dumped scenes and their pictures (read only)

LINEUP = [  # model, gear
    ('human', {'w': 'sword:iron', 's': 'iron', 'h': 'iron'}),
    ('orc', {'w': 'axe:iron', 'h': 'iron'}),
    ('dwarf', {'w': 'pickaxe:iron', 'h': 'gold'}),
    ('goblin', {'w': 'dagger:hell', 's': 'wood'}),
    ('elf', {'bow': 'wood', 'h': 'silver'}),
    ('lizardman', {'w': 'spear:silver', 's': 'silver'}),
    ('skeleton', {'w': 'mace:adamantium', 'h': 'hell'}),
    ('vampire', {'w': 'sword:gold', 's': 'gold', 'h': 'diamond'}),
]

def stage(out, models, page_patch):
    out.mkdir(parents=True, exist_ok=True)
    for f in SRC.glob('r3*.png'):
        dst = out/f.name
        if not dst.exists(): shutil.copy2(f, dst)
    for f in (ROOT/'game/Interface/textures').glob('*.png'): shutil.copy2(f, out/f'r3t-{f.stem}.png')
    for f in Path(models).glob('*.json'): shutil.copy2(f, out/f'model-{f.stem}.json')
    d = json.load(open(SRC/'worldlook-3d-1.json'))
    base = next(t for t in d['things'] if t.get('model'))
    things = [t for t in d['things'] if not t.get('model')]
    for i, (m, g) in enumerate(LINEUP):
        t = json.loads(json.dumps(base)); t.update(model=m, gear=g, x=37 + i, y=31, dir=2, act='idle', ref=f'vox{i}', name=m)
        things.append(t)
    d['things'] = things; d['cx'], d['cy'] = 40, 31
    json.dump(d, open(out/'worldlook-3d-vox.json', 'w'))
    html = (ROOT/'game/Interface/remastered.html').read_text()
    html = html.replace("function send(action,value){window.location.href=", "function send(action,value){return;window.location.href=", 1)
    if page_patch:
        assert html.count(voxgear.PAGE_OLD) == 1
        html = html.replace(voxgear.PAGE_OLD, voxgear.PAGE_NEW, 1)
    i = html.index('<head>') + len('<head>')
    # the models look (Settings > Look > models): units drawn as 3D models wearing their gear pieces
    rep = wr.REPLAY.replace('v3set(true);', 'v3set(true);V3.models=true;V3.unitModels=true;', 1)
    assert rep != wr.REPLAY
    (out/'replay.html').write_text(html[:i] + '<script>window.__errs=[];addEventListener("error",e=>__errs.push(e.message+" @"+e.lineno));' + rep + '</script>' + html[i:])

CAMS = {
    'corner45': 'scene=vox&cx=40.5&cy=31&dist=5.2&pitch=0.62&yaw=0.785&dayp=0.4',
    'corner315': 'scene=vox&cx=40.5&cy=31&dist=5.2&pitch=0.62&yaw=-0.785&dayp=0.4',
    'front': 'scene=vox&cx=40.5&cy=31&dist=5.2&pitch=0.45&yaw=0&dayp=0.4',
    'game': 'scene=vox&cx=40.5&cy=31&dist=11&pitch=0.62&yaw=0.785&dayp=0.4',
}

def shoot(out, tag, w=1400, h=800):
    from playwright.sync_api import sync_playwright
    wr.OUT = out
    files = {}
    with wr.Server() as s, sync_playwright() as pw:
        b, p, errs = wr.browser(pw, w, h)
        for name, q in CAMS.items():
            wr.load(p, s.base + q, settle=4000)
            f = out/f'{name}-{tag}.png'
            p.screenshot(path=str(f))
            files[name] = str(f)
        files['errors'] = errs + p.evaluate('window.__errs||[]')
        b.close()
    print(json.dumps(files, indent=1))
    return files

if __name__ == '__main__':
    out, models = Path(sys.argv[1]), sys.argv[2]
    tag = sys.argv[3] if len(sys.argv) > 3 else 'shot'
    stage(out, models, page_patch=(tag != 'before'))
    shoot(out, tag)
