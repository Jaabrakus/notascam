#!/usr/bin/env python3
"""Run existing game regressions with a private compiler tree, tracking provenance."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game-root',type=Path,required=True);p.add_argument('--suite',choices=['bounds','orders','defense'],required=True);p.add_argument('--label',required=True);p.add_argument('--port',type=int,default=12198);a=p.parse_args()
 reportpath=a.game_root/'tests'/f'{a.label}-checks.json'
 if reportpath.exists():p.error('unique label required')
 sys.path.insert(0,str(a.game_root/'tools'))
 import check_combat
 check_combat.RUNTIME=ROOT/'runtime/macos-x64'
 import check_defense_bounds,check_easy_orders,check_defense
 runner={'bounds':check_defense_bounds,'orders':check_easy_orders,'defense':check_defense}[a.suite]
 source=ROOT/'runtime/macos-x64/compiler/DMStandard/_Standard.dm';compiler=source.parents[1]/'DMCompiler.dll';before={'compiler':sha(compiler),'standard':sha(source)}
 sys.argv=['check_'+a.suite,'--label',a.label,'--port',str(a.port)]
 try:runner.main()
 except SystemExit:pass
 report=json.loads(reportpath.read_text());report['compiler_before']=before;report['compiler_after']={'compiler':sha(compiler),'standard':sha(source)};report['compiler_stable']=report['compiler_before']==report['compiler_after'];report['compiler_path']=str(compiler);report['passed']=report['passed'] and report['compiler_stable'];reportpath.write_text(json.dumps(report,indent=2)+'\n');return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
