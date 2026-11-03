"""Build the portable, offline sprite conversion workbench (no AI API)."""
from pathlib import Path
import base64
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def data_url(path):
    return 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()


def main():
    assets = {
        'reference': data_url(HERE.parent / 'goa-races-lotr-v1.png'),
        'example': data_url(ROOT / 'standalone/remastered/game/Icons/Remastered/Races64/Human.dmi'),
    }
    html = (HERE / 'workshop.template.html').read_text()
    for marker, value in {
        '/*ASSETS*/null': json.dumps(assets, separators=(',', ':')),
        '/*ENGINE*/': (HERE / 'sprite-engine.js').read_text(),
        '/*APP*/': (HERE / 'workshop.js').read_text(),
    }.items():
        html = html.replace(marker, value)
    (HERE / 'index.html').write_text(html)
    (ROOT / 'Dungeon Master Sample/GOA Sprite Converter.html').write_text(html)
    print('Built GOA Sprite Converter.html and sprite-engine/index.html')


if __name__ == '__main__':
    main()
