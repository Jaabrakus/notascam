"""Package native imagegen base-body poses as aligned 64px game sprites."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
from PIL import Image
import html

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEST = ROOT / 'Dungeon Master Sample/Base Body Holding Poses'
DIRECTIONS = ['South', 'North', 'East', 'West']
spec = importlib.util.spec_from_file_location('worn_build', HERE.parent / 'armor-designs/worn-masters-v1/build.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    sources = HERE / 'artwork'
    sources.mkdir(exist_ok=True)
    records = []
    preview = Image.new('RGBA', (1024, 768))
    for row, item in enumerate(json.loads((HERE / 'inputs.json').read_text())):
        name = item['name']
        folder = DEST / name
        folder.mkdir(exist_ok=True)
        canonical = sources / (name + '_Artwork.png')
        if not canonical.exists():
            shutil.copyfile(item['source'], canonical)
        artwork = folder / canonical.name
        shutil.copyfile(canonical, artwork)
        (folder / 'Generation_Prompt.md').write_text(item['prompt'])
        im = Image.open(canonical).convert('RGBA')
        cuts = helper.columns(im)
        alpha = im.getchannel('A').point(lambda a: 255 if a >= 128 else 0)
        figures = []
        for i in range(4):
            a, b = cuts[i:i+2]
            bounds = alpha.crop((a, 0, b, im.height)).getbbox()
            assert bounds
            box = (a + bounds[0], bounds[1], a + bounds[2], bounds[3])
            bottom = box[3]
            foot = alpha.crop((box[0], round(bottom - (bottom - box[1]) * .14), box[2], bottom)).getbbox()
            center = box[0] + (foot[0] + foot[2]) / 2
            figures.append((box, center, bottom))
        span = max(max(cx-box[0], box[2]-cx) for box,cx,_ in figures)
        scale = min(56 / max(box[3]-box[1] for box,_,_ in figures), 29 / span)
        atlas = Image.new('RGBA', (256, 64))
        frames = []
        for i, (box, cx, bottom) in enumerate(figures):
            isolated = Image.new('RGBA', im.size)
            isolated.paste(im.crop((cuts[i], 0, cuts[i+1], im.height)), (cuts[i], 0))
            tile = isolated.transform((64, 64), Image.Transform.AFFINE,
                (1/scale, 0, cx-32/scale, 0, 1/scale, bottom-61/scale),
                resample=Image.Resampling.NEAREST)
            bb = tile.getchannel('A').point(lambda a: 255 if a>=128 else 0).getbbox()
            assert bb and bb[0]>0 and bb[1]>0 and bb[2]<64 and bb[3]<64, (name, i, bb)
            filename = name + '_' + DIRECTIONS[i] + '_64px.png'
            tile.save(folder / filename)
            assert Image.open(folder / filename).tobytes() == tile.tobytes()
            atlas.paste(tile, (64*i, 0))
            frames.append(dict(direction=DIRECTIONS[i], file=filename, rect=[64*i, 0, 64, 64], feet=[32,61], sourceBounds=box))
        sheet = name + '_Sheet_64px.png'
        atlas.save(folder / sheet)
        large = atlas.resize((1024,256), Image.Resampling.NEAREST)
        large.save(folder / (name + '_Preview_4x.png'))
        preview.alpha_composite(large, (0,256*row))
        record = dict(name=name, artwork=artwork.name, sheet=sheet, frameSize=[64,64],
            directionOrder=DIRECTIONS, frames=frames, equipmentVisible=False,
            armorVisible=False, generation='built-in imagegen',
            limits='Four standing empty-hand holding poses. No walking, attacks, equipment layers or sixteen-direction animation included.',
            sourceSha256=hashlib.sha256(canonical.read_bytes()).hexdigest())
        (folder / 'manifest.json').write_text(json.dumps(record, indent=2))
        records.append(record)
    preview.save(DEST / 'Holding_Poses_Preview_4x.png')
    (DEST / 'index.json').write_text(json.dumps(dict(sets=records), indent=2))
    (DEST / 'README.md').write_text('# Base Body Holding Poses\n\nThree human base-body pose sets, drawn using built-in imagegen. Characters wear only charcoal shorts. Weapons, shields and worn armor are absent; hands retain the intended equipment-holding stances.\n\nEach folder includes original artwork, a 256×64 sheet, four individual 64×64 transparent frames, a 4× nearest-neighbor preview, generation prompt and manifest. Direction order: South, North, East, West. Feet are registered at (32,61).\n\nThese are standing pose drafts. Walking, attacks, equipment attachment layers and sixteen directions are not included.\n')
    cards = []
    for item in records:
        name = item['name']
        label = html.escape(name.replace('_', ' '))
        cards.append('<article><h2>' + label + '</h2><img src="' + name + '/' + name + '_Preview_4x.png" alt="' + label + '"><p><a href="' + name + '/' + item['sheet'] + '">64px sheet</a> · <a href="' + name + '/' + item['artwork'] + '">Original artwork</a></p></article>')
    (DEST / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Base Body Holding Poses</title><style>body{background:#181818;color:#eee;font:16px system-ui;margin:32px}article{margin:32px 0;border:1px solid #444;padding:16px}img{width:100%;max-width:1024px;image-rendering:pixelated}a{color:#9bd4ff}h2{font-size:20px}</style><h1>Base Body Holding Poses</h1><p>No armor, weapons or shields. Four standing directions per set; empty grips are ready for equipment fitting.</p>' + ''.join(cards))
    print(json.dumps(dict(folder=str(DEST), sets=len(records), frames=12, frameSize=64)))


if __name__ == '__main__':
    main()

