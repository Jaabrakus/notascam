"""Display original GOA wearable frames without redrawing their artwork."""
from pathlib import Path
import base64
from io import BytesIO
import json
import math
import re
from html import escape

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GOA = Path('/Users/kiwimango/Downloads/GOA Source')


def metadata(path):
    im = Image.open(path)
    text = im.info.get('Description', '')
    def number(block, key, default):
        match = re.search(r'^\s*'+key+r'\s*=\s*(\d+)', block, re.M)
        return int(match[1]) if match else default
    width, height = number(text,'width',32), number(text,'height',32)
    states, offset = [], 0
    for block in re.split(r'(?=^state\s*=)', text, flags=re.M)[1:]:
        match = re.search(r'^state\s*=\s*"(.*?)"',block,re.M)
        if not match:
            continue
        dirs, frames = number(block,'dirs',1), number(block,'frames',1)
        states.append(dict(name=match[1],dirs=dirs,frames=frames,offset=offset,movement=number(block,'movement',0)))
        offset += dirs*frames
    return im.convert('RGBA'), width, height, states


def frame(path, view, preferred=None):
    im,w,h,states = metadata(path)
    candidates = [s for s in states if preferred is not None and s['name']==preferred]
    if not candidates:
        candidates = [s for s in states if s['name'] in ('','Normal','normal','default')]
    if not candidates:
        candidates = [s for s in states if s['dirs']==4 and s['name'].lower() not in ('gui','hud','icon')]
    if not candidates:
        return None, None
    state=next((s for s in candidates if not s['movement']),candidates[0])
    index=state['offset']+view%state['dirs'];columns=im.width//w
    return im.crop((index%columns*w,index//columns*h,index%columns*w+w,index//columns*h+h)),state['name']


def data_url(im):
    output=BytesIO();im.save(output,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()


def make_preview(entry):
    views,isolated,used = [],[],[]
    for view in range(4):
        base,_=frame(GOA/'icons/base_m1.dmi',view)
        composed=Image.new('RGBA',(96,96));composed.alpha_composite(base,(32,32))
        layer_canvas=Image.new('RGBA',(96,96))
        for source in entry['sources']:
            path=Path(source);path=path if path.is_absolute() else GOA/path
            layer,state=frame(path,view,entry.get('state'))
            if layer is None:
                continue
            dx,dy=entry.get('offset',[0,0]);position=(32+dx,64-layer.height-dy)
            layer_canvas.alpha_composite(layer,position)
            used.append(dict(source=str(path),state=state))
        composed.alpha_composite(layer_canvas)
        views.append(composed);isolated.append(layer_canvas)
    boxes=[im.getbbox() for im in views];left=min(b[0] for b in boxes)-4;top=min(b[1] for b in boxes)-4;right=max(b[2] for b in boxes)+4;bottom=max(b[3] for b in boxes)+4
    box=(max(0,left),max(0,top),min(96,right),min(96,bottom));size=max(box[2]-box[0],box[3]-box[1]);sheet=Image.new('RGBA',(size*4,size));layers=Image.new('RGBA',(size*4,size))
    for v in range(4):
        x=(size-(box[2]-box[0]))//2;y=(size-(box[3]-box[1]))//2
        sheet.alpha_composite(views[v].crop(box),(v*size+x,y))
        layers.alpha_composite(isolated[v].crop(box),(v*size+x,y))
    available=any(im.getbbox() for im in isolated)
    return sheet,layers,available,used


def main():
    inventory=json.loads((HERE/'inventory.json').read_text())
    entries=sorted(inventory['entries'],key=lambda e:(e['category'],e['label']))
    rendered=[]
    for e in entries:
        sheet,layer,available,used=make_preview(e)
        rendered.append(dict(**e,composite=data_url(sheet),layers=data_url(layer),previewAvailable=available,usedFrames=used))
    manifest=dict(count=len(rendered),entries=rendered)
    template=(HERE/'gallery.template.html').read_text().replace('/*WARDROBE*/null',json.dumps(manifest,separators=(',',':')))
    (HERE/'index.html').write_text(template)
    (ROOT/'Dungeon Master Sample/GOA All Wearables.html').write_text(template)
    # Contact sheet: all source-available wearable/color entries, not selected examples.
    cols,cellw,cellh=12,128,144
    height=70+math.ceil(len(rendered)/cols)*cellh
    overview=Image.new('RGB',(cols*cellw,height),'#172226');draw=ImageDraw.Draw(overview)
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',12)
    title=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',22)
    draw.text((20,14),f"GOA wardrobe — all {len(rendered)} wearable / color entries",font=title,fill='#e5d1a5')
    draw.text((20,43),'Original source sprites on the native GOA body. Open the gallery for all four directions and separate layers.',font=font,fill='#aebfbb')
    for i,e in enumerate(rendered):
        x=i%cols*cellw;y=70+i//cols*cellh
        sheet,_,_,_=make_preview(e);size=sheet.height
        front=sheet.crop((0,0,size,size));scale=min(3,104/size);front=front.resize((round(size*scale),round(size*scale)),Image.Resampling.NEAREST)
        overview.paste(front,(x+(cellw-front.width)//2,y+4),front)
        label=e['label'];lines=[]
        while label and len(lines)<2:
            cut=min(19,len(label));lines.append(label[:cut]);label=label[cut:]
        for row,line in enumerate(lines):draw.text((x+4,y+111+row*14),line,font=font,fill='#d7dfd5')
    overview.save(HERE/'all-wearables.png')
    overview.save(ROOT/'Dungeon Master Sample/GOA All Wearables.png')
    (HERE/'preview-verification.json').write_text(json.dumps(dict(entries=len(rendered),previewAvailable=sum(e['previewAvailable'] for e in rendered),missingStanding=[e['id'] for e in rendered if not e['previewAvailable']],categories=sorted({e['category'] for e in rendered}),sourceArtworkChanges='none; frame extraction, nearest-neighbor enlargement and compositing only'),indent=2))
    print(json.dumps(dict(entries=len(rendered),previewAvailable=sum(e['previewAvailable'] for e in rendered),gallery=str(HERE/'index.html'),overviewSize=list(overview.size))))


if __name__=='__main__':
    main()
