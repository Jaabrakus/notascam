from pathlib import Path
from datetime import datetime,timezone
import json,secrets,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;JOBS=ROOT/'sprite-engine/jobs'
source=ROOT/'hybrids/references/Vampire-approved-flight.png';result=HERE/'Vampire-flight-approved-north-fixed.png'
from PIL import Image
w=Image.open(source).height
index=ROOT/'sprite-engine/remaining-races-jobs.json';entries=json.loads(index.read_text());previous=next(e for e in entries if e['race']=='VampireFly')
if previous.get('approved_north_only'):print(previous['url']);raise SystemExit
identifier=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-')+secrets.token_hex(4);folder=JOBS/identifier;folder.mkdir()
for filename,path in [('input-original.png',source),('input-sheet.png',source),('style-reference.png',ROOT/'sprite-engine/jobs/20261029-214924-9587fb64/result.png'),('result.png',result)]:shutil.copyfile(path,folder/filename)
spec=dict(format='dungeon-master.sprite-redraw',version=1,name='VampireFly · approved design · north wings corrected',kind='character',source=dict(filename=source.name,frameWidth=w,frameHeight=w,state='Fly appearance',movement=0,delays=[2],cells=[dict(column=d,row=0,direction=['South','North','East','West'][d],frame=0,sourceCell=d,sourceRect=[d*w,0,w,w]) for d in range(4)]),output=dict(columns=4,rows=1,frameWidth=64,frameHeight=64,directionOrder=['South','North','East','West'],transparent=True),style=dict(reference='style-reference.png',name='User-approved first Vampire design'),notes='Only North changed. Other three RGBA views preserved exactly. One approved appearance per direction; complete flying animation pending.',instructions='Use the approved first Vampire flying row. Edit only North wing layering; preserve other views. Do not replace the character design.')
(folder/'request.json').write_text(json.dumps(spec,indent=2));(folder/'request.md').write_text(spec['notes'])
backup=index.with_name('remaining-races-jobs-before-approved-vampire.json')
if not backup.exists():shutil.copyfile(index,backup)
for e in entries:
 if e['race']=='VampireFly':e.update(id=identifier,path=str(folder),source=str(source),cells=4,url='http://127.0.0.1:8876/?job='+identifier,approved_north_only=True)
index.write_text(json.dumps(entries,indent=2));(HERE/'vampire-job.json').write_text(json.dumps(dict(id=identifier,path=str(folder),url='http://127.0.0.1:8876/?job='+identifier),indent=2));print('Published',identifier)
