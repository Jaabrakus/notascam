#!/usr/bin/env python3
"""Apply data-defined appearance layers using exact donor pixels.

Each JSON preset supplies base sheets, donor regions, extraction masks, per-pose
attachment points and depth. No race-specific coordinates live in this engine.
Only integer enlargement, quarter turns and integer placement are supported.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]


def safe_id(value):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',value):raise ValueError('Use simple layer and appearance IDs')
    return value


def read_image(path):
    with Image.open(path) as image:
        return np.array(image.convert('RGBA'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def polygon_mask(size, polygon):
    image=Image.new('1',size)
    ImageDraw.Draw(image).polygon([tuple(p) for p in polygon],fill=1)
    return np.array(image,dtype=bool)


def expand(mask):
    padded=np.pad(mask,1)
    return np.logical_or.reduce([padded[y:y+mask.shape[0],x:x+mask.shape[1]]
                                 for y in range(3) for x in range(3)])


def extract(donor, spec):
    cell=spec['cell'];size=spec.get('cellSize',64)
    tile=donor[cell[1]*size:(cell[1]+1)*size,cell[0]*size:(cell[0]+1)*size]
    if tile.shape[:2]!=(size,size):raise ValueError('Invalid donor cell')
    mask=tile[...,3]>=spec.get('alphaMin',128)
    rgb=tile[...,:3].astype(float)
    rule=spec.get('colorRule',{})
    for channel,minimum in rule.get('min',{}).items():mask &= rgb[...,int(channel)]>=minimum
    for a,b,factor in rule.get('ratios',[]):mask &= rgb[...,a]>rgb[...,b]*factor
    if 'maxSpread' in rule:mask &= rgb.max(2)-rgb.min(2)<=rule['maxSpread']
    bounds=spec['region'];region=np.zeros(mask.shape,bool)
    region[bounds[1]:bounds[3],bounds[0]:bounds[2]]=True
    mask &= region
    if spec.get('polygon'):mask &= polygon_mask((size,size),spec['polygon'])
    if spec.get('outlineRadius'):
        near=mask.copy()
        for _ in range(spec['outlineRadius']):near=expand(near)
        mask |= near & region & (rgb.max(2)<spec.get('outlineMax',45)) & (tile[...,3]>=128)
    if not mask.any():raise ValueError('Empty source layer')
    result=np.zeros_like(tile);result[mask]=tile[mask]
    return result


def transformed(piece, anchor, scale, turns):
    if not isinstance(scale,int) or scale<1:raise ValueError('Scale must be a positive integer')
    anchor=list(anchor);h,w=piece.shape[:2]
    for _ in range(turns%4):
        piece=np.rot90(piece);anchor=[anchor[1],w-1-anchor[0]];h,w=w,h
    piece=np.repeat(np.repeat(piece,scale,axis=0),scale,axis=1)
    return piece,[anchor[0]*scale,anchor[1]*scale]


def put(destination, piece, x, y, cell_box, clip=None):
    x0,y0,x1,y1=cell_box;h,w=piece.shape[:2]
    ys,xs=np.nonzero(piece[...,3])
    if len(xs) and (xs.min()+x<x0 or ys.min()+y<y0 or xs.max()+x>=x1 or ys.max()+y>=y1):
        raise ValueError('Layer crosses its animation cell boundary')
    left,top=max(x,0),max(y,0);right,bottom=min(x+w,destination.shape[1]),min(y+h,destination.shape[0])
    if right<=left or bottom<=top:return 0
    patch=piece[top-y:bottom-y,left-x:right-x];mask=patch[...,3]>0
    if clip is not None:mask &= clip[top:bottom,left:right]
    destination[top:bottom,left:right][mask]=patch[mask]
    return int(mask.sum())


def render(config, root, stage):
    original=read_image(root/config['geometryReference'])
    h,w=original.shape[:2];rows,cols=config['grid']['rows'],config['grid']['columns']
    xedges=config['grid'].get('xEdges',[round(i*w/cols) for i in range(cols+1)])
    yedges=config['grid'].get('yEdges',[round(i*h/rows) for i in range(rows+1)])
    if xedges[0]!=0 or xedges[-1]!=w or yedges[0]!=0 or yedges[-1]!=h:raise ValueError('Grid does not cover source')
    r,g,b=original[...,:3].astype(int).transpose(2,0,1)
    # Skin masks are an input asset for general races. This preset uses an exact
    # selection rule for its green body, shared with the palette swap proof.
    if config.get('bodyMask'):
        skin=read_image(root/config['bodyMask'])[...,3]>0
    else:
        rule=config['skinMaskRule']
        skin=(g-r>=rule['greenMinusRed'])&(g-b>=rule['greenMinusBlue'])&(g>rule['minGreen'])&(original[...,3]>0)
    inputs={config['geometryReference']:sha(root/config['geometryReference'])}
    results=[]
    for variant in config['variants']:
        safe_id(variant['id'])
        base=read_image(root/variant['base']);inputs[variant['base']]=sha(root/variant['base'])
        if base.shape!=original.shape:raise ValueError('Base sheet dimensions differ')
        folder=stage/variant['id'];(folder/'layers').mkdir(parents=True)
        front=np.zeros_like(base);back=np.zeros_like(base);records=[]
        for spec in variant['layers']:
            safe_id(spec['id'])
            donor_path=root/spec['source'];inputs[spec['source']]=sha(donor_path)
            donor=read_image(donor_path);piece=extract(donor,spec['extract'])
            layer=np.zeros_like(base);placements=[]
            for placement in spec['placements']:
                row,col=placement['cell'];box=[xedges[col],yedges[row],xedges[col+1],yedges[row+1]]
                transformed_piece,anchor=transformed(piece,spec['sourceAnchor'],placement.get('scale',spec.get('scale',1)),placement.get('quarterTurns',0))
                x=box[0]+placement['target'][0]-anchor[0];y=box[1]+placement['target'][1]-anchor[1]
                if not isinstance(x,int) or not isinstance(y,int):raise ValueError('Use integer pixel placement')
                clip=skin.copy() if spec.get('clipToSkin') else None
                if placement.get('occludePolygons'):
                    if clip is None:clip=np.ones((h,w),bool)
                    for polygon in placement['occludePolygons']:
                        shifted=[[p[0]+box[0],p[1]+box[1]] for p in polygon]
                        clip &= ~polygon_mask((w,h),shifted)
                count=put(layer,transformed_piece,x,y,box,clip)
                if not count and not placement.get('allowOccluded'):
                    raise ValueError('Invisible attachment: '+spec['id']+' cell '+str([row,col]))
                placements.append(dict(cell=[row,col],copiedPixels=count,fullyOccluded=not bool(count)))
            donor_colors=set(map(tuple,piece[piece[...,3]>0]))
            assert all(tuple(p) in donor_colors for p in np.unique(layer[layer[...,3]>0],axis=0)), 'Interpolated donor pixels'
            depth=back if spec.get('depth')=='behind' else front
            mask=layer[...,3]>0;depth[mask]=layer[mask]
            Image.fromarray(layer).save(folder/'layers'/(spec['id']+'.png'))
            records.append(dict(id=spec['id'],source=spec['source'],depth=spec.get('depth','front'),placements=placements,exactDonorRGBA=True))
        composite=base.copy();visible=base[...,3]>=config.get('occlusionAlphaMin',128)
        exposed_back=(back[...,3]>0)&~visible;composite[exposed_back]=back[exposed_back]
        visible_front=front[...,3]>0;composite[visible_front]=front[visible_front]
        affected=visible_front|((back[...,3]>0)&~visible)
        assert np.array_equal(composite[~affected],base[~affected]), 'Unrelated body pixels changed'
        Image.fromarray(base).save(folder/'palette-only.png')
        Image.fromarray(front).save(folder/'front-layers.png')
        Image.fromarray(back).save(folder/'back-layers.png')
        Image.fromarray(composite).save(folder/'composite.png')
        results.append(dict(id=variant['id'],layers=records,bodyOutsideLayersIdentical=True,
                            additionalVisiblePixels=int(((composite[...,3]>0)&~visible).sum())))
    assert all(sha(root/path)==value for path,value in inputs.items()), 'Input changed'
    (stage/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    report=dict(status='technical_checks_passed_needs_visual_review',inputs=inputs,variants=results,
                geometryUnmodified=True,interpolation='none',imageGeneration=False,
                baseIsProductionAtlas=config.get('baseIsProductionAtlas',False),
                limits=['Only configured attachments and calibrated poses are covered.',
                        'New body proportions require new attachment calibration.',
                        'Inherited generated base remains an unregistered draft.'])
    (stage/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    # Overview copies the first pose row without rescaling any sprite pixels.
    band=yedges[1]+28
    comparison=Image.new('RGBA',(w,band*len(results)),(68,73,82,255))
    draw=ImageDraw.Draw(comparison)
    for index,variant in enumerate(config['variants']):
        draw.text((12,index*band+8),variant['id'].title()+' - copied appearance layers',fill='white')
        with Image.open(stage/variant['id']/'composite.png') as image:
            comparison.alpha_composite(image.crop((0,0,w,yedges[1])),(0,index*band+28))
    comparison.save(stage/'comparison.png')
    viewer=Path(__file__).with_name('appearance_layers_viewer.html').read_text()
    viewer_data=dict(name=config['name'],rows=rows,columns=cols,xEdges=xedges,yEdges=yedges,
                     variants=[v['id'] for v in config['variants']])
    (stage/'index.html').write_text(viewer.replace('/*CONFIG*/',json.dumps(viewer_data).replace('<','\\u003c')))
    return report


def run_job(config_path,out,root):
    config=json.loads(config_path.read_text());out=out.resolve()
    if out.exists():
        manifest=out/'file-hashes.json'
        if manifest.is_file() and json.loads((out/'config.json').read_text())==config:
            hashes=json.loads(manifest.read_text())
            report=json.loads((out/'verification.json').read_text())
            unchanged=all((out/p).is_file() and sha(out/p)==h for p,h in hashes.items())
            unchanged &= all((root/p).is_file() and sha(root/p)==h for p,h in report['inputs'].items())
            unchanged &= report.get('pipelineSha256')==sha(Path(__file__))
            unchanged &= report.get('viewerSha256')==sha(Path(__file__).with_name('appearance_layers_viewer.html'))
            if unchanged:return dict(output=str(out),status='unchanged_outputs_reused')
        raise ValueError('Output exists with different or unverified inputs; use a new versioned review folder')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.appearance-layers-',dir=out.parent) as temp:
        stage=Path(temp)/'result';stage.mkdir()
        report=render(config,root,stage)
        report['pipelineSha256']=sha(Path(__file__))
        report['viewerSha256']=sha(Path(__file__).with_name('appearance_layers_viewer.html'))
        (stage/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
        hashes={str(p.relative_to(stage)):sha(p) for p in sorted(stage.rglob('*')) if p.is_file()}
        (stage/'file-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
        stage.rename(out)
    return dict(output=str(out),status=report['status'],variants=len(report['variants']),
                layers=sum(len(v['layers']) for v in report['variants']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--config',type=Path)
    mode.add_argument('--batch',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args();root=args.root.resolve()
    if args.config:
        if not args.output:parser.error('--output is required with --config')
        print(json.dumps(run_job(args.config,args.output,root)))
    else:
        jobs=json.loads(args.batch.read_text());failures=[]
        for job in jobs:
            try:print(json.dumps(run_job(root/job['config'],root/job['output'],root)))
            except Exception as error:
                failures.append(str(error));print(json.dumps(dict(config=job['config'],status='failed',error=str(error))))
        if failures:raise SystemExit(1)


if __name__=='__main__':main()
