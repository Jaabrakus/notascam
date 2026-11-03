"""Lossless frame extraction and read-only inventory of existing injury art.

No game sprites are modified; contact-sheet labels live outside source cells.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import json, re, collections

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
ICONS=ROOT/'standalone/remastered/game/Icons'
RACES=['Demon','DevourerZombie','Dwarves','FrogMan','Gargoyle','Goblins','Human','HumanBlack','Kobold','LizardMan','Night Elf','Orc','Skeleton','Vampire']
SLOTS=['LeftArm','RightArm','LeftLeg','RightLeg']
INJURY=['NoLeftArm','NoRightArm','NoArms','NoLeftLeg','NoRightLeg','NoLegs','None']

def read(path):
 im=Image.open(path);d=im.info.get('Description','');states=[];offset=0
 def n(block,key,default):
  m=re.search(r'^\s*'+key+r'\s*=\s*(\d+)',block,re.M);return int(m[1]) if m else default
 w,h=n(d,'width',32),n(d,'height',32)
 for block in re.split(r'(?=^state\s*=)',d,flags=re.M)[1:]:
  name=re.search(r'^state\s*=\s*"(.*?)"',block,re.M)[1];dirs,frames=n(block,'dirs',1),n(block,'frames',1)
  state=dict(name=name,dirs=dirs,frames=frames,offset=offset,movement=n(block,'movement',0));states.append(state);offset+=dirs*frames
 return dict(path=str(path),image=im.convert('RGBA'),width=w,height=h,columns=im.width//w,states=states,cells=offset)

def frame(data,state,direction=0,f=0):
 if isinstance(state,str):state=next(s for s in data['states'] if s['name']==state)
 i=state['offset']+(f%state['frames'])*state['dirs']+direction%state['dirs'];x=i%data['columns']*data['width'];y=i//data['columns']*data['height']
 return data['image'].crop((x,y,x+data['width'],y+data['height']))

def labels(sheet,rowlabels,title):
 zoom=3;out=Image.new('RGBA',(220+sheet.width*zoom,50+sheet.height*zoom),(26,33,36,255));draw=ImageDraw.Draw(out)
 draw.text((12,12),title,fill='white');out.alpha_composite(sheet.resize((sheet.width*zoom,sheet.height*zoom),Image.Resampling.NEAREST),(220,50))
 for row,label in enumerate(rowlabels):draw.text((12,50+row*64*zoom+85),label,fill='white')
 return out

inventory=[]
for race in RACES:
 body=read(ICONS/'Remastered/Races64'/f'{race}.dmi')
 limbs=read(ICONS/'Remastered/Limbs64'/f'{race}.dmi')
 normal=next(s for s in body['states'] if s['name'] in ('','Normal') and s['dirs']==4)
 sheet=Image.new('RGBA',(256,512))
 for row,state in enumerate([normal]+INJURY):
  for d in range(4):sheet.paste(frame(body,state,d),(64*d,64*row))
 sheet.save(HERE/f'{race}-injury-source.png')
 sheet.crop((0,64,256,256)).save(HERE/f'{race}-arms-source.png')
 sheet.crop((0,256,256,512)).save(HERE/f'{race}-legs-source.png')
 if race in ['Human','Gargoyle','Skeleton','Vampire']:
  labels(sheet,['Normal']+INJURY,f'{race}: original source injury states. Columns S / N / E / W.').save(HERE/f'{race}-injury-labeled.png')
 graft=Image.new('RGBA',(256,256))
 for row,slot in enumerate(SLOTS):
  for d in range(4):graft.paste(frame(limbs,f'{slot}@{race}',d),(64*d,64*row))
 graft.save(HERE/f'{race}-self-graft-source.png')
 if race=='Human':labels(graft,SLOTS,'Human: original graft overlays (not loose ground items).').save(HERE/'Human-self-graft-labeled.png')
 inventory.append(dict(race=race,injuryStates=body['states'],limbStates=limbs['states'],limbCells=limbs['cells']))

blood=read(ICONS/'Blood.dmi');stone=read(ICONS/'Remastered/Items/stonelimb.dmi')
blist=[('Arm',0),('1',0),('2',0),('3',0),('4',0),('Dead',0),('Propelled',0),('Propelled',1),('Burst',0),('Burst',4),('Burst',8),('Burst',13)]
bsheet=Image.new('RGBA',(32*4,32*4))
for i,(name,f) in enumerate(blist):bsheet.paste(frame(blood,name,f=f),(32*(i%4),32*(i//4)))
bsheet.paste(frame(stone,'Arm'),(0,32*3));bsheet.save(HERE/'blood-and-stone-source.png')
large=Image.new('RGBA',(4*192,4*220),(26,33,36,255));draw=ImageDraw.Draw(large)
for i,(name,f) in enumerate(blist+[('Stone Arm',0)]):
 cell=frame(stone,'Arm') if name=='Stone Arm' else frame(blood,name,f=f)
 x,y=(i%4)*192,(i//4)*220;large.alpha_composite(cell.resize((192,192),Image.Resampling.NEAREST),(x,y));draw.text((x+6,y+194),f'{name}, frame {f}',fill='white')
large.save(HERE/'blood-and-stone-labeled.png')

palettes={}
for p in [ICONS/'Blood.dmi',ICONS/'Remastered/Races64/Human.dmi',ICONS/'Human.dmi']:
 data=read(p); selected=frame(data,'Arm') if p.name=='Blood.dmi' else frame(data,'NoLeftArm')
 counts=collections.Counter(tuple(px[:3]) for px in selected.getdata() if px[3]>0 and px[0]>90 and px[1]<75 and px[2]<75 and px[0]>px[1]*1.6 and px[0]>px[2]*1.6)
 palettes[str(p.relative_to(ICONS))]=[dict(rgb=list(c),hex='#%02x%02x%02x'%c,count=count) for c,count in counts.most_common(32)]
(HERE/'source-inventory.json').write_text(json.dumps(dict(races=inventory,totalWearerSheets=len(inventory),totalOverlayStates=sum(len(i['limbStates']) for i in inventory),totalOverlayCells=sum(i['limbCells'] for i in inventory),bloodStates=blood['states'],bloodPalettes=palettes),indent=2))
print(json.dumps(dict(races=len(inventory),overlayStates=sum(len(i['limbStates']) for i in inventory),overlayCells=sum(i['limbCells'] for i in inventory),bloodPalettes=palettes)))
