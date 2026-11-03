# No-window preview of 3D gear on the sprite units (python3 preview.py OUTDIR [2d|3d] [tag]): the game's real 3D
# page (tools/worldlook_replay.py's replay script) in headless Chrome, in a private folder, given a lineup of
# races in drawn body armour. '3d': their pictures without the held and worn pieces, which gear3d.js adds as 3D
# models; '2d': today's pictures with the drawn weapon, shield and helmet layers, to compare. Writes stills from
# the game's corner cameras and a turn round the lineup. Nothing in game/ is touched.
import json, os, shutil, sys
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'tools'))
sys.path.insert(0, str(ROOT/'art/enhance'))
import worldlook_replay as wr       # noqa: E402
from game_export import read_dmi_full   # noqa: E402

SRC = ROOT/'tests/worldlook-replay'
ICONS = ROOT/'game/Icons/Remastered'

# sheet, body state, drawn body armour (tier: chest, legs, arms), 3D gear, act
LINEUP = [
    ('Human', '', ('iron', 'mail', 'mail', 'plate'), dict(w='longsword:iron', s='kite:iron', h='nasal:iron'), 'idle'),
    ('Dwarves', '', ('iron', 'banded', 'plate', 'plate'), dict(w='warhammer:iron', s='round:iron', h='horned:iron'), 'attack'),
    ('Orc', 'Normal', ('iron', 'scale', 'scale', 'plate'), dict(w='battle axe:iron', h='great helm:iron'), 'idle'),
    ('Goblins', '', ('leather', 'leather', 'leather', 'leather'), dict(w='scimitar:iron', s='buckler:iron', h='kettle:iron'), 'attack'),
    ('Night Elf', 'Normal', ('silver', 'scale', 'mail', 'plate'), dict(w='bow:wood', s=None, h='winged:silver'), 'idle'),
    ('LizardMan', '', ('iron', 'lamellar', 'scale', None), dict(w='spear:silver', s='round:iron', h='crested:gold'), 'idle'),
    ('Skeleton', 'Normal', ('iron', 'tabard', 'mail', 'mail'), dict(w='arming sword:iron', s='heater:iron', h='nasal:iron'), 'attack'),
    ('Vampire', '', ('chitin', 'plate', 'plate', 'plate'), dict(w='morning star:gold', s='heater:gold', h='kettle:gold'), 'idle'),
    ('Demon', '', ('hell', 'plate', 'plate', 'plate'), dict(w='halberd:hell', s='tower:hell', h='horned:hell'), 'idle'),
    ('Kobold', 'Normal', ('leather', 'leather', 'leather', None), dict(w='pickaxe:iron', s=None, h='kettle:iron'), 'attack'),
]

_dmi = {}


def cells(path, state):
    if path not in _dmi:
        _dmi[path] = {n: c for n, m, c in read_dmi_full(str(path))}
    st = _dmi[path]
    return st.get(state)


def layer_cell(c, f, d):
    if c is None:
        return None
    k = f * 4 + d
    return c[k] if k < len(c) else c[d] if len(c) >= 4 else c[0]


def strip(sheet, state, armour, gear2d, d, n=3, gear_root=None):
    """One facing's picture strip (View3D.dm Remaster3DStrip): n frames of the layers stacked."""
    body = cells(ICONS/'Races64'/f'{sheet}.dmi', state) or cells(ICONS/'Races64'/f'{sheet}.dmi', '')
    tier, chest, legs, arms = armour
    lay = [body]
    g = ICONS/'Gear64'/sheet/f'{tier}.dmi'
    sty = lambda s: s if tier != 'leather' else 'leather'
    if legs: lay.append(cells(g, f'legs.{sty(legs)}.{tier}'))
    if chest: lay.append(cells(g, f'chest.{sty(chest)}.{tier}'))
    if arms:
        for side in 'LR':
            lay.append(cells(g, f'arms.{sty(arms)}.{tier}.{side}'))
    for slot, v in gear2d.items():   # today's drawn pieces, for the 2d comparison
        if not v:
            continue
        style, t2 = v.split(':')
        g2 = (gear_root or ICONS/'Gear64')/sheet/f'{t2}.dmi'
        name = {'w': 'weapon', 's': 'shield', 'h': 'helmet'}[slot]
        lay.append(cells(g2, f'{name}.{style}.{t2}'))
    out = Image.new('RGBA', (64 * n, 64), (0, 0, 0, 0))
    for f in range(n):
        fr = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        for L in lay:
            c = layer_cell(L, f, d)
            if c is not None:
                fr.alpha_composite(Image.fromarray(c))
        out.paste(fr, (64 * f, 0))
    return out


def stage(out, mode):
    out.mkdir(parents=True, exist_ok=True)
    for f in SRC.glob('r3*.png'):
        dst = out/f.name
        if not dst.exists(): shutil.copy2(f, dst)
    for f in (ROOT/'game/Interface/textures').glob('*.png'): shutil.copy2(f, out/f'r3t-{f.stem}.png')
    shutil.copy2(HERE/'gear3d.json', out/'gear3d.json')
    shutil.copy2(HERE/'anchors.json', out/'gear3d-anchors.json')
    for f in out.glob('g3p-*.png'): f.unlink()
    (out/'gear3d-pix.json').unlink(missing_ok=True)
    if mode in ('pix', 'anim'):   # the pixel pieces (pixelgear.py), from G3PIX
        for f in Path(os.environ['G3PIX']).glob('*'): shutil.copy2(f, out/f.name)
    d = json.load(open(SRC/'worldlook-3d-1.json'))
    base = next(t for t in d['things'] if t.get('model'))
    things = [t for t in d['things'] if not (t.get('model') or t.get('kind') in ('mine', 'npc', 'player', 'animal'))]
    for i, (sheet, state, armour, gear, act) in enumerate(LINEUP):
        g2 = {k: v for k, v in gear.items() if v} if mode in ('2d', 'baked') else {}
        n = 5 if mode in ('2d', 'baked') and gear.get('w') and not gear['w'].startswith('bow') else 3
        root = Path(os.environ['G3BAKED']) if mode == 'baked' else None   # the 3D pixel pieces baked into sheets (bake64.py)
        texd = []
        for di in range(4):
            name = f'r3u-g3{mode}-{i}-{di}.png'
            strip(sheet, state, armour, g2, di, n, root).save(out/name)
            texd.append(name)
        t = json.loads(json.dumps(base))
        t.update(model=None, tex=texd[0], texd=texd, wf=n, x=36 + (i % 5) * 2, y=30 + (i // 5) * 2, dir=2, act=act, ref=f'g3{i}', name=sheet, hp=100, selected=0)   # the game sends a portrait (tex): own units are then drawn full bright
        t.pop('model')
        if mode == 'anim':
            t['act'] = 'idle'   # the animation arena: everyone stands until something happens to them
        if mode in ('3d', 'pix', 'anim'):
            t['g3'] = dict(sheet=sheet, **{k: v for k, v in gear.items() if v})
            if armour[3]:
                t['g3']['arms'] = 1   # in arm armour: its doll is cut by the sleeved map (game.js)
        things.append(t)
    d['things'] = things; d['cx'], d['cy'] = 40, 31
    json.dump(d, open(out/f'worldlook-3d-g3{mode}.json', 'w'))
    html = Path(os.environ.get('G3PAGE') or ROOT/'game/Interface/remastered.html').read_text()   # G3PAGE: a candidate page (a clone of game/)
    html = html.replace("function send(action,value){window.location.href=", "function send(action,value){return;window.location.href=", 1)
    if mode == 'anim':   # the ragdolls (ragdoll.js) and the parts they are cut into (parts.py), from G3RIG
        for f in Path(os.environ['G3RIG']).glob('*'): shutil.copy2(f, out/f.name)
        shutil.copy2(ROOT/'game/Icons/Remastered/Fx/breath.png', out/'rb-breath-dragon.png')
        shutil.copy2(HERE/'g3sack.png', out/'g3sack.png')
        if (HERE/'golem'/'boss-golem.json').exists(): shutil.copy2(HERE/'golem'/'boss-golem.json', out/'boss-golem.json')   # the user's stone golem (bosses.js)   # the game's pixel sack (work.js)   # the game's pixel particles (fire, frost, holy...)
    if mode in ('3d', 'pix', 'anim') and '<!--rm-gear3d-->' in html:   # the game's page has the hooks (since 2026-10-25): only the scripts go in
        px = "const dpr=Math.min(2,window.devicePixelRatio||1);"
        assert html.count(px) == 1, 'frame size hook'
        html = html.replace(px, "const dpr=V3.pixScale||Math.min(2,window.devicePixelRatio||1);c.style.imageRendering=V3.pixScale?'pixelated':'';", 1)
        js = (HERE/'gear3d.js').read_text() + ('\n' + '\n'.join((HERE/f).read_text() for f in ('ragdoll.js', 'skills.js', 'deaths.js', 'work.js', 'magicfx.js', 'game.js', 'bosses.js')) if mode == 'anim' else '')
        html = html.replace('<!--rm-gear3d-->', '<script>\n' + js + '\n</script>', 1)
    elif mode in ('3d', 'pix', 'anim'):
        hook = 'iadd(IG,tk).v(LX,yA,LZ,hw,sh,sway,u0,u1,c[0],c[1],c[2],c[3]);'
        assert html.count(hook) == 1
        html = html.replace(hook, hook + "if(t.g3){G3.rec.length=0;v3gear3d(t,kd,v3face(t),fi,LX,yA,LZ,hw,sh,sway,right,LV,lv,nowS)}", 1)
        vsh = "'if(inst>0.5){C=i2;N=vec3(0.0);if(inst<1.5){"
        assert html.count(vsh) == 1
        html = html.replace(vsh, "G3VS+" + vsh, 1)   # the shader's gear mode (gear3d.js)
        sil = html.index('show as a green silhouette.')
        end = 'gl.uniform4f(L.tint,0,0,0,0);gl.depthFunc(gl.LESS);gl.depthMask(true);gl.disable(gl.BLEND)}'
        j = html.index(end, sil) + len(end)
        html = html[:j] + 'g3draw();' + html[j:]
        # live 3D pieces are drawn each frame; pixel ones are kept with the unit (the page's still records), but not
        # slid along a step by its walking records (v3walkEmit), which don't carry them
        keep = 'gen&&!walking&&still&&'
        assert html.count(keep) == 1, 'still records hook'
        html = html.replace(keep, '!(t.g3&&!G3.pix)&&' + keep, 1)
        wk = 'if(gen&&walking&&still&&t._pl&&!t.climb)'
        assert html.count(wk) == 1, 'walking records hook'
        html = html.replace(wk, 'if(gen&&walking&&still&&t._pl&&!t.climb&&!t.g3)', 1)
        mk = 'v3rcMake(t,kd,rcEp,gen,rcW,IG,sil,castG,contact,rings,rs0,BL,bs0)'
        assert html.count(mk) == 1
        html = html.replace(mk, 'g3keep(' + mk + ',t)', 1)
        em = 'v3rcEmit(R,IG,sil,castG,contact,rings,BL,iadd);'
        assert html.count(em) == 2, 'kept records hooks'   # the plain-unit pass and the full check
        html = html.replace(em, em + 'if(R.g3)g3put(R);')
        ck = '&&R.wf===t.wf&&'
        assert html.count(ck) == 1
        html = html.replace(ck, '&&R.wf===t.wf&&R.g3k===g3key(t)&&', 1)
        # a pixel world to try (the arena's World row): the view drawn at a fraction of the screen's pixels, then
        # scaled up with hard edges, so one drawn pixel is a block of the screen's
        px = "function v3frame(ts){V3.lastFrameAt=performance.now();v3kick();if(!V3.on){v3floatsTick();return}const gl=V3.gl,c=$('world3d');const dpr=Math.min(2,window.devicePixelRatio||1);"
        assert html.count(px) == 1, 'frame size hook'
        html = html.replace(px, px.replace("const dpr=Math.min(2,window.devicePixelRatio||1);", "const dpr=V3.pixScale||Math.min(2,window.devicePixelRatio||1);c.style.imageRendering=V3.pixScale?'pixelated':'';"), 1)
        assert html.count('</head>') == 1
        js = (HERE/'gear3d.js').read_text() + ('\n' + '\n'.join((HERE/f).read_text() for f in ('ragdoll.js', 'skills.js', 'deaths.js', 'work.js', 'magicfx.js', 'game.js', 'bosses.js')) if mode == 'anim' else '')
        html = html.replace('</head>', '<script>\n' + js + '\n</script></head>', 1)
    i = html.index('<head>') + len('<head>')
    (out/'replay.html').write_text(html[:i] + '<script>window.__errs=[];addEventListener("error",e=>__errs.push(e.message+" @"+e.lineno));' + wr.REPLAY + '</script>' + html[i:])


def cams(mode):
    s = f'scene=g3{mode}&clean=1&dayp=0.4'
    c = {
        'corner45': f'{s}&cx=40&cy=31&dist=5.5&pitch=0.62&yaw=0.785',
        'corner315': f'{s}&cx=40&cy=31&dist=5.5&pitch=0.62&yaw=-0.785',
        'front': f'{s}&cx=40&cy=31&dist=5.5&pitch=0.45&yaw=0',
        'game': f'{s}&cx=40&cy=31&dist=11&pitch=0.62&yaw=0.785',
    }
    c['hands'] = f'{s}&cx=37&cy=30.3&dist=2.4&pitch=0.5&yaw=0.785'   # the Human's and dwarf's fists up close
    c['hands2'] = f'{s}&cx=37&cy=30.3&dist=2.4&pitch=0.5&yaw=-0.785'
    c['swing'] = f'{s}&cx=38&cy=30.5&dist=2.6&pitch=0.5&yaw=0.785'   # the dwarf and skeleton attacking: a strip over time
    for k, yaw in enumerate((0.0, 0.5, 1.0, 1.6, 2.4, 3.14)):
        c[f'turn{k}'] = f'{s}&cx=38&cy=30&dist=3.2&pitch=0.55&yaw={yaw}'
    return c


def shoot(out, mode, tag, w=1400, h=800, only=None):
    from playwright.sync_api import sync_playwright
    wr.OUT = out
    files = {}
    with wr.Server() as s, sync_playwright() as pw:
        b, p, errs = wr.browser(pw, w, h)
        for name, q in cams(mode).items():
            if only and name not in only:
                continue
            wr.load(p, s.base + q, settle=4000)
            f = out/f'{name}-{tag}.png'
            if name == 'swing':   # eight moments through one 0.9 s swing, side by side
                shots = []
                for k in range(8):
                    p.screenshot(path=str(f)); shots.append(Image.open(f).crop((380, 120, 880, 620)).copy())
                    p.wait_for_timeout(112)
                im = Image.new('RGB', (500 * 4, 500 * 2))
                for k, sh in enumerate(shots):
                    im.paste(sh, ((k % 4) * 500, (k // 4) * 500))
                im.save(f)
            else:
                p.screenshot(path=str(f))
            files[name] = str(f)
        files['errors'] = errs + p.evaluate('window.__errs||[]')
        files['g3'] = p.evaluate('typeof G3!=="undefined"?{ready:G3.ready,failed:G3.failed||null,n:Object.keys(G3.P).length,gpu:!!G3.B,cpuVerts:G3.va?G3.va.length/12:0}:null')
        b.close()
    print(json.dumps(files, indent=1))
    return files


if __name__ == '__main__':
    out = Path(sys.argv[1]); mode = sys.argv[2] if len(sys.argv) > 2 else '3d'
    tag = sys.argv[3] if len(sys.argv) > 3 else mode
    only = sys.argv[4].split(',') if len(sys.argv) > 4 else None
    stage(out, mode)
    shoot(out, mode, tag, only=only)
