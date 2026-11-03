"""Extract the six fixed masters from original sprite pixels, without redraws."""
from pathlib import Path
from PIL import Image,ImageDraw
import hashlib,json,shutil
from heads import extract,skin_color,light
SOURCES=[
 ('standard-male','elf','Elf_male_User_Approved.png'),
 ('standard-female','elf-female','Elf_female_User_Approved.png'),
 ('stocky-male','orc','Orc_male_User_Approved.png'),
 ('stocky-female','orc-female','Orc_female_User_Approved.png'),
 ('small-male','goblin','goblin-walk-guide.png'),
 ('small-female','goblin-female','goblin-female-walk-guide.png')]
DIRECTIONS=['South','North','East','West']


def prepare(here,dest,donors):
    records={};directory=dest/'Body Templates';directory.mkdir(parents=True,exist_ok=True)
    sources_by_id={a['id']:a for a in donors}
    for key,guide,filename in SOURCES:
        folder=directory/key;folder.mkdir(exist_ok=True)
        rejected=folder/'Body_Master_Artwork.png'
        if rejected.exists():
            archive=folder/'Rejected Generated Interpretation';archive.mkdir(exist_ok=True)
            shutil.move(str(rejected),str(archive/rejected.name))
            if (folder/'Generation_Prompt.md').exists():shutil.move(str(folder/'Generation_Prompt.md'),str(archive/'Generation_Prompt.md'))
        original=here/'references'/filename;artwork=folder/'Approved_Source_Artwork.png'
        shutil.copyfile(original,artwork)
        source=Image.open(artwork).convert('RGBA')
        assert source.size==(1024,768),(key,source.size)
        # These references are exactly 4× enlarged 64px cells. Integer reduction
        # retains their original pixel layout and never fits one body to another.
        atlas=source.resize((256,192),Image.Resampling.NEAREST)
        atlas.save(folder/'Approved_Source_Atlas_64px.png')
        core_atlas=Image.new('RGBA',(256,192));skin_atlas=Image.new('RGBA',(256,192))
        head_atlas=Image.new('RGBA',(256,192));neutral_atlas=Image.new('RGBA',(256,192));rig=[];tones=[]
        donor=sources_by_id[guide]
        for f in range(3):
            joints=[];row_tones=[]
            for v in range(4):
                tile=atlas.crop((v*64,f*64,v*64+64,f*64+64))
                head,extra,info=extract(tile,donor,f,v)
                head_atlas.paste(head,(v*64,f*64))
                body=tile.copy();skin=Image.new('RGBA',(64,64));tone=skin_color(tile,info['cutY'])
                for y in range(64):
                    for x in range(64):
                        c=tile.getpixel((x,y))
                        if head.getpixel((x,y))[3]:body.putpixel((x,y),(0,0,0,0));continue
                        if c[3]>0 and max(c[:3])>22 and max(c[:3])-min(c[:3])>=12:skin.putpixel((x,y),(255,255,255,255))
                # Fill only the occluded central back under long hair. Every
                # originally visible body pixel and every head pixel is retained.
                if v==1:
                    half=7 if key.startswith('standard') else 9 if key.startswith('stocky') else 5
                    waist=round(donor['rigs'][f][v]['hip'])-2
                    cx=info.get('extractionCenter',info['neck'])[0]
                    for y in range(info['cutY'],min(waist,61)):
                        for x in range(max(1,cx-half),min(63,cx+half+1)):
                            if head.getpixel((x,y))[3] and not body.getpixel((x,y))[3]:
                                body.putpixel((x,y),(*tone,255));skin.putpixel((x,y),(255,255,255,255))
                core_atlas.paste(body,(v*64,f*64));skin_atlas.paste(skin,(v*64,f*64))
                neutral=body.copy()
                for y in range(64):
                    for x in range(64):
                        c=neutral.getpixel((x,y))
                        if skin.getpixel((x,y))[3]:
                            value=max(65,min(235,round(light(c)*160/max(10,light(tone)))))
                            neutral.putpixel((x,y),(value,value,value,c[3]))
                neutral_atlas.paste(neutral,(v*64,f*64))
                body.save(folder/(DIRECTIONS[v]+'_Pose_'+str(f)+'_64px.png'))
                joints.append(dict(neck=info['neck'],feet=[32,61],bounds=list(body.getchannel('A').getbbox()),bodyJoints=donor['rigs'][f][v]))
                row_tones.append(tone)
            rig.append(joints);tones.append(row_tones)
        for img,name in [(core_atlas,'Body_Core_Atlas_64px.png'),(skin_atlas,'Skin_Mask_64px.png'),(head_atlas,'Source_Heads_64px.png'),(neutral_atlas,'Neutral_Body_Core_64px.png')]:img.save(folder/name)
        rec=dict(id=key,build=key.rsplit('-',1)[0],sex=key.rsplit('-',1)[1],reference=guide,
            core='Body Templates/'+key+'/Body_Core_Atlas_64px.png',
            neutral='Body Templates/'+key+'/Neutral_Body_Core_64px.png',
            skinMask='Body Templates/'+key+'/Skin_Mask_64px.png',sourceTones=tones,
            sourceAtlas='Body Templates/'+key+'/Approved_Source_Atlas_64px.png',
            frames=3,frameSize=64,logicalBodySpace=64,directionOrder=DIRECTIONS,sequence=[0,1,0,2],rig=rig,
            coreAlphaSha256=hashlib.sha256(core_atlas.getchannel('A').tobytes()).hexdigest(),
            artworkSha256=hashlib.sha256(artwork.read_bytes()).hexdigest(),
            sourceArtwork='Body Templates/'+key+'/Approved_Source_Artwork.png',
            method='Original visible body pixels copied at their existing 64px coordinates. No generated body redraw, no independent body scaling. Hidden central back under hair is backed with the source skin tone.')
        (folder/'rig.json').write_text(json.dumps(rec,indent=2));records[key]=rec
    return records


def tint(core,target,mask,source):
    out=core.copy();baseline=max(10,light(source))
    for y in range(core.height):
        for x in range(core.width):
            c=core.getpixel((x,y))
            if mask.getpixel((x,y))[3]:
                factor=max(.35,min(1.60,light(c)/baseline))
                out.putpixel((x,y),(*(min(255,round(v*factor)) for v in target),c[3]))
    return out

