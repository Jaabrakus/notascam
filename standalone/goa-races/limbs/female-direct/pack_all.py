"""Track and pack every registered female appearance from direct AI sheets."""
import base64
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pack import normalize, clean, STATES, packing


def side_score(frame, both_missing, category, height):
    yy, xx = np.mgrid[:64, :64]
    zone = ((yy >= round(62 - height * .54)) & (yy < round(62 - height * .20))) if category == 'arms' else yy >= round(62 - height * .23)
    added = (frame[..., 3] >= 128) & ~(both_missing[..., 3] >= 128) & zone
    return int(added[:, :30].sum()) - int(added[:, 34:].sum())


def order_singles(frames, category, height, flags):
    for view in (0, 1):
        scores = [side_score(frames[row][view], frames[2][view], category, height) for row in (0, 1)]
        # Missing anatomical left retains the viewer-left limb in front, and
        # the viewer-right limb in back. Reorder whole poses, never body pixels.
        sign = 1 if view == 0 else -1
        if scores[0] * sign < 0 and scores[1] * sign > 0:
            frames[0][view], frames[1][view] = frames[1][view], frames[0][view]
        elif not (scores[0] * sign > 0 and scores[1] * sign < 0):
            bad = [row for row in (0, 1) if scores[row] * sign * (1 if row == 0 else -1) <= 0]
            flags.append(dict(category=category, view=['South','North'][view], issue='single-limb side requires visual review', scores=scores, badRows=bad))


def apply_overrides(frames, category, folder, height, selected_rows=(0, 1, 2)):
    applied = set()
    for row in selected_rows:
        for view, name in enumerate(packing.DIRECTIONS):
            path = folder / 'overrides' / (category + '-row' + str(row) + '-' + name + '.png')
            if not path.exists():
                continue
            metadata = path.with_suffix('.json')
            if not metadata.exists() or json.loads(metadata.read_text()).get('visualReview') != 'accepted':
                continue
            im = Image.open(path).convert('RGBA')
            box = im.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox()
            if box is None:
                raise ValueError('Empty corrective pose: ' + str(path))
            crop = im.crop(box)
            scale = min(height / crop.height, 60 / crop.width)
            resized = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.NEAREST)
            frame = Image.new('RGBA', (64, 64))
            frame.paste(resized, ((64 - resized.width)//2, 62 - resized.height))
            frames[row][view] = np.asarray(frame)
            applied.add((category, row, name))
    return applied


def align_head(frame, reference, height):
    """Translate the complete pose to its approved direction's head anchor."""
    def center(image):
        visible = image[..., 3] >= 128
        ys, xs = np.nonzero(visible)
        top = int(ys.min())
        return float(np.median(xs[ys < top + height * .30]))
    shift = round(center(reference) - center(frame))
    if not shift:
        return frame
    ys, xs = np.nonzero(frame[..., 3] >= 128)
    if xs.min() + shift < 0 or xs.max() + shift >= 64:
        raise ValueError('Approved head alignment would clip a complete pose')
    aligned = np.zeros_like(frame)
    if shift > 0:
        aligned[:, shift:] = frame[:, :-shift]
    else:
        aligned[:, :shift] = frame[:, -shift:]
    return aligned


def build():
    catalog = json.loads((HERE / 'all-catalog.json').read_text())
    coverage, packed, errors = [], [], []
    for job in catalog:
        destination = Path(job['folder'])
        available = {c: Path(job['categories'][c]['path']).exists() for c in ('arms', 'legs')}
        status = dict(id=job['id'], race=job['race'], appearance=job['appearance'], sex='female',
                      sourceStatus=job['sourceStatus'], nativeSheets=available, status='pending', flags=[])
        if job['sourceStatus'] == 'ready' and all(available.values()):
            try:
                height = job['targetHeight']
                arms = normalize(Path(job['categories']['arms']['path']), 'arms', height)
                legs = normalize(Path(job['categories']['legs']['path']), 'legs', height)
                normal = Image.open(destination / 'normal64.png').convert('RGBA')
                originals = [np.asarray(normal.crop((v*64, 0, v*64+64, 64))) for v in range(4)]
                flags = []
                reviewed = apply_overrides(arms, 'arms', destination, height, (2,)) | apply_overrides(legs, 'legs', destination, height, (2,))
                order_singles(arms, 'arms', height, flags)
                order_singles(legs, 'legs', height, flags)
                reviewed |= apply_overrides(arms, 'arms', destination, height, (0,1)) | apply_overrides(legs, 'legs', destination, height, (0,1))
                combined_metadata = destination / 'combined-6rows-v1.json'
                if combined_metadata.exists() and json.loads(combined_metadata.read_text()).get('noArmsBackReview') != 'accepted':
                    flags.append(dict(category='arms', view='North', issue='both-arm absence requires visual review', badRows=[2]))
                remaining_flags = []
                for flag in flags:
                    flag['badRows'] = [row for row in flag.get('badRows', (0,1)) if (flag['category'], row, flag['view']) not in reviewed]
                    if flag['badRows']:
                        remaining_flags.append(flag)
                flags = remaining_flags
                arms[0][2], arms[1][3] = originals[2].copy(), originals[3].copy()
                arms[0][3], arms[1][2] = arms[2][3].copy(), arms[2][2].copy()
                rows, removed = [], 0
                for row in [originals] + arms + legs:
                    views = []
                    for view, frame in enumerate(row):
                        frame = align_head(frame, originals[view], height)
                        result, count = clean(frame)
                        removed += count
                        keep = result[..., 3] > 0
                        assert np.array_equal(result[keep, :3], frame[keep, :3])
                        assert not result[~keep].any()
                        views.append(Image.fromarray(result))
                    rows.append(views)
                png, dmi = destination / 'injuries64-v1.png', destination / 'injuries64-v1.dmi'
                packing.sheet(rows, png)
                packing.dmi({state: [row] for state, row in zip(STATES, rows)}, [0], [200], False, dmi)
                status.update(status='standing injury draft', image=str(png), dmi=str(dmi), flags=flags,
                              frameSize=[64,64], footBaseline=62, headAlignedToNormal=True, directions=packing.DIRECTIONS,
                              rowLabels=STATES, sourceRGBPreserved=True, isolatedPixelsRemoved=removed,
                              walkingInjuries='not generated', provenance='direct built-in AI edits of this female identity; whole-frame ordering, complete-pose head anchoring and nearest-neighbor packing only')
                (destination / 'injuries64-v1.json').write_text(json.dumps(status, indent=2) + '\n')
                packed.append(status)
            except (ValueError, OSError, AssertionError) as error:
                status.update(status='packing error', error=str(error))
                errors.append(status)
        coverage.append(status)
    (HERE / 'all-coverage.json').write_text(json.dumps(coverage, indent=2) + '\n')
    (HERE / 'all-packed.json').write_text(json.dumps(packed, indent=2) + '\n')
    # Self-contained review: no fetch dependency when opened as a local file.
    items = []
    for record in coverage:
        item = dict(record)
        if record.get('image'):
            item['pngData'] = 'data:image/png;base64,' + base64.b64encode(Path(record['image']).read_bytes()).decode()
        items.append(item)
    data = json.dumps(items).replace('<', '\\u003c')
    template = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>All Female Limb Sheets</title><style>body{margin:24px;background:#20222a;color:#eee;font:16px system-ui}h1{font-size:24px}p{color:#bfc6d6;max-width:85ch}select{font:inherit;padding:8px;max-width:95vw}img{image-rendering:pixelated;display:block;width:512px;max-width:95vw;background:conic-gradient(#333 25%,#292c33 0 50%,#333 0 75%,#292c33 0);background-size:20px 20px}a{color:#9cd3ff}#issues{white-space:pre-wrap;font-size:13px}</style><h1>All Female Limb Sheets</h1><p><a href="GOA%20Female%20Races%20and%20Hybrids.html">Female walks</a> · <a href="GOA%20Female%20Sprite%20Drafts.zip">Download PNG/DMI</a></p><p id="coverage"></p><p>Rows: Normal, missing left arm, missing right arm, both arms missing, missing left leg, missing right leg, both legs missing. Columns: front, back, right-facing, left-facing. 64×64 standing frames. Injury walking frames remain unfinished.</p><select id="pick" aria-label="Female appearance"></select><h2 id="title"></h2><p id="state"></p><img id="sheet" alt="Selected female injury sheet"><p id="issues"></p><script>const items=__DATA__;const pick=document.getElementById('pick'),sheet=document.getElementById('sheet');items.forEach((x,i)=>{const o=document.createElement('option');o.value=i;o.textContent=x.race+' · '+x.appearance+' — '+x.status;pick.append(o)});const ready=items.filter(x=>x.pngData).length;document.getElementById('coverage').textContent=ready+' / '+items.length+' female appearances have packed injury drafts. All remaining forms are listed below.';function show(){const x=items[Number(pick.value)];document.getElementById('title').textContent=x.race+' · Female · '+x.appearance;document.getElementById('state').textContent=x.status;sheet.hidden=!x.pngData;if(x.pngData)sheet.src=x.pngData;document.getElementById('issues').textContent=x.error||((x.flags||[]).length?'Left/right pose review pending: '+JSON.stringify(x.flags):'')}pick.onchange=show;show();</script></html>'''
    preview = HERE.parents[3] / 'Dungeon Master Sample/All Female Limb Sheets.html'
    preview.write_text(template.replace('__DATA__', data))
    print(json.dumps({'femaleAppearances':len(catalog), 'nativeSheets':sum(sum(x['nativeSheets'].values()) for x in coverage),
                      'packed':len(packed), 'remaining':len(catalog)-len(packed), 'packingErrors':errors,
                      'flaggedAppearances':sum(bool(x['flags']) for x in packed), 'preview':str(preview)}))


if __name__ == '__main__':
    build()
