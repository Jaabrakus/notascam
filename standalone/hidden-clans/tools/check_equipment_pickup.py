from pathlib import Path
import sys,shutil,re,tempfile,json,hashlib,zipfile,argparse
import check_combat
ROOT=Path(__file__).resolve().parents[1]
check_combat.ROOT=ROOT
if (ROOT/"runtime/server").exists():check_combat.RUNTIME=ROOT/"runtime"
p=argparse.ArgumentParser();p.add_argument("--label",required=True);p.add_argument("--port",type=int,default=12543);args=p.parse_args();label=args.label
assert re.fullmatch(r'[A-Za-z0-9_-]+',label)
assert not (ROOT/'tests'/f'{label}-checks.json').exists()
files=[ROOT/'game/Code/Remastered/Orders.dm',ROOT/'tests/equipment_orders.dm',Path(__file__)]
hashes=lambda:{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
before=hashes()
with tempfile.TemporaryDirectory(prefix="dm-equipment-orders-") as t:
 w=Path(t)/"world";shutil.copytree(ROOT/"game",w)
 p=w/"Code/World.dm";s=p.read_text(encoding="latin-1");a=s.index("\tNew()");b=s.index("\nvar/Season",a)
 p.write_text(s[:a]+"\tNew()\n\t\tlog=file(\"ErrorLog.txt\")\n\t\tspawn(1) EquipmentRun()\n"+s[b:],encoding="latin-1")
 d=re.sub(r'^#include .*\.dmm"\s*$','',(w/"Cave Crawlers.dme").read_text(encoding="latin-1"),flags=re.M)
 shutil.copy2(ROOT/"tests/equipment_orders.dm",w/"equipment_orders.dm")
 f=w/"equipment.dme";f.write_text(d+'\n#include "equipment_orders.dm"\n',encoding="latin-1")
 with zipfile.ZipFile(ROOT/'tests'/f'{label}-source.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for p in sorted(w.rglob('*')):
   if p.is_file():z.write(p,str(p.relative_to(w)))
 ok=check_combat.run_world(w,f,label,60,prefix="EQUIPMENT",port=args.port)
(ROOT/'tests'/f'{label}-inputs.json').write_text(json.dumps(dict(before=before,after=hashes(),unchanged=before==hashes()),indent=2)+'\n')
raise SystemExit(0 if ok and before==hashes() else 1)
