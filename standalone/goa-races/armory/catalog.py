"""Catalog drawable equipment designs and their real source-backed materials.

This is an art catalog, not a replacement for gameplay item definitions. Images
remain source files; callers choose which assets to embed or load.
"""
from pathlib import Path
import hashlib
import json
import re

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GEAR = ROOT / 'standalone/remastered/game/Interface/gear3d'
GEAR64 = ROOT / 'standalone/remastered/game/Icons/Remastered/Gear64'
GOA = Path('/Users/kiwimango/Downloads/GOA Source')
DIRECTIONS = ['South', 'North', 'East', 'West']


def source_name(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_dmi(path):
    with Image.open(path) as image:
        description = image.info['Description']
        def number(block, key, fallback):
            match = re.search(r'^\s*' + key + r'\s*=\s*(\d+)', block, re.M)
            return int(match[1]) if match else fallback
        header = description.split('state =', 1)[0]
        width, height = number(header, 'width', 32), number(header, 'height', 32)
        metadata = dict(width=width, height=height, columns=image.width // width,
                        imageSize=list(image.size), states=[], sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    offset = 0
    for block in re.split(r'(?=^state\s*=)', description, flags=re.M)[1:]:
        match = re.search(r'^state\s*=\s*"(.*?)"', block, re.M)
        if not match:
            continue
        delay = re.search(r'^\s*delay\s*=\s*([\d., ]+)', block, re.M)
        state = dict(name=match[1], offset=offset, dirs=number(block, 'dirs', 1),
                     frames=number(block, 'frames', 1), movement=number(block, 'movement', 0))
        state['delays'] = [float(value) for value in delay[1].split(',')] if delay else [1] * state['frames']
        metadata['states'].append(state)
        offset += state['dirs'] * state['frames']
    return metadata


def label(text):
    return text.replace('_', ' ').replace('-', ' ').title()


def build_catalog():
    """Return JSON-serializable art recipes without image data or side effects."""
    gear = json.loads((GEAR / 'gear3d-pix.json').read_text())
    sources, items, body = {}, [], {}

    def register(path):
        key = source_name(path)
        if key not in sources:
            sources[key] = read_dmi(path)
        return key, sources[key]

    def layer(path, state_name=None):
        key, meta = register(path)
        record = dict(source=key, width=meta['width'], height=meta['height'], columns=meta['columns'])
        if state_name is None:
            record['states'] = meta['states']
        else:
            states = [s for s in meta['states'] if s['name'] == state_name]
            if not states:
                raise ValueError(f'Missing source state {path}: {state_name}')
            record['state'] = state_name
            record['states'] = states
        return record

    for key, piece in gear['pieces'].items():
        prefix, name = key.split('.', 1)
        slot = 'head' if prefix == 'helmet' else prefix
        strips = []
        for pose in range(len(piece['poses'])):
            filename = 'g3p-' + key.replace(' ', '_') + '-idx-' + str(pose) + '.png'
            path = GEAR / filename
            if not path.is_file():
                raise FileNotFoundError(path)
            strips.append(source_name(path))
        items.append(dict(id=key, label=label(name), slot=slot, renderer='gear16',
                          pieceKey=key, materials=piece['tiers'], referenceMaterial=piece['ref'],
                          facings=gear['facings'], poseCount=len(piece['poses']),
                          poses=piece['poses'], strips=strips,
                          anchorSlot={'head': 'head', 'weapon': 'weapon', 'shield': 'shield'}[slot],
                          sourceMetadata=source_name(GEAR / 'gear3d-pix.json'),
                          materialRecipes={},
                          notes='Original material-indexed 16-angle strips; gear pose frames do not create missing body animations.'))

    # Discover armor and clothes from actual state names, keeping limb layers paired.
    ignored = {'fx', 'oldlooks'}
    for path in sorted((GEAR64 / 'Human').glob('*.dmi')):
        if path.stem.startswith('old-') or path.stem in ignored:
            continue
        meta = read_dmi(path)
        for state in meta['states']:
            name = state['name']
            parts = name.split('.')
            if parts[0] not in {'chest', 'legs', 'arms'}:
                continue
            if name == 'legs.boots':
                design, slot, material = 'feet.boots', 'feet', 'original'
            elif name == 'legs.cloth':
                design, slot, material = 'legs.cloth', 'legs', 'cloth'
            elif len(parts) >= 3:
                design, slot, material = '.'.join(parts[:2]), parts[0], parts[2]
            else:
                continue
            info = body.setdefault(design, dict(id=design, label=label(design.split('.', 1)[1]),
                slot=slot, renderer='dmi', materials=[], materialRecipes={},
                anchorSlot={'chest':'torso','legs':'hips','arms':'shoulders','feet':'feet'}[slot],
                sourceRaces={}, notes='Original 64-pixel full-body overlay; fit to the updated body rig.'))
            if material not in info['materials']:
                info['materials'].append(material)
            recipe = info['materialRecipes'].setdefault(material, dict(layers=[], armedLayers=[]))
            selected = layer(path, name)
            if name.endswith(' armed'):
                recipe['armedLayers'].append(selected)
            else:
                recipe['layers'].append(selected)
            for folder in GEAR64.iterdir():
                matching = folder / path.name
                if folder.is_dir() and matching.is_file():
                    info['sourceRaces'].setdefault(folder.name, {})[material] = source_name(matching)
    items.extend(body.values())

    # GOA's original held blade is multipart during w-attack. Pixel_y grows up in
    # BYOND; these catalog offsets are normalized to a 64px space with +y down.
    held = layer(GOA / 'sword1/swordover.dmi')
    attack_layers = []
    for filename, dx, dy in [('sword1.dmi', -24, -23), ('sword2.dmi', 12, 12),
                             ('sword3.dmi', 0, 20), ('sword4.dmi', 0, -21)]:
        record = layer(GOA / 'sword1' / filename, 'w-attack')
        record.update(offset=[dx * 2, -dy * 2], offsetSpace='64px, +x right, +y down')
        attack_layers.append(record)
    items.append(dict(id='goa.sword', label='GOA Original Sword', slot='weapon', renderer='goaHeld',
        materials=['original'], facings=4, anchorSlot='weapon',
        materialRecipes={'original': dict(layers=[held], attackLayers=attack_layers)},
        notes='Original held and walking overlay plus four w-attack components. Native source-body alignment is authored for GOA 32px bodies; updated race fitting is required.'))
    recipes = {}
    for material, suffix in [('original', ''), ('dark-red', '_dred')]:
        recipes[material] = dict(layers=[layer(GOA / 'armor' / ('armor_body' + suffix + '.dmi')),
                                        layer(GOA / 'armor' / ('armor_sholders' + suffix + '.dmi'))])
    items.append(dict(id='goa.chest', label='GOA Chest and Shoulders', slot='chest', renderer='dmi',
        materials=list(recipes), materialRecipes=recipes, anchorSlot='torso',
        notes='Native 32px chest and shoulder overlays; choose the matching body state and movement when available.'))

    material_ids = sorted({m for item in items for m in item['materials']})
    by_slot = {slot: sum(item['slot'] == slot for item in items) for slot in ['weapon', 'shield', 'head', 'chest', 'arms', 'legs', 'feet', 'hands', 'back']}
    return dict(format='dungeon-master.universal-gear-catalog', version=1,
        coordinateSpace=64, directionOrder=DIRECTIONS,
        slots=[dict(id=s, label=label(s), designCount=count, drawable=count>0) for s,count in by_slot.items()],
        materials=[dict(id=m, label=label(m)) for m in material_ids],
        items=items, sources=sources,
        counts=dict(designs=len(items), bySlot=by_slot, shapeMaterialVariants=sum(len(i['materials']) for i in items),
                    gear16Designs=sum(i['renderer']=='gear16' for i in items), gear16Strips=sum(len(i.get('strips', [])) for i in items),
                    canonicalDmiSources=len(sources)),
        source=dict(gearMetadata=source_name(GEAR/'gear3d-pix.json'),
                    gearMetadataSha256=hashlib.sha256((GEAR/'gear3d-pix.json').read_bytes()).hexdigest(),
                    canonicalArmorRoot=source_name(GEAR64/'Human'), nativeGoaRoot=str(GOA)),
        notes=['A universal equipment design is selected by id + supported material, then fitted to each race and direction.',
               'Shape/material combinations are drawable art variants, not new gameplay item definitions or invented combat statistics.',
               'Race-specific original armor source paths are optional source alternatives; canonical recipes use Human overlays.',
               'Hands/gloves and back/cloak slots have no modern source-backed design in this catalog and are explicitly empty.',
               'Gear16 strips have sixteen orientations; body source sprites may still have only four.'])


def main():
    catalog = build_catalog()
    (HERE/'catalog.json').write_text(json.dumps(catalog, indent=2))
    lines = ['# Universal equipment art catalog', '',
        'This catalog groups real drawable designs by shape and supported material. It does not replace gameplay item definitions or invent combat statistics.', '',
        f"**{catalog['counts']['designs']} designs**, **{catalog['counts']['shapeMaterialVariants']} supported shape/material variants**. The 43 existing 3D-derived gear designs use 136 original strips at sixteen orientations.", '',
        '| Slot | Drawable designs |', '|---|---:|']
    lines += [f"| {slot['label']} | {slot['designCount']} |" for slot in catalog['slots']]
    lines += ['', '## Designs', '', '| ID | Slot | Materials | Renderer |', '|---|---|---:|---|']
    lines += [f"| `{i['id']}` | {i['slot']} | {len(i['materials'])} | `{i['renderer']}` |" for i in catalog['items']]
    lines += ['', '## Rendering contract', '',
        '`catalog.py` exposes `build_catalog()` with no image embedding or writes. `catalog.json` is its generated snapshot.', '',
        '- `gear16`: `pieceKey`, `strips` and per-pose `w/h/ax/ay` come from the existing metadata. Only `materials` listed for that shape are declared supported. Decode the original material-index pixels using `gear3d-pix.json.index`, then select one of sixteen horizontal strip cells.',
        '- `dmi`: each supported material has `materialRecipes[material].layers`. Every layer supplies its actual `source`, frame width/height, source columns, and selected `states` with offsets, direction/frame counts, movement and delays. A layer with `state` selects that exact state; GOA dynamic layers omit it and list all source states.',
        '- DM armor overlays are 64px full-body layers. Arms use paired L/R layers. `armedLayers` contains the alternate right-arm pose and replaces the normal right-arm layer when used; it must not be added on top of the normal right-arm layer.',
        '- `feet.boots` is a real source state named `legs.boots` in `cloth.dmi`. There are no dedicated modern hand/glove or back/cloak assets in the catalog.',
        '- `goaHeld`: the held/walk overlay lives in `layers`; `attackLayers` are separate w-attack pieces. Their offsets are already converted from BYOND +y-up 32px offsets into +y-down 64px fitting coordinates. GOA source frames should be displayed at 2x their 32px size.',
        '- `sourceRaces` provides original race-specific armor filenames as alternatives; inspect their own metadata when switching sources. Canonical recipes and source metadata in this catalog are Human-based.', '',
        'Armory renderers still need body-fit anchors, scale, depth ordering, and limb availability rules. These recipes do not create missing body animations. Full source transparency and source images remain unchanged.', '',
        'Source paths inside the project are project-relative; GOA paths are absolute because that input lives outside this workspace. No network lookup or image generation is performed.', '']
    (HERE/'CATALOG.md').write_text('\n'.join(lines))
    print(json.dumps(catalog['counts']))


if __name__ == '__main__':
    main()
