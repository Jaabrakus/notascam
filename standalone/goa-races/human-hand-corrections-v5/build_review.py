from pathlib import Path
from PIL import Image,ImageDraw
from io import BytesIO
import base64,json,html
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def data(im):
 b=BytesIO();im.save(b,format='PNG');return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
entries=json.loads((HERE.with_name('human-hand-corrections-v4')/'manifest.json').read_text());cards=[]
for e in entries:
 f=Path(e['folder']);old=Image.open(f/'before.png').convert('RGBA');new=Image.open(HERE.parent/'hybrids/packed'/e['race']/e['appearance']/'sprites.png').convert('RGBA')
 cards.append('<section><h2>'+html.escape(e['race']+' · '+e['appearance'])+'</h2><div class="pair"><figure><figcaption>Original idle · East / West</figcaption><img alt="Original side views" src="'+data(old.crop((128,0,256,64)))+'"></figure><figure><figcaption>Redrawn arms · East / West</figcaption><img alt="Redrawn side idle arms" src="'+data(new.crop((128,0,256,64)))+'"></figure></div></section>')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Male Human idle arm redraws</title><style>body{margin:0;padding:24px;background:#14232a;color:#eaf1f3;font:16px system-ui}main{max-width:1000px;margin:auto}h1{font-size:26px}h2{font-size:18px}p,figcaption{color:#b5cbd1;line-height:1.5}section{padding:16px;margin:20px 0;background:#20343b;border-radius:9px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}img{display:block;width:100%;image-rendering:pixelated;background:repeating-conic-gradient(#20343b 0 25%,#243a42 0 50%) 0/16px 16px}figcaption{padding-bottom:8px}@media(max-width:600px){.pair{grid-template-columns:1fr}}</style><main><h1>Male Human idle arm redraws</h1><p>Updated male Human side views. Normal and red-eyed Possessed1 Humans now have shorter rounded noses and revised idle arms; all 16 appearances are shown for comparison.</p>'''+''.join(cards)+'</main></html>'
(HERE/'index.html').write_text(page);(ROOT/'Dungeon Master Sample/GOA Male Human Idle Hand Redraws.html').write_text(page)
# Focused review image: both side views, old and redrawn, for the base and red-eyed Humans.
proof=Image.new('RGBA',(1024,576),(20,32,38,255));draw=ImageDraw.Draw(proof)
for row,(race,kind) in enumerate([('Human','base'),('Human','Possessed1'),('HumanBlack','base')]):
 f=HERE/race/kind
 for col,name in enumerate(['before.png','candidate.png']):
  im=Image.open(f/name if col==0 else HERE.parent/'hybrids/packed'/race/kind/'sprites.png').crop((128,0,256,64)).resize((384,192),Image.Resampling.NEAREST);proof.alpha_composite(im,(col*512+64,row*192));draw.text((col*512+4,row*192+4),race+' / '+kind+(' · previous' if col==0 else ' · corrected'),fill='white')
proof.save(HERE/'comparison.png');print('Built review for 16 independently redrawn male Human variants.')
