#!/usr/bin/env python3
"""Repeatable Orc appearance batch. No image generation or network required."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'pipeline'))
import appearance_layers as engine

def luminance(rgb):
    return np.sum(rgb.astype(float)*np.array([.2126,.7152,.0722]),axis=-1)

def sample_palette(donor, kind):
    sample=donor[28:40,25:39].reshape(-1,4)
    rgb=sample[:,:3].astype(int);r,g,b=rgb.T
    if kind=='gray':mask=(rgb.max(1)-rgb.min(1)<35)&(rgb.max(1)>25)&(rgb.max(1)<125)
    elif kind=='red':mask=(r>3*g)&(r>3*b)&(r>45)
    else:mask=(g>r*1.1)&(g>b*1.2)&(g>30)
    colors=np.unique(rgb[mask&(sample[:,3]>=128)],axis=0)
    if len(colors)<6:raise ValueError('Not enough sampled skin colors')
    lum=luminance(colors)
    return np.array([colors[np.abs(lum-q).argmin()] for q in np.quantile(lum,[.03,.2,.4,.6,.8,.98])],dtype=np.uint8)

def recolor(master, donor, variant):
    rgb=master[:,:,:3].astype(int);r,g,b=rgb.transpose(2,0,1)
    skin=(g-r>=6)&(g-b>=9)&(g>25)&(master[:,:,3]>0)
    shades=sample_palette(donor,variant['paletteKind'])
    lum=luminance(rgb);levels=np.quantile(lum[skin],[.03,.2,.4,.6,.8,.98])
    indices=np.abs(lum[skin,None]-levels).argmin(1)
    result=master.copy();result[skin,:3]=shades[indices]
    allowed=skin.copy()
    if variant.get('eyeSwap'):
        eyes=(r>90)&(r>g*2.5)&(r>b*2.5)&(master[:,:,3]>0)
        eye_sample=donor[10:28,:64].reshape(-1,4)
        values=eye_sample[:,:3].astype(int)
        selection=(eye_sample[:,3]>=128)&(values[:,0]>150)&(values[:,1]>150)&(values[:,2]>120)
        whites=np.unique(values[selection],axis=0)
        if not len(whites):raise ValueError('Missing donor eye colors')
        light=luminance(whites);eye_ramp=whites[np.argsort(light)]
        result[eyes,:3]=eye_ramp[np.clip((r[eyes]/255*(len(eye_ramp)-1)).astype(int),0,len(eye_ramp)-1)]
        allowed|=eyes
    assert np.array_equal(result[:,:,3],master[:,:,3]),'Palette pass changed transparency'
    assert np.array_equal(result[~allowed],master[~allowed]),'Palette pass changed protected pixels'
    return result,{'skinPalette':shades.tolist(),'skinPixels':int(skin.sum()),'eyeSwap':bool(variant.get('eyeSwap')),'alphaIdentical':True,'nonAppearancePixelsIdentical':True}

def validate_master(master):
    # Calibration is tied to this approved sheet. New animations need their own
    # anchors, not an automatic rescale of coordinates from an unrelated pose.
    lock=ROOT/'master-lock.json'
    actual={'path':'inputs/approved-attack.png','sha256':engine.sha(master)}
    if lock.exists():
        if json.loads(lock.read_text())!=actual:raise ValueError('Approved master changed. Create a new preset and calibration instead of overwriting this lock.')
    else:lock.write_text(json.dumps(actual,indent=2)+'\n')

def build(output, only=None):
    start=time.perf_counter();registry=json.loads((ROOT/'variants.json').read_text())
    master_path=ROOT/registry['master'];validate_master(master_path)
    original_hash=engine.sha(master_path);master=engine.read_image(master_path)
    (ROOT/'palette-bases').mkdir(exist_ok=True);output.mkdir(parents=True,exist_ok=True)
    variants=registry['variants']
    if only:
        requested=set(only);variants=[v for v in variants if v['id'] in requested]
        missing=requested-{v['id'] for v in variants}
        if missing:raise ValueError('Unknown or uncalibrated variants: '+', '.join(sorted(missing)))
    report=[]
    for v in variants:
        donor_path=ROOT/v['donor'];donor_hash=engine.sha(donor_path)
        recolored,checks=recolor(master,engine.read_image(donor_path),v)
        Image.fromarray(recolored).save(ROOT/'palette-bases'/f'{v["id"]}.png')
        result=engine.run_job(ROOT/v['preset'],output/v['id'],ROOT)
        assert engine.sha(donor_path)==donor_hash
        report.append({'id':v['id'],'layerDefinitions':v['layers'],'paletteChecks':checks,'result':result})
        print(v['id']+': '+result['status'])
    assert engine.sha(master_path)==original_hash
    report_data={'status':'built_for_visual_review','sourceUnchanged':True,'imageGeneration':False,'networkRequired':False,'variants':report,'excluded':registry['excluded'],'seconds':round(time.perf_counter()-start,2)}
    (output/'batch-report.json').write_text(json.dumps(report_data,indent=2)+'\n')
    preview(output,variants,registry)
    print('Output: '+str(output))
    return report_data

def preview(output,variants,registry):
    # Display all four directions of the ready pose. Only integer reduction is
    # used in this contact preview; original-size sprites remain unmodified.
    rows=[]
    for v in variants:
        image=Image.open(output/v['id']/v['id'].lower()/'composite.png').convert('RGBA')
        band=image.crop((0,0,image.width,registry['sourceGrid']['yEdges'][1]))
        rows.append((v['id'],band))
    canvas=Image.new('RGBA',(1254,len(rows)*350),'#444952');draw=ImageDraw.Draw(canvas)
    for i,(label,band) in enumerate(rows):draw.text((12,i*350+10),label,fill='white');canvas.alpha_composite(band,(0,i*350+35))
    canvas.save(output/'comparison.png')
    data={'variants':[v['id'] for v in variants],'grid':registry['sourceGrid']}
    template=(ROOT/'pipeline/batch_viewer.html').read_text()
    (output/'index.html').write_text(template.replace('/*CONFIG*/',json.dumps(data)))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'output-v1')
    parser.add_argument('--only',nargs='+',help='Variant IDs such as Ashen Hellblooded')
    args=parser.parse_args()
    build(args.output.resolve(),args.only)
