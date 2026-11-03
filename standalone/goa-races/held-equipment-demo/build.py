"""Build a small, self-contained example using the shared equipment renderer."""
from pathlib import Path
import base64
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARMORY = HERE.parent / 'armory'

catalog = json.loads((ARMORY / 'catalog.json').read_text())
catalog['items'] = [i for i in catalog['items'] if i['id'] in ('weapon.arming sword','weapon.hand axe','weapon.mace','weapon.dagger','weapon.spear','weapon.bow','weapon.crystal staff','weapon.warhammer','weapon.longsword','weapon.scimitar','weapon.battle axe','weapon.morning star','shield.round')]
body = next(b for b in json.loads((ARMORY / 'bodies.json').read_text())['bodies'] if b['id'] == 'human')
paths = {body['source']} | {p for i in catalog['items'] for p in i['strips']}
paths.add(str(HERE / 'combat/body.png'))
action_sources={kind:str(HERE/'combat'/kind/'body.png') for kind in ['spear','bow','staff']}
action_sources['one-hand-sweep']=str(HERE/'combat/spear-one-hand-sweep/body.png')
action_sources['spear-jab']=str(HERE/'combat/spear-short-jab/body.png')
paths.update(action_sources.values())
paths.add(str(HERE/'combat/arrow.png'))
paths.add(str(HERE/'combat/universal-flinch/body.png'))
images = {}
for name in paths:
    path = Path(name)
    if not path.is_absolute():
        path = ROOT / path
    images[name] = 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()
data = dict(catalog=catalog, bodies=[body], images=images,
            combatSource=str(HERE / 'combat/body.png'),
            actionSources=action_sources,arrowSource=str(HERE/'combat/arrow.png'),
            sweepProfile=json.loads((HERE/'combat/spear-one-hand-sweep/rig.json').read_text()),
            jabProfile=json.loads((HERE/'combat/spear-short-jab/rig.json').read_text()),
            flinchProfile=json.loads((HERE/'combat/universal-flinch/rig.json').read_text()),flinchSource=str(HERE/'combat/universal-flinch/body.png'),
            gear=json.loads((ROOT / 'standalone/remastered/game/Interface/gear3d/gear3d-pix.json').read_text()))
html = (HERE / 'template.html').read_text().replace('/*DATA*/null', json.dumps(data))
html = html.replace('/*ENGINE*/', (ARMORY / 'equipment.js').read_text()).replace('/*APP*/', (HERE/'actions.js').read_text()+'\n'+(HERE / 'demo.js').read_text())
(HERE / 'index.html').write_text(html)
(ROOT / 'Dungeon Master Sample/GOA Sword and Shield Demo.html').write_text(html)
(ROOT / 'Dungeon Master Sample/GOA Human Combat Sample.html').write_text(html)
print('Built human weapon action demo')
