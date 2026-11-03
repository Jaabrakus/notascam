from pathlib import Path
import argparse,hashlib,json,re,shutil,tempfile
import check_combat as runner
B=Path(__file__).resolve().parents[1];runner.ROOT=B;runner.RUNTIME=B/'runtime' if (B/'runtime/server').exists() else B.parent/'replica/runtime/macos-x64'
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--candidate',action='store_true',help='Compatibility flag; current game is the default');p.add_argument('--baseline',type=Path);p.add_argument('--port',type=int,default=12542);a=p.parse_args();source=a.baseline if a.baseline else B/'game';fixture_source=B/'tests/ordinary_inventory.dm';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
fixture_hash=sha(fixture_source); source_hashes={str(f.relative_to(source)):sha(f)for f in source.rglob('*')if f.is_file()}
with tempfile.TemporaryDirectory(prefix='dm-ordinary-inventory-')as temp:
 world=Path(temp)/'world';shutil.copytree(source,world);s=(world/'Code/World.dm').read_text(encoding='latin-1');start,end=s.index('\tNew()'),s.index('\nvar/Season');(world/'Code/World.dm').write_text(s[:start]+'\tNew()\n\t\tspawn(0) InventoryRun()\n'+s[end:],encoding='latin-1');dme=re.sub(r'^#include .*\.dmm"\s*$','',(world/'Cave Crawlers.dme').read_text(encoding='latin-1'),flags=re.M);fixture=world/'ordinary_inventory.dme';fixture.write_text(dme+'\n#include "ordinary_inventory.dm"\n',encoding='latin-1');shutil.copy2(fixture_source,world/'ordinary_inventory.dm')
 if not a.baseline:
  file=world/'Code/Remastered/InventoryActions.dm';s=file.read_text(encoding='latin-1');needle='return input(controller,"What would you like to do with the [src]?","Choose",null) in menu';assert s.count(needle)==1;s=s.replace(needle,'return controller:InventoryAuditChoice(src,loc,menu)');file.write_text(s,encoding='latin-1')
 else:
  needle='var/Result=input("What would you like to do with the [src]?","Choose",null)in menu'
  for name in ['Food.dm','Item Procs.dm']:
   file=world/'Code/Items'/name;s=file.read_text(encoding='latin-1');assert s.count(needle)==1;s=s.replace(needle,'var/Result=usr:InventoryAuditChoice(src,M,menu)');file.write_text(s,encoding='latin-1')
 file=world/'Code/Remastered/SelectedActions.dm';s=file.read_text(encoding='latin-1');needle='return alert(recipient, message, title, "Yes", "No")';assert s.count(needle)==1;s=s.replace(needle,'return InventoryCrownReply(src,recipient)');file.write_text(s,encoding='latin-1')
 runner.run_world(world,fixture,a.label,45,prefix='INVENTORY',port=a.port)
 report=B/'tests'/(a.label+'-checks.json');r=json.loads(report.read_text());r['fixture_sha256']=fixture_hash;r['source_sha256']=source_hashes;r['source_stable']=fixture_hash==sha(fixture_source) and source_hashes=={str(f.relative_to(source)):sha(f)for f in source.rglob('*')if f.is_file()};r['scope']='Private real Human/Orc food/equipment modal audit. Only carried-choice and nested Crown confirmation input delivery replaced with yielding scripted replies; original carried-item DblClick and low-level effects unchanged. No normal save or native input.';report.write_text(json.dumps(r,indent=2)+'\n')

raise SystemExit(0 if r.get("passed") and r["source_stable"] else 1)
