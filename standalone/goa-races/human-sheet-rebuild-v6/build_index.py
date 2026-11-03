from pathlib import Path
from PIL import Image
import base64,json,html
ART=Path(__file__).resolve().parents[1];ROOT=ART.parents[1];OUT=ROOT/'Dungeon Master Sample/Human Sprites';cards=[]
manifest=json.loads((OUT/'manifest.json').read_text())
for r in manifest['records']:
 name=f"{r['race']}-Male-{r['appearance']}-64";p=OUT/(name+'.png');src='data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()
 cards.append('<section><h2>'+html.escape(r['race']+' / '+r['appearance'])+'</h2><p>South · North · East · West — idle, walk A, walk B</p><img src="'+src+'" alt="'+html.escape(name)+' rebuilt sprite sheet"><p><a href="'+name+'.png">PNG</a> · <a href="'+name+'.dmi">DMI</a> · <a href="'+name+'.json">Metadata</a></p></section>')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Rebuilt Human sprite sheets</title><style>body{margin:0;padding:24px;background:#14232a;color:#eef4f5;font:16px system-ui}main{max-width:1000px;margin:auto}h1{font-size:26px}h2{font-size:20px}p{color:#bfd1d7;line-height:1.5}a{color:#8de1d0}section{background:#20343b;padding:18px;margin:25px 0;border-radius:8px}img{display:block;width:min(100%,768px);height:auto;image-rendering:pixelated;background:repeating-conic-gradient(#20343b 0 25%,#293e46 0 50%) 0/16px 16px}</style><main><h1>Rebuilt Human sprite sheets</h1><p>All 16 male Human appearances rebuilt with complete saved redraw frames. PNGs use 64 × 64 cells; the four-phase movement loop is 0, 1, 0, 2 at 200ms.</p><p><a href="../GOA%20Male%20Human%20Sprites.zip">Download all Human sheets</a> · <a href="../All%20Sprites.html">All sprite sets</a></p>'''+''.join(cards)+'</main></html>'
(OUT/'index.html').write_text(page)
print('Built the 16-sheet Human preview from rebuilt PNG bytes.')
