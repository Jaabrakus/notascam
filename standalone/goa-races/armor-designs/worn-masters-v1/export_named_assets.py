"""Package the current worn masters with readable names and individual facings."""
from pathlib import Path
import hashlib
import json
import shutil
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
DEST=ROOT/'Dungeon Master Sample/Worn Armor and Idle Poses'
NAMES={
    'deepguard-iron':'Deepguard_Iron_Unarmed',
    'deepguard-iron-armed':'Deepguard_Iron_Sword_and_Shield',
    'deepguard-iron-spear-shield-idle':'Deepguard_Iron_Spear_and_Shield_Idle',
    'deepguard-iron-staff-idle':'Deepguard_Iron_Crystal_Staff_Idle',
    'human-leather':'Human_Leather_Unarmed',
    'dwarf-gold':'Dwarf_Gold_Unarmed',
}
PROMPTS={
    'deepguard-iron':HERE.parent/'deepguard-iron/pixel-fit-v2/PROMPT.md',
    'deepguard-iron-armed':HERE/'DEEPGUARD-IRON-ARMED-PROMPT.md',
    'deepguard-iron-spear-shield-idle':HERE/'DEEPGUARD-IRON-SPEAR-SHIELD-IDLE-V2-PROMPT.md',
    'deepguard-iron-staff-idle':HERE/'DEEPGUARD-IRON-STAFF-IDLE-V2-PROMPT.md',
    'human-leather':HERE/'HUMAN-LEATHER-PROMPT.md',
    'dwarf-gold':HERE/'DWARF-GOLD-PROMPT.md',
}


def main():
    masters=json.loads((HERE/'masters.json').read_text())['masters']
    DEST.mkdir(parents=True,exist_ok=True)
    result=[]
    for master in masters:
        name=NAMES[master['id']];folder=DEST/name;folder.mkdir(exist_ok=True)
        artwork=folder/(name+'_Artwork.png')
        source=HERE/master['source'];shutil.copyfile(source,artwork)
        size=master['frameSize'];sheet=folder/(name+'_Sheet_'+str(size)+'px.png')
        shutil.copyfile(HERE/master['spriteFile'],sheet)
        frames=[]
        with Image.open(sheet) as atlas:
            assert atlas.mode=='RGBA' and atlas.size==(size*4,size)
            for frame in master['frames']:
                x,y,w,h=frame['rect'];image=atlas.crop((x,y,x+w,y+h))
                path=folder/(name+'_'+frame['direction']+'_'+str(size)+'px.png')
                image.save(path)
                assert image.getchannel('A').getbbox()
                assert Image.open(path).tobytes()==image.tobytes()
                frames.append(dict(direction=frame['direction'],file=path.name,frameSize=[w,h],bodyOrigin=frame['bodyOrigin'],feet=frame['feet']))
        assert hashlib.sha256(artwork.read_bytes()).hexdigest()==master['sourceSha256']
        prompt=PROMPTS[master['id']]
        if prompt.exists():shutil.copyfile(prompt,folder/'Generation_Prompt.md')
        record=dict(id=master['id'],name=name,race=master['race'],artwork=artwork.name,sheet=sheet.name,frameSize=[size,size],bodySpace=[64,64],directionOrder=['South','North','East','West'],frames=frames,sourceSha256=master['sourceSha256'],sourceAsset=str(source.resolve().relative_to(ROOT)),pose=master.get('pose','standing'),holdingHand=master.get('holdingHand'),offhand=master.get('offhand'),limits=master['limits'])
        (folder/'manifest.json').write_text(json.dumps(record,indent=2))
        result.append(dict(name=name,folder=name,manifest=name+'/manifest.json'))
    (DEST/'index.json').write_text(json.dumps(dict(sets=result),indent=2))
    (DEST/'README.md').write_text('# Worn Armor and Idle Poses\n\nCurrent complete-character artwork and sprite exports. The spear/shield and staff folders contain the corrected v2 poses.\n\nEach folder contains the high-resolution artwork, a four-direction sprite sheet, individual South (front), North (back), East (right-facing) and West (left-facing) PNGs, a frame manifest and the generation prompt.\n\nAll bodies use 64px fitting space. Spear and staff frames are padded to 128 × 128 to preserve the full pole; their body origin is (32,32). Other frames are 64 × 64. The direction PNGs keep their frame padding and shared registration. These are standing views; motion and sixteen-direction versions are not included.\n\n'+''.join('- '+r['name']+'\n' for r in result))
    print(json.dumps(dict(folder=str(DEST),sets=len(result),directionPNGs=sum(len(m['frames']) for m in masters),artworkPNGs=len(result),spriteSheets=len(result))))


if __name__=='__main__':main()
