"""Review sheets use the same whole-character display scale as the viewer."""
from pathlib import Path
from PIL import Image,ImageDraw
import math
ORDER=['base','possessed1','possessed2','marked','ashen','hellblooded','werewolf','zombie']


def sheet(root,actors,path,columns=4):
    rows=math.ceil(len(actors)/columns)
    canvas=Image.new('RGB',(columns*256,rows*280),(21,28,35));draw=ImageDraw.Draw(canvas)
    for i,a in enumerate(actors):
        x=(i%columns)*256;y=(i//columns)*280
        draw.rounded_rectangle((x+5,y+5,x+250,y+273),radius=10,fill=(28,39,48),outline=(53,70,80))
        image=Image.open(root/a['composite']).crop((0,0,128,128))
        scale=3*a['displayScale'];size=round(128*scale)
        image=image.resize((size,size),Image.Resampling.NEAREST)
        canvas.paste(image,(round(x+128-64*scale),round(y+235-93*scale)),image)
        label=a['label'].replace(' · Female',' · F').replace(' · Male',' · M')
        draw.text((x+13,y+16),label[:38],fill=(235,242,248))
        draw.text((x+13,y+251),a['build']+' body',fill=(151,194,179))
    canvas.save(path)


def build(root,actors):
    by={a['id']:a for a in actors}
    directory=root/'Hybrid Previews';directory.mkdir(exist_ok=True)
    sheets=[]
    for race in sorted({a['race'] for a in actors}):
        chosen=[a for a in actors if a['race']==race and '-flying' not in a['id'] and a['appearance'].lower() in ORDER]
        if not any(a['appearance'].lower()!='base' for a in chosen):continue
        chosen.sort(key=lambda a:(a['sex']=='female',ORDER.index(a['appearance'].lower())))
        filename=race.replace('-','_')+'_Hybrids_Male_and_Female.png'
        sheet(root,chosen,directory/filename)
        sheets.append(dict(race=race,file='Hybrid Previews/'+filename,appearances=len(chosen)))
    gargoyles=[a for a in actors if a['race']=='gargoyle']
    sheet(root,gargoyles,directory/'Gargoyle_Eye_and_Wing_Variants.png')
    sheets.append(dict(race='gargoyle',file='Hybrid Previews/Gargoyle_Eye_and_Wing_Variants.png',appearances=len(gargoyles)))
    ids=['human-marked','human-female-marked','orc-marked','orc-female-marked',
        'human-ashen','human-female-ashen','elf-ashen','elf-female-ashen',
        'human-hellblooded','human-female-hellblooded','dwarf-hellblooded','dwarf-female-hellblooded',
        'dark-elf-werewolf','dark-elf-female-werewolf','kobold-werewolf','kobold-female-werewolf',
        'goblin-possessed2','goblin-female-possessed2','lizardman-zombie','lizardman-female-zombie']
    sheet(root,[by[id] for id in ids],root/'Polished_Hybrids_Overview.png')
    ids=['human','human-female','elf','elf-female','orc','orc-female','dwarf','dwarf-female',
        'dark-elf','dark-elf-female','goblin','goblin-female','kobold','kobold-female','frogman','frogman-female']
    sheet(root,[by[id] for id in ids],root/'Original_Heads_on_Shared_Bodies.png')
    return sheets

