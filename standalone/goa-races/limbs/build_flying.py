"""Build a self-contained Human source-pixel limb fly-off prototype."""
from pathlib import Path
from collections import Counter
import base64,json
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def src(path):return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()

def main():
    normal=HERE/'pixel-assets/human/normal.png';parts=HERE/'pixel-assets/human/parts.png'
    blood=ROOT/'standalone/remastered/game/Icons/Blood.dmi'
    colors=Counter((r,g,b) for r,g,b,a in Image.open(blood).convert('RGBA').getdata() if a and r>=65 and r>g*1.8 and r>b*1.6)
    palette=[list(rgb) for rgb,_count in colors.most_common(5)]
    if not palette:raise ValueError('No source red blood palette found.')
    donors={name:dict(parts=src(HERE/'pixel-assets'/name.lower()/'parts.png'),sourceFrames=3,material='source skin pixels',source=str(HERE/'pixel-assets'/name.lower()/'parts.png')) for name in ['Human','Orc'] if (HERE/'pixel-assets'/name.lower()/'parts.png').exists()}
    data=dict(normal=src(normal),parts=src(parts),donors=donors,sourceFrames=3,bloodPalette=palette,metadata=json.loads((HERE/'pixel-assets/human/metadata.json').read_text()),
              provenance=dict(body=str(normal),parts=str(parts),bloodPaletteSource=str(blood)))
    html=(HERE/'flying-pieces.template.html').read_text().replace('/*DATA*/null',json.dumps(data,separators=(',',':'))).replace('/*APP*/',(HERE/'flying-pieces.js').read_text())
    (HERE/'flying-pieces.html').write_text(html)
    (ROOT/'Dungeon Master Sample/Flying Sprite Pieces.html').write_text(html)
    print('Built flying-pieces.html and Dungeon Master Sample/Flying Sprite Pieces.html')

if __name__=='__main__':main()
