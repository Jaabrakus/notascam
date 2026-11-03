"""Copy approved appearances into six-row AI edit templates; no limb art is made."""
import json
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
REGISTRY = HERE.parents[1] / 'armory' / 'bodies.json'
STATES = ['NoLeftArm', 'NoRightArm', 'NoArms', 'NoLeftLeg', 'NoRightLeg', 'NoLegs']


def main():
    destination = HERE / 'references'
    destination.mkdir(exist_ok=True)
    bodies = json.loads(REGISTRY.read_text())['bodies']
    catalog = []
    for body in bodies:
        with Image.open(body['source']) as source:
            source = source.convert('RGBA')
            reference = Image.new('RGBA', (1024, 256))
            scale = body['targetHeight'] / body['normalization']['referenceHeight'] * 4
            for view in range(4):
                x, y, w, h = body['sourceRects'][0][view]
                l, t, r, bottom = body['frameBounds'][0][view]
                cell = source.crop((x, y, x + w, y + h))
                cell = cell.resize((round(w * scale), round(h * scale)), Image.Resampling.NEAREST)
                dx = round(128 - (l + r) * .5 * scale)
                dy = round(244 - bottom * scale)
                reference.alpha_composite(cell, (view * 256 + dx, dy))
        path = destination / (body['id'] + '-body.png')
        reference.save(path)
        # A repeated, intact reference provides an explicit 24-cell layout.
        # Actual missing limbs must be drawn by image_gen, not this script.
        template = Image.new('RGBA', (1024, 1536))
        for row in range(6):
            template.paste(reference, (0, row * 256))
        template_path = destination / (body['id'] + '-edit-template.png')
        template.save(template_path)
        catalog.append(dict(bodyId=body['id'], race=body['raceKey'], label=body['label'],
                            variant=body['variant'], status=body['status'],
                            source=body['source'], reference=str(path), template=str(template_path),
                            injuryStates=STATES, detachedPiecesRequested=False,
                            stage='intact layout reference prepared; AI redraw pending'))
    (HERE / 'body-catalog.json').write_text(json.dumps(catalog, indent=2) + '\n')
    print(json.dumps({'appearances': len(catalog), 'hybrids': sum(r['variant'] in ['Possessed1','Possessed2','Marked','Ashen','Hellblooded','Werewolf','Zombie'] for r in catalog), 'detachedPiecesGenerated': 0}))


if __name__ == '__main__':
    main()
