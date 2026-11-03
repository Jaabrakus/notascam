"""Package the shared armory as a self-contained local HTML tool."""
from pathlib import Path
import base64
import csv
import io
import json

from catalog import build_catalog
from body_registry import build_bodies

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def main():
    catalog = build_catalog()
    for item in catalog['items']:
        if item['id'] == 'goa.sword':
            item['fitAdaptation'] = dict(grip64=[21,43], completeSourceDirections=['South','East'],
                reflectedDirections={'North':'South','West':'East'},
                notes='Incomplete North/West held overlays are reconstructed by reflection around the measured grip; source files remain unchanged.')
    registry_path = HERE / 'bodies.json'
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else build_bodies()
    paths = set(catalog['sources'])
    for item in catalog['items']:
        paths.update(item.get('strips', []))
    paths.update(body['source'] for body in registry['bodies'])
    images = {str(p): 'data:image/png;base64,' + base64.b64encode(resolve(p).read_bytes()).decode() for p in sorted(paths)}
    gear = json.loads((ROOT / 'standalone/remastered/game/Interface/gear3d/gear3d-pix.json').read_text())
    data = dict(catalog=catalog, bodies=registry['bodies'], images=images, gear=gear)
    html = (HERE / 'armory.template.html').read_text()
    for marker, source in {
        '/*DATA*/null': json.dumps(data, separators=(',', ':')),
        '/*SPRITE_ENGINE*/': (HERE.parent / 'sprite-engine/sprite-engine.js').read_text(),
        '/*RENDERER*/': (HERE / 'equipment.js').read_text(),
        '/*APPLICATION*/': (HERE / 'armory.js').read_text(),
    }.items():
        html = html.replace(marker, source)
    (HERE / 'index.html').write_text(html)
    (ROOT / 'Dungeon Master Sample/GOA Universal Armory.html').write_text(html)
    (HERE / 'catalog.json').write_text(json.dumps(catalog, indent=2))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'name', 'slot', 'material', 'renderer', 'directions'])
    for item in catalog['items']:
        for material in item['materials']:
            writer.writerow([item['id'], item['label'], item['slot'], material, item['renderer'], item.get('facings', 4)])
    (HERE / 'Universal Gear and Weapons.csv').write_text(output.getvalue())
    (ROOT / 'Dungeon Master Sample/Universal Gear and Weapons.csv').write_text(output.getvalue())
    print(f'Armory built: {len(registry["bodies"])} bodies, {len(catalog["items"])} designs, {len(images)} embedded source images.')


if __name__ == '__main__':
    main()
