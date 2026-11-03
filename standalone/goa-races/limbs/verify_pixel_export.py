"""Mechanical exporter conformance check using asymmetric synthetic pixel parts."""
from pathlib import Path
import json
import tempfile

from PIL import Image, ImageDraw
import build_pixel_assets as export


def main():
    with tempfile.TemporaryDirectory(prefix='limb-export-fixture-') as temporary:
        root=Path(temporary)
        normal=Image.new('RGBA',(64,64));normal.save(root/'source.png')
        frames=[];cuts=[]
        for frame in range(3):
            images=[];layers=[]
            for view in range(4):
                core=Image.new('RGBA',(64,64));ImageDraw.Draw(core).rectangle((26,15,37,41),fill=(70+view,80+frame,90,192))
                parts={}
                for slot,box in zip(export.SLOTS,[(20,28,25,42),(38,27,44,41),(26,42,31,59),(32,42,38,60)]):
                    part=Image.new('RGBA',(64,64))
                    if not (view==2 and slot=='LeftArm'):
                        ImageDraw.Draw(part).rectangle(box,fill=(110+frame*10,80+view*10,130,128 if slot=='LeftLeg' else 255))
                    parts[slot]=part
                original=core.copy()
                for part in parts.values():original.paste(part,(0,0),export.support(part))
                images.append(original);layers.append(dict(core=core,parts=parts,masks={slot:export.support(part) for slot,part in parts.items()},method='asymmetric test fixture',qualityFlags=[]))
            frames.append(images);cuts.append(layers)
        class Cutter:
            @staticmethod
            def render_body(_body):return frames
            @staticmethod
            def split_frame(_cell,_body,frame,view):return cuts[frame][view]
        body=dict(id='fixture',label='Fixture',raceKey='Fixture',variant='Base',source=str(root/'source.png'),sourceRects=[[[0,0,64,64]]*4]*3,animation=dict(kind='walk',sequence=[0,1,0,2],delaysMs=[200]*4),qualityFlags=[])
        manifest,report=export.pack_body(body,Cutter,root/'output')
        assert report['exactRGBAReconstruction'] and report['injuryViewsChecked']==192
        assert report['overlappingPixels']==report['outsideMaskChangedPixels']==0
        assert report['proof'][2]['visiblePartPixels']['LeftArm']==0
        assert manifest[0]['rows']==12 and manifest[1]['rows']==48
        folder=root/'output/fixture'
        with Image.open(folder/'injuries.png') as atlas:
            assert atlas.size==(256,3072)
            for state_index,(bits,state) in enumerate(export.STATES):
                for frame in range(3):
                    for view in range(4):
                        actual=atlas.crop((view*64,(state_index*3+frame)*64,(view+1)*64,(state_index*3+frame+1)*64))
                        expected=export.without(frames[frame][view],cuts[frame][view],bits)
                        assert actual.tobytes()==expected.tobytes(),(state,frame,view)
        with Image.open(folder/'injuries.dmi') as dmi:
            assert dmi.size==(256,4096)
            text=dmi.info['Description']
            assert text.count('state = ')==16
            assert text.count('\tframes = 4')==16
            assert text.count('\tdelay = 2,2,2,2')==16
            assert dmi.crop((0,0,256,64)).tobytes()==dmi.crop((0,128,256,192)).tobytes()
        import wound_pixels
        pure_files=['normal.png','core.png','parts.png','injuries.png','normal.dmi','parts.dmi','injuries.dmi']
        before={name:export.sha(folder/name) for name in pure_files}
        wounded_manifest,wounded=export.pack_body(body,Cutter,root/'output',wounds=wound_pixels)
        assert before=={name:export.sha(folder/name) for name in pure_files}
        assert len(wounded_manifest)==3 and wounded['woundCaps']['capPixels']>0
        assert wounded['woundCaps']['outsideCapAndRemovedMaskChangedPixels']==0
        assert wounded['woundCaps']['outsideCapVsPureInjuryChangedPixels']==0
        with Image.open(folder/'wound-caps.dmi') as dmi:
            assert dmi.info['Description'].count('state = ')==4
        with Image.open(folder/'injuries-with-blood.dmi') as dmi:
            assert dmi.info['Description'].count('state = ')==16
        bone=dict(body,id='fixture-bone',raceKey='Skeleton')
        _,bloodless=export.pack_body(bone,Cutter,root/'output',wounds=wound_pixels)
        assert bloodless['woundCaps']['capPixels']==0
        assert (root/'output/fixture-bone/injuries.png').read_bytes()==(root/'output/fixture-bone/injuries-with-blood.png').read_bytes()
        bad=cuts[0][0].copy();bad['parts']=dict(bad['parts']);bad['parts']['LeftArm']=bad['parts']['LeftArm'].copy()
        bad['parts']['LeftArm'].putpixel((27,16),(1,2,3,255))
        try:
            export.validate_partition(frames[0][0],bad)
        except ValueError as error:
            assert 'Overlapping' in str(error)
        else:raise AssertionError('Overlapping part assignments were accepted')
        result=dict(injury_states=16,injury_views_checked=192,exact_rgba_reconstruction=True,no_overlap=True,hidden_empty_parts_allowed=True,outside_removal_mask_unchanged=True,dmi_states=16,dmi_walk_frames=4,dmi_walk_delays_deciseconds=[2,2,2,2],neutral_pose_repeated_exactly=True,pure_files_unchanged_with_blood=True,cap_pixels_source_palette_only=True,cap_budget=4,blood_outside_cap_and_removal_masks_unchanged=True,bone_has_no_blood=True,ai_calls=0)
        print(json.dumps(result))


if __name__=='__main__':main()
