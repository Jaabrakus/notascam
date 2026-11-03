"""Catalog native imagegen artwork and preserve real source rectangles.

This cuts source cells; it never repaints, recolors or fabricates missing views.
Fitting and animation remain explicit separate authoring stages.
"""
from pathlib import Path
import json, re, hashlib
from itertools import combinations
from PIL import Image

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
STANDARD=['helmet','chest','shoulder-left','shoulder-right','bracer-left','bracer-right','belt','hip-panels','greave-left','greave-right','boot-left','boot-right']
METAL=['helmet','chest','shoulder-one','bracer-left','bracer-right','belt-hip-panels','lower-leg-left','lower-leg-right']
SPECIAL={
 'elf-leather':['hood-mantle','chest-wrap','strap-left','bracer-right','belt','hip-panels','boot-left','boot-right'],
 'dwarf-leather':['helmet','chest-apron','strap-right','bracer-left','bracer-right','belt','boot-left','boot-right'],
 'dark-elf-leather':['brow-piece','longcoat','harness','gauntlet-left','bracer-right','belt-hip-panels','boot-left','boot-right'],
 'goblin-leather':['helmet','chest','harness-satchel','bracer-left','bracer-right','belt-hip-panels','boot-left','boot-right'],
 'kobold-leather':['brow-piece','chest','back-mantle','bracer-left','bracer-right','belt-hip-panels','boot-left','boot-right'],
 'melee-weapons':['weapon.dagger','weapon.arming sword','weapon.longsword','weapon.scimitar','weapon.hand axe','weapon.battle axe','weapon.warhammer','weapon.mace','goa.sword'],
 'polearms-tools':['weapon.morning star','weapon.spear','weapon.halberd','weapon.pickaxe','weapon.bow','weapon.hammer','weapon.fishing rod','weapon.harpoon','weapon.spade'],
 'magic-staves':['weapon.crystal staff','weapon.orb staff','weapon.skull staff','weapon.flame staff','weapon.nature staff','weapon.dragon staff','weapon.spider staff'],
 'enchanted-weapons':['weapon.rune sword','weapon.flame sword','weapon.frost axe','weapon.storm spear','weapon.void blade','weapon.holy mace','weapon.soul eater','weapon.bloodwhisker'],
 'dragon-helmets':['kobold-dragonhide.helmet','orc-dragonbone.helmet'],
 'dragonbone-shoulder':['orc-dragonbone.shoulder-one'],
 'custom-helmets':['helmet.kettle','helmet.nasal','helmet.horned','helmet.winged','helmet.great helm','helmet.crested'],
 'custom-shields':['shield.buckler','shield.round','shield.heater','shield.kite','shield.tower'],
 'robe-colors':['robe.black','robe.red','robe.white','robe.brown','robe.blue','robe.purple','robe.crimson','robe.green','robe.grey'],
 'special-robes':['robe.dragonrobe','robe.spiderrobe','robe.bonerobe','robe.gold'],
 'armor-styles':['chest.banded','chest.mail','chest.scale','chest.lamellar','chest.brigandine','chest.tabard','goa.chest','arms.plate','arms.mail','legs.mail','legs.scale','legs.cloth'],
 'ornate-helmets':['ornate.helmet.kettle','ornate.helmet.nasal','ornate.helmet.horned','ornate.helmet.winged','ornate.helmet.great-helm','ornate.helmet.crested'],
 'ornate-armor-finishes':['human.iron.gold-trim','human.iron.gold-trim.ruby','orc.leather.gold-trim','orc.leather.gold-trim.amber','dark-elf.silver.gold-trim','dark-elf.silver.gold-trim.amethyst'],
}
DIRS=['South','North','East','West']


def bands(image):
    alpha=image.getchannel('A');busy=[]
    for y in range(image.height):
        if sum(v>=128 for v in alpha.crop((0,y,image.width,y+1)).getdata())>=12:busy.append(y)
    groups=[]
    for y in busy:
        if not groups or y-groups[-1][-1]>6:groups.append([y])
        else:groups[-1].append(y)
    return [(g[0],g[-1]+1) for g in groups]


def view_cuts(image):
    """Find transparent gutters; generated views are not equal-width cells."""
    alpha=image.getchannel('A');busy=[]
    for x in range(image.width):
        if sum(v>=128 for v in alpha.crop((x,0,x+1,image.height)).getdata())>=3:busy.append(x)
    groups=[]
    for x in busy:
        if not groups or x-groups[-1][-1]>3:groups.append([x])
        else:groups[-1].append(x)
    gaps=[((a[-1]+1+b[0])//2,b[0]-a[-1]-1) for a,b in zip(groups,groups[1:])]
    if len(groups)==4:return [0]+[g[0] for g in gaps]+[image.width],'detected gutters'
    candidates=[]
    for choice in combinations(gaps,3):
        cuts=[0]+[g[0] for g in choice]+[image.width]
        if min(b-a for a,b in zip(cuts,cuts[1:]))<image.width*.11:continue
        cost=sum(((g[0]-(i+1)*image.width/4)/(image.width/4))**2-1.2*g[1]/(image.width/4) for i,g in enumerate(choice))
        candidates.append((cost,cuts))
    if candidates:return min(candidates)[1],'detected grouped-piece gutters'
    return [round(i*image.width/4) for i in range(5)],'column layout requires review'


def build():
    records=[];failures=[]
    for source in sorted(HERE.glob('*-v1.png')):
        if source.name=='source-weapon-designs.png':continue
        name=source.stem.removesuffix('-v1').removesuffix('-pieces').removesuffix('-design')
        if name=='armor':name='human-iron'
        if name=='leather':name='human-leather'
        pieces=SPECIAL.get(name,STANDARD if name in ['human-iron','human-leather','orc-leather'] else METAL)
        with Image.open(source) as image:
            if image.mode!='RGBA':failures.append(dict(id=name,reason='no alpha'));continue
            rows=bands(image)
            if name=='polearms-tools':
                # Spear tip and halberd tip nearly touch; inspect and retain
                # the actual source rows rather than assuming a uniform grid.
                rows=[(29,145),(163,328),(331,544),(558,684),(699,889),(906,1026),(1041,1210),(1225,1428),(1440,1596)]
            if name=='special-robes':rows=[(10,311),(318,617),(621,899),(902,1234)]
            if name=='dragonbone-shoulder':rows=[(0,image.height)]
            if name=='ornate-armor-finishes':rows=[(28,234),(254,454),(473,702),(711,939),(947,1214),(1216,1503)]
            if len(rows)!=len(pieces):
                failures.append(dict(id=name,reason='row count requires review',expected=len(pieces),detected=rows));continue
            cuts=[0]+[(rows[i-1][1]+rows[i][0])//2 for i in range(1,len(rows))]+[image.height]
            frames=[]
            for row,part in enumerate(pieces):
                columns,cut_method=view_cuts(image.crop((0,cuts[row],image.width,cuts[row+1])))
                for view in range(4):
                    rect=[columns[view],cuts[row],columns[view+1],cuts[row+1]]
                    tile=image.crop(rect);box=tile.getchannel('A').point(lambda a:255 if a>=128 else 0).getbbox()
                    record=dict(part=part,direction=DIRS[view],sourceRect=rect,viewCutMethod=cut_method,visible=bool(box))
                    if box:
                        b=[max(0,box[0]-3),max(0,box[1]-3),min(tile.width,box[2]+3),min(tile.height,box[3]+3)]
                        dest=HERE/'parts'/name/re.sub(r'[^a-zA-Z0-9._-]+','_',part)/(DIRS[view]+'.png');dest.parent.mkdir(parents=True,exist_ok=True)
                        tile.crop(b).save(dest)
                        record.update(file=str(dest.relative_to(HERE)),cropInCell=b)
                    frames.append(record)
            race=next((r for r in ['dark-elf','human','dwarf','elf','orc','goblin','kobold'] if name.startswith(r+'-')),None)
            material=name[len(race)+1:] if race else None
            record=dict(id=name,label=name.replace('-',' ').title(),source=source.name,sourceSize=list(image.size),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),parts=pieces,frames=frames,material=material,crafting=dict(onlyRace=race,enforcement='authoring rule; game crafting integration pending') if race else None,fitStatus='unregistered design draft; not production fitted',animationStatus='four standing design views only; no authored walk or attack states')
            if name=='dragon-helmets':record['approvedDesign']='User approved recognizable dragon-head helms; use these as helmet overrides for dragonhide and dragonbone.'
            record['missingViews']=[dict(part=f['part'],direction=f['direction']) for f in frames if not f['visible']]
            records.append(record)
    by_id={s['id']:s for s in records}
    for name,part in [('kobold-dragonhide','kobold-dragonhide.helmet'),('orc-dragonbone','orc-dragonbone.helmet')]:
        if name in by_id and 'dragon-helmets' in by_id:
            override=[dict(f,part='helmet',sourceSheet=by_id['dragon-helmets']['source']) for f in by_id['dragon-helmets']['frames'] if f['part']==part]
            by_id[name]['frames']=[f for f in by_id[name]['frames'] if f['part']!='helmet']+override
            by_id[name]['helmetOverride']='dragon-helmets: '+part
    if 'orc-dragonbone' in by_id and 'dragonbone-shoulder' in by_id:
        sheet=by_id['orc-dragonbone'];other=by_id['dragonbone-shoulder']
        override=[dict(f,part='shoulder-one',sourceSheet=other['source']) for f in other['frames']]
        sheet['frames']=[f for f in sheet['frames'] if f['part']!='shoulder-one']+override
        sheet['shoulderOverride']='dragonbone-shoulder: repaired North view'
    for sheet in records:
        sheet['missingViews']=[dict(part=f['part'],direction=f['direction']) for f in sheet['frames'] if not f['visible']]
        sheet['cropSha256']=hashlib.sha256(json.dumps(sheet['frames'],sort_keys=True).encode()).hexdigest()
    fit_path=HERE/'fit-results.json'
    if fit_path.exists():
        fits=json.loads(fit_path.read_text())
        for sheet in records:
            fit=fits.get(sheet['id'])
            if fit and fit['sourceSha256']==sheet['sha256'] and fit.get('cropSha256')==sheet['cropSha256']:sheet['fitPreview']=fit
    source_catalog=json.loads((HERE.parents[1]/'armory/catalog.json').read_text())
    mapping={}
    for sheet in records:
        for part in sheet['parts']:
            if part.startswith(('weapon.','shield.','helmet.','arms.','legs.','chest.','goa.')):mapping[part]=dict(sheet=sheet['id'],part=part)
    for design,sheet,part in [('chest.plate','human-iron','chest'),('legs.plate','human-iron','greave-left'),('feet.boots','human-leather','boot-left'),('chest.leather','human-leather','chest'),('arms.leather','human-leather','bracer-left'),('legs.leather','human-leather','greave-left'),('chest.robe','robe-colors','robe.blue')]:
        if sheet in by_id:mapping[design]=dict(sheet=sheet,part=part,notes='Class design represented by modular draft pieces; no game integration implied.')
    missing=[i['id'] for i in source_catalog['items'] if i['id'] not in mapping]
    coverage=dict(scope='63 modern drawable source designs; native art drafts only. Material/race combinations and animation states require separate fitting and authoring.',sourceDesigns=len(source_catalog['items']),mappedDesigns=len(source_catalog['items'])-len(missing),mapping=mapping,missing=missing)
    (HERE/'source-coverage.json').write_text(json.dumps(coverage,indent=2))
    catalog=dict(version=1,method='native imagegen redraws; source cells cut without repainting',rules=dict(racialCrafting='Only the named crafting race can craft each racial tradition. Wearer rules and body fit are separate.',silhouettes='Asymmetry, single/no shoulder guards, exotic mantles, harnesses, coats and wraps allowed.',pixelSpace='64x64 character fitting space; large generated sheets require registration before use.'),sourceCoverage=coverage,sheets=records,review=failures)
    (HERE/'catalog.json').write_text(json.dumps(catalog,indent=2))
    data=json.dumps(catalog,separators=(',',':'))
    (HERE/'index.html').write_text((HERE/'gallery.template.html').read_text().replace('/*DATA*/null',data))
    sample=ROOT/'Dungeon Master Sample';link=sample/'Fantasy Racial Gear Redraws.html'
    if not link.exists():link.symlink_to(__import__('os').path.relpath(HERE/'index.html',sample))
    print(json.dumps(dict(sheets=len(records),rows=sum(len(s['parts']) for s in records),views=sum(len(s['frames']) for s in records),review=failures)))


if __name__=='__main__':build()
