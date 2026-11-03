"""Package a local fitting viewer using the game's actual 16-angle gear strips.

No game sources or sprite images are modified. Images are embedded unchanged;
the browser performs palette decoding and frame selection at display time.
"""
from pathlib import Path
import base64
import hashlib
import json
import re

from PIL import Image

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
GOA = Path('/Users/kiwimango/Downloads/GOA Source')
GEAR = PROJECT / 'remastered/game/Interface/gear3d'


def image_data(path):
    return 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()


def dmi(path):
    with Image.open(path) as image:
        description = image.info['Description']
        width = re.search(r'^\s*width\s*=\s*(\d+)', description, re.M)
        height = re.search(r'^\s*height\s*=\s*(\d+)', description, re.M)
        result = dict(src=image_data(path), width=int(width[1]) if width else 32,
                      height=int(height[1]) if height else 32, columns=0, states=[])
        result['columns'] = image.width // result['width']
    offset = 0
    for block in re.split(r'(?=^state\s*=)', description, flags=re.M)[1:]:
        def number(key, fallback):
            match = re.search(r'^\s*' + key + r'\s*=\s*(\d+)', block, re.M)
            return int(match[1]) if match else fallback
        state = dict(name=re.search(r'^state\s*=\s*"(.*?)"', block, re.M)[1],
                     offset=offset, dirs=number('dirs', 1), frames=number('frames', 1),
                     movement=number('movement', 0))
        result['states'].append(state)
        offset += state['dirs'] * state['frames']
    return result


def main():
    metadata = json.loads((GEAR / 'gear3d-pix.json').read_text())
    assert metadata['facings'] == 16
    images = {}
    for name, piece in metadata['pieces'].items():
        for pose in range(len(piece['poses'])):
            filename = 'g3p-' + name.replace(' ', '_') + '-idx-' + str(pose) + '.png'
            path = GEAR / filename
            if not path.exists():
                raise FileNotFoundError(path)
            images[filename] = image_data(path)

    native = {name: dmi(GOA / 'icons' / name) for name in ['base_m1.dmi', 'base_m2.dmi', 'base_m3.dmi']}
    goa_armor = {name: dmi(GOA / name) for name in [
        'armor/armor_body.dmi', 'armor/armor_sholders.dmi',
        'armor/armor_body_dred.dmi', 'armor/armor_sholders_dred.dmi']}
    goa_sword = {name: dmi(GOA / name) for name in [
        'sword1/swordover.dmi', 'sword1/sword1.dmi', 'sword1/sword2.dmi',
        'sword1/sword3.dmi', 'sword1/sword4.dmi']}
    armor = dmi(PROJECT / 'remastered/game/Icons/Remastered/Gear64/Human/iron.dmi')
    draft = HERE.parent / 'goa-races-lotr-v1.png'
    boxes = []
    with Image.open(draft) as image:
        alpha = image.getchannel('A').point(lambda value: 255 if value >= 180 else 0)
        for y0, y1 in [(50, 310), (310, 530), (530, 790), (790, 1040), (1040, 1254), (1254, 1510)]:
            row = []
            for x0, x1 in [(90, 300), (310, 510), (520, 725), (730, 940)]:
                box = alpha.crop((x0, y0, x1, y1)).getbbox()
                if not box:
                    raise ValueError('Missing draft body')
                row.append([box[0] + x0, box[1] + y0, box[2] + x0, box[3] + y0])
            boxes.append(row)
    data = dict(gear=metadata, images=images, native=native, goaArmor=goa_armor, goaSword=goa_sword,
                dmArmor=armor, draft=image_data(draft), boxes=boxes)
    template = (HERE / 'viewer.template.html').read_text()
    output = template.replace('/*EMBEDDED_DATA*/null', json.dumps(data, separators=(',', ':')))
    assert '/*EMBEDDED_DATA*/' not in output
    (HERE / 'index.html').write_text(output)
    (HERE / 'goa-held-sword.html').write_text(output.replace('/*INITIAL_GOA_SWORD*/false', 'true'))
    (HERE / 'sources.json').write_text(json.dumps(dict(
        gear_source=str(GEAR), gear_metadata_sha256=hashlib.sha256((GEAR / 'gear3d-pix.json').read_bytes()).hexdigest(),
        facings=metadata['facings'], pieces=len(metadata['pieces']), embedded_gear_strips=len(images),
        draft_body_source=str(draft), image_modifications='none; frame selection and palette decoding happen in browser',
        status='fitting prototype; four-view draft bodies, existing 16-angle gear; no live game integration'
    ), indent=2))
    print(f'Built {HERE / "index.html"}: {len(images)} original gear strips / {len(metadata["pieces"])} pieces')


if __name__ == '__main__':
    main()
