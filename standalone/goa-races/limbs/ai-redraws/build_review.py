"""Index native AI redraws without repainting or changing their source pixels."""
import html
import json
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
SAMPLE = HERE.parents[3] / 'Dungeon Master Sample'


def build():
    records = []
    for meta in sorted((HERE / 'raw').glob('*.json')):
        record = json.loads(meta.read_text())
        image_path = Path(record['savedPath'])
        with Image.open(image_path) as image:
            record['imageSize'] = list(image.size)
            record['hasAlpha'] = image.mode == 'RGBA'
            record['alphaRange'] = list(image.getchannel('A').getextrema()) if image.mode == 'RGBA' else None
        record['file'] = 'raw/' + image_path.name
        records.append(record)
    (HERE / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')
    cards = []
    for record in records:
        name = html.escape(record['race'] + ' — ' + record['category'])
        src = '../standalone/goa-races/limbs/ai-redraws/' + record['file']
        cards.append('<article><h2>' + name + '</h2><a href="' + html.escape(src, quote=True) + '"><img loading="lazy" src="' + html.escape(src, quote=True) + '" alt="' + name + '"></a></article>')
    document = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Limb Redraws</title>
<style>body{margin:24px;background:#181a20;color:#eee;font:16px system-ui}h1{font-size:24px}p{max-width:75ch;color:#bbb}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}article{background:#242731;padding:12px;border-radius:8px}h2{font-size:17px}img{display:block;width:100%;height:auto;image-rendering:pixelated;background-color:#444;background-image:conic-gradient(#333 25%,#444 0 50%,#333 0 75%,#444 0);background-size:20px 20px}</style>
<h1>AI Limb Redraws</h1><p>Actual AI-generated source art. These drafts need injury-state, laterality, alignment and animation review before game integration. Click a sheet to open its original image. Existing game assets remain unchanged.</p>
<p>Arms: missing left, missing right, missing both. Legs: missing left, missing right, missing both. Pieces: left arm, right arm, left leg, right leg. Columns: front, back, right-facing, left-facing. These are requested layouts; each draft still requires visual verification.</p><main>'''
    SAMPLE.mkdir(exist_ok=True)
    output = SAMPLE / 'AI Limb Redraws.html'
    output.write_text(document + '\n'.join(cards) + '</main></html>')
    print(json.dumps({'sheets': len(records), 'races': len({r['race'] for r in records}), 'review': str(output)}))


if __name__ == '__main__':
    build()
