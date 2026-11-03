"""Package current idle holding poses into a self-contained review page."""
from pathlib import Path
import json,base64,html
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
manifest=json.loads((HERE/'idle-holds/manifest.json').read_text())
def card(record):
    image=HERE/'idle-holds'/record['image'];src='data:image/png;base64,'+base64.b64encode(image.read_bytes()).decode()
    return '<section><h2>'+html.escape(record['label'])+'</h2><img src="'+src+'" alt="'+html.escape(record['label'])+' idle in four directions"><div class="dirs"><span>South</span><span>North</span><span>East</span><span>West</span></div></section>'
featured=[r for r in manifest if r['id'] in ['spear-jab','sword','axe','hammer','mace','dagger','bow','staff'] and not r['shield']]
extra=[r for r in manifest if r not in featured]
page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Idle weapon holds</title><style>body{margin:0;padding:28px;background:#14232a;color:#edf4f5;font:16px system-ui}main{max-width:1080px;margin:auto}h1{font-size:27px}p{color:#bfd0d5;line-height:1.5}a{color:#8de1d0}section{background:#20343b;padding:16px;margin:22px 0;border-radius:10px}h2{font-size:19px;margin:0 0 12px}img{display:block;width:100%;height:auto;image-rendering:pixelated}.dirs{display:grid;grid-template-columns:repeat(4,1fr);text-align:center;color:#bfd0d5}header{background:#14232a;padding:10px 0}summary{cursor:pointer;font-size:19px;padding:16px 0}</style><main><header><h1>Idle weapon holds</h1><p>Current holding poses with their weapon layers. Each row shows all four directions so we can inspect the grip, stance and visible weapon angle.</p><p><a href="GOA%20Armed%20Walk%20Pose.html">See the reference-inspired sword-and-shield walk on our sprites</a></p><p><a href="GOA%20Human%20Combat%20Sample.html">Open interactive idle viewer — choose weapons, toggle shield or play the slower jab</a></p></header>'''
page+=''.join(card(r) for r in featured)+'<details><summary>More weapons and shield combinations</summary>'+''.join(card(r) for r in extra)+'</details></main></html>'
(ROOT/'Dungeon Master Sample/GOA Idle Weapon Holds.html').write_text(page)
print('Built idle holding gallery:',len(manifest),'loadouts')
