#!/usr/bin/env python3
"""Refresh a compact, source-preserving rig inventory and browser review index.

No sprites or rigs are changed. Silhouette equality is a screening result, never
proof that joints, layer order, hidden anatomy or equipment fit are compatible.
"""
import hashlib
import html
import json
import os
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / 'Dungeon Master Sample'
SPRITES = SAMPLE / 'Sprites'
OUT = SAMPLE / 'GOA Race Rig Inventory'
STAGED = ROOT / 'standalone/remastered/reports/goa-sprite-test/staged/rig'
BASELINES = {
    'Male/Elf': ('GOA Reusable Animation Rig v1', 'elf-male.json',
                 'approved_baseline', 'README.md'),
    'Male/Human': ('GOA Retarget Review - Human Male', 'character.json',
                   'approved_baseline', 'README-CLAUDE.md'),
    'Male/Orc': ('GOA Retarget Review - Orc Male', 'character.json',
                 'needs_visual_review', 'README-CLAUDE.md'),
}


def relative(path):
    return str(path.relative_to(ROOT))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def baseline(key):
    if key not in BASELINES:
        return None
    folder, filename, status, evidence = BASELINES[key]
    package = SAMPLE / folder
    profile_path = package / 'profiles' / filename
    profile = json.loads(profile_path.read_text())
    refs = set()
    for view in profile['views']:
        refs.update(view['parts'].values())
        for row in view['walk']:
            refs.update(row.values())
    files = [profile_path, package / 'source/engine.js', package / evidence]
    files += [package / 'preview/assets' / ref for ref in sorted(refs)]
    missing = [relative(p) for p in files if not p.is_file()]
    return dict(package=relative(package), status=status,
                statusEvidence=relative(package / evidence),
                approvalScope='Saved visual baseline; not approval of every clip or live integration.',
                profile=relative(profile_path),
                viewOrder=[v['name'] for v in profile['views']],
                partCounts=[len(v['parts']) for v in profile['views']],
                missingFiles=missing,
                hashes={relative(p): digest(p) for p in files if p.is_file()})


def compare(path, parent):
    if not parent or path == parent:
        return None
    with Image.open(path) as image, Image.open(parent) as base:
        a, b = image.convert('RGBA'), base.convert('RGBA')
        if a.size != b.size:
            return dict(status='different_sheet_layout', parent=relative(parent))
        # Include every view and walk frame; ignore invisible RGB noise.
        am = a.getchannel('A').point(lambda p: 255 if p >= 128 else 0)
        bm = b.getchannel('A').point(lambda p: 255 if p >= 128 else 0)
        changes = ImageChops.difference(am, bm).histogram()[255]
        return dict(status='matching_silhouette_needs_joint_review' if changes == 0
                    else 'silhouette_differs_needs_anatomy_review',
                    parent=relative(parent), differingVisiblePixels=changes,
                    approvedInheritance=False)


def url(path):
    return quote(os.path.relpath(ROOT / path, OUT), safe='/')


def main():
    OUT.mkdir(exist_ok=True)
    families = []
    for sex in ('Male', 'Female'):
        for folder in sorted((SPRITES / sex).iterdir()):
            if not folder.is_dir():
                continue
            sheets = sorted(folder.glob('*/sprites.png'))
            if not sheets:
                continue
            parent = folder / 'base/sprites.png'
            parent = parent if parent.is_file() else None
            key = f'{sex}/{folder.name}'
            variants = []
            for path in sheets:
                with Image.open(path) as im:
                    size = list(im.size)
                variants.append(dict(id=f'{key}/{path.parent.name}',
                                     appearance=path.parent.name, source=relative(path),
                                     sha256=digest(path), size=size,
                                     comparison=compare(path, parent)))
            inputs = [STAGED / (folder.name + '.json'),
                      STAGED / 'finezones' / folder.name / 'fine.png',
                      STAGED / 'finezones' / folder.name / 'fine.json'] if sex == 'Male' else []
            families.append(dict(id=key, sex=sex, race=folder.name,
                                 baseSource=relative(parent) if parent else None,
                                 rig=baseline(key),
                                 candidateInputs=[relative(p) for p in inputs if p.is_file()],
                                 inputRegistrationVerified=False,
                                 appearances=variants))
    summary = dict(families=len(families),
                   appearances=sum(len(f['appearances']) for f in families),
                   approvedBaselines=sum(bool(f['rig'] and f['rig']['status']=='approved_baseline') for f in families),
                   existingReviewRigs=sum(bool(f['rig'] and f['rig']['status']=='needs_visual_review') for f in families),
                   verifiedHybridInheritance=0)
    report = dict(schemaVersion=1, summary=summary, families=families,
                  rules=['Preserve original body pixels and calibrated Human/Elf renderers.',
                         'Reuse animation clips; calibrate each distinct anatomy separately.',
                         'Same silhouette does not prove rig compatibility; different silhouette may only be hair or horns.',
                         'Never run the legacy filler-producing cutter blindly over this inventory.',
                         'Female profiles require their own calibration; do not assume male joints.',
                         'Record hybrid inheritance only after body-part and joint review.'])
    (OUT / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    cards = []
    for family in families:
        rig = family['rig']
        status = rig['status'].replace('_', ' ') if rig else 'body preparation needed'
        link = (f'<a href="{url(rig["package"] + "/preview/index.html")}">Open existing animation rig</a>'
                if rig else '')
        images = []
        for appearance in family['appearances']:
            comparison = appearance['comparison']
            detail = comparison['status'].replace('_', ' ') if comparison else 'source body'
            images.append(f'<figure><a href="{url(appearance["source"])}"><img loading="lazy" '
                          f'src="{url(appearance["source"])}" alt="{html.escape(appearance["id"])}"></a>'
                          f'<figcaption>{html.escape(appearance["appearance"])}<small>{detail}</small></figcaption></figure>')
        cards.append(f'<section><h2>{html.escape(family["id"])} · {status}</h2>{link}'
                     f'<details><summary>{len(images)} source appearances</summary><div class="sheets">'
                     + ''.join(images) + '</div></details></section>')
    (OUT / 'index.html').write_text('''<!doctype html><meta charset="utf-8">
<title>GOA race rig inventory</title><style>
body{background:#181c24;color:#e5e9ef;font:16px system-ui;margin:32px;max-width:1500px}
a{color:#a2ceff}section{border-top:1px solid #455164;padding:16px 0}
h2{font-size:19px}summary{cursor:pointer;margin-top:14px}.sheets{display:flex;flex-wrap:wrap;gap:12px}
figure{margin:12px 0;background:#303948;padding:12px}img{width:256px;image-rendering:pixelated}
small{display:block;max-width:256px;color:#bdc6d4}p{max-width:900px;line-height:1.5}
</style><h1>GOA race rig inventory</h1>
<p>Male Elf and Human have saved approved baselines. Orc has an existing review rig.
Open each rig to review movement. Expand a family to compare the original sheets.</p>
<p>Hybrid inheritance is pending anatomy review. Silhouette checks alone cannot establish joint,
layer or equipment compatibility. These sheets are preserved source art.</p>
<p><a href="inventory.json">Machine-readable inventory and baseline hashes</a></p>
''' + ''.join(cards))
    (OUT / 'README.md').write_text('''# Reusable race animation work

Run `python3 standalone/goa-races/character-retarget/inventory.py` from the repository root.
Open `index.html` to compare the source appearances and open existing animation rigs.
The command reads source art and writes only this inventory folder. It does not generate art.

## Established baselines

- Male Elf: GOA Reusable Animation Rig v1.
- Male Human: GOA Retarget Review - Human Male. README-CLAUDE.md records user approval;
  its older fit-report.json predates that approval. Preserve this package's renderer and local repairs.
- Male Orc: GOA Retarget Review - Orc Male. Existing cutouts and renderer, still awaiting visual review.
- These approval records do not claim all clips, exports, female bodies or hybrids are complete.

## Next work

1. Review the existing Orc beside Human and Elf before rebuilding any Orc assets.
2. Prepare female Elf and small Goblin profiles to validate the shared format across different proportions.
3. Extract remaining bodies from their own original sheets and registered zones. Available staged male
   inputs are recorded as candidates, not validated registrations. Never borrow another race's joint rows.
4. Compare each hybrid's body parts and joints with its own parent. Keep its actual artwork. Save a parent
   link plus only the necessary profile/attachment overrides when compatibility is established.
5. Batch export reviewed profiles; rerun only entries whose input/profile/renderer hashes changed.

The existing generic zone cutter adds synthetic fillers. Adapt source-preserving extraction before
bulk builds. Hidden surfaces may come from another frame of the same facing; report unavailable surfaces.
Do not automatically rerun the Orc builder: its documented behavior replaces its existing review folder.

## Keeping chat context small

Read this file and the inventory summary first. Open only the active character's profile and review notes.
The inventory saves source hashes, baseline asset/renderer hashes, and candidate inputs. It does not yet
implement incremental animation builds or certify inheritance. Silhouette differences include heads,
hair and markings; they do not automatically require another skeleton.
''')
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
