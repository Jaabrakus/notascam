"""Pack direct AI artwork without palette changes, head splicing or body warps."""
from collections import deque
import html
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import pixel_cutter
import build_pixel_assets as packing
from build_hybrid_injuries import ai_cells

STATES = ['Normal', 'NoLeftArm', 'NoRightArm', 'NoArms', 'NoLeftLeg', 'NoRightLeg', 'NoLegs']


def clean(frame):
    visible = frame[..., 3] >= 128
    unseen = visible.copy()
    components = []
    for y, x in zip(*np.nonzero(visible)):
        if not unseen[y, x]:
            continue
        pending, points = deque([(int(y), int(x))]), []
        unseen[y, x] = False
        while pending:
            yy, xx = pending.popleft()
            points.append((yy, xx))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = yy + dy, xx + dx
                    if (dy or dx) and 0 <= ny < 64 and 0 <= nx < 64 and unseen[ny, nx]:
                        unseen[ny, nx] = False
                        pending.append((ny, nx))
        components.append(points)
    if not components:
        raise ValueError('An injury pose is empty')
    largest = max(components, key=len)
    output = np.zeros_like(frame)
    for y, x in largest:
        output[y, x, :3] = frame[y, x, :3]
        output[y, x, 3] = 255
    return output, int(visible.sum()) - len(largest)


def main():
    directory = HERE / 'direct-repairs'
    bodies = {b['id']: b for b in json.loads((HERE.parents[1] / 'armory/bodies.json').read_text())['bodies']}
    records, sections = [], []
    for key, title in [('elf-ashen', 'Blond Ashen Elf'), ('orc-werewolf', 'Orc Werewolf')]:
        body = bodies[key]
        arms, arm_path = ai_cells(body, 'arms', directory / (key + '-arms-v1.png'))
        legs, leg_path = ai_cells(body, 'legs', directory / (key + '-legs-v1.png'))
        normal = [np.asarray(cell) for cell in pixel_cutter.render_body(body)[0]]
        # Reorder whole AI frames where the model swapped anatomical sides in
        # a back view. This does not repaint or mirror any character pixels.
        if key == 'elf-ashen':
            legs[0][1], legs[1][1] = legs[1][1], legs[0][1]
        else:
            arms[0][1], arms[1][1] = arms[1][1], arms[0][1]
        # In these cardinal profiles the missing far arm is fully occluded.
        # Reusing the approved complete profile preserves the visible near arm.
        arms[0][2] = normal[2].copy()
        arms[1][3] = normal[3].copy()
        all_rows = [normal] + arms + legs
        cleaned, removed = [], 0
        for row in all_rows:
            clean_row = []
            for frame in row:
                result, count = clean(frame)
                removed += count
                assert not result[result[..., 3] == 0].any(), 'Hidden background pixels remain'
                # Every surviving RGB sample must be unchanged source artwork.
                keep = result[..., 3] > 0
                assert np.array_equal(result[keep, :3], frame[keep, :3])
                clean_row.append(Image.fromarray(result))
            cleaned.append(clean_row)
        # Neither character has a tail. A no-leg pose must not retain foot pixels.
        for frame in cleaned[-1]:
            assert not np.asarray(frame)[57:, :, 3].any(), 'Stray feet remain in NoLegs'
        sheet_path = directory / (key + '-injuries64-v1.png')
        dmi_path = sheet_path.with_suffix('.dmi')
        packing.sheet(cleaned, sheet_path)
        packing.dmi({state: [row] for state, row in zip(STATES, cleaned)}, [0], [200], False, dmi_path)
        record = dict(id=key, label=title, path=str(sheet_path), dmi=str(dmi_path),
                      sourceArt=[arm_path, leg_path], approvedBody=body['source'],
                      frameSize=[64, 64], columns=4, rows=7, rowLabels=STATES,
                      directions=packing.DIRECTIONS, detachedFragmentsRemoved=removed,
                      survivingRGBUnchanged=True, noLegFootClearancePassed=True,
                      method='direct AI edits; common-scale nearest-neighbor frame packing; whole-frame state ordering; isolated alpha speck cleanup',
                      farArmProfiles='approved complete profile reused where the missing far arm is fully occluded',
                      animation='standing poses only; walk animations not verified',
                      status='targeted direct repair; ready for visual review, not installed into live game')
        (directory / (key + '-injuries64-v1.json')).write_text(json.dumps(record, indent=2) + '\n')
        records.append(record)
        relative = '../standalone/goa-races/limbs/ai-redraws/direct-repairs/' + sheet_path.name
        rows = []
        for index, state in enumerate(STATES):
            rows.append('<div class="row"><b>' + state + '</b><div class="crop"><img src="' + html.escape(relative, quote=True) + '" style="transform:translateY(-' + str(index * 128) + 'px)" alt="' + state + '"></div></div>')
        sections.append('<section><h2>' + title + '</h2><p><a href="' + relative + '">PNG sheet</a> · <a href="' + relative.replace('.png', '.dmi') + '">DMI</a></p><div class="directions">Front · Back · East · West</div>' + ''.join(rows) + '</section>')
    document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Blond Ashen Elf and Orc Werewolf — Limb Repairs</title><style>body{margin:24px;background:#1e2026;color:#eee;font:15px system-ui}h1{font-size:24px}h2{font-size:20px}a{color:#9cd3ff}p{color:#bac0cb}.sheets{display:flex;flex-wrap:wrap;gap:30px}.row{display:flex;align-items:center;gap:12px}.row>b{width:100px;font-size:13px}.crop{width:512px;height:128px;overflow:hidden;background:conic-gradient(#333 25%,#292c33 0 50%,#333 0 75%,#292c33 0);background-size:20px 20px}.crop img{display:block;width:512px;height:896px;image-rendering:pixelated}.directions{margin-left:112px;width:512px;text-align:center;padding:10px 0;word-spacing:28px}</style><h1>Blond Ashen Elf and Orc Werewolf — Direct Limb Repairs</h1><p>64×64 frames, displayed at 2×. Direct AI artwork with original colours; red cut caps retained. Standing poses only—walking animation remains to be checked.</p><main class="sheets">'''
    sample = HERE.parents[3] / 'Dungeon Master Sample'
    output = sample / 'Blond Ashen Elf and Orc Werewolf - Limb Sheets.html'
    output.write_text(document + ''.join(sections) + '</main></html>')
    (directory / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps({'framesChecked': 56, 'bodies': 2, 'preview': str(output), 'removedIsolatedPixels': sum(r['detachedFragmentsRemoved'] for r in records)}))


if __name__ == '__main__':
    main()
