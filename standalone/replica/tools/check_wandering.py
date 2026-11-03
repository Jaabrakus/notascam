#!/usr/bin/env python3
"""Compare open-terrain wandering distributions; not a claim of edge parity."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import parse_qsl

ROOT=Path(__file__).resolve().parents[1]
# Declared before collecting/evaluating the candidate samples: 10,000 per facing,
# 2 percentage points per direction and 3 points total variation per facing.
MAX_DIRECTION_DIFFERENCE=.02
MAX_TOTAL_VARIATION=.03

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',action='store_true')
    parser.add_argument('--server-dir',type=Path,default=ROOT/'runtime/macos-x64/server')
    args=parser.parse_args()
    command=[sys.executable,str(ROOT/'tools/check_parity.py'),'wander_distribution','--server-dir',str(args.server_dir)]
    if args.reference:command.append('--reference')
    with (ROOT/'reports/wander-distribution-run.log').open('w') as log:
        run=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    raw=json.loads((ROOT/'reports/wander_distribution-parity.json').read_text())
    if run.returncode not in (0,1) or raw['errors'] or raw['actual'][-1:]!=['PARITY|complete']:
        raise RuntimeError('Wandering sample run failed')
    def parse(lines):
        result={}
        for line in lines:
            if not line.startswith('PARITY|distribution|'):continue
            _,_,facing,counts=line.split('|')
            result[facing]={k:int(v) for k,v in parse_qsl(counts)}
        return result
    expected=parse(raw['expected']);actual=parse(raw['actual']);scenarios=[]
    for facing in ('1','5','4','6','2','10','8','9'):
        before=expected[facing];after=actual[facing]
        if sum(before.values())!=10000 or sum(after.values())!=10000:
            raise RuntimeError('Incomplete sample counts')
        differences={k:abs(before[k]-after[k])/10000 for k in before}
        variation=sum(differences.values())/2
        scenarios.append(dict(facing=int(facing),reference=before,actual=after,total_variation=variation,
            maximum_direction_difference=max(differences.values()),passed=variation<=MAX_TOTAL_VARIATION and max(differences.values())<=MAX_DIRECTION_DIFFERENCE))
    result=dict(passed=all(s['passed'] for s in scenarios),runtime_sha256=raw['runtime_sha256'],
        fixture_sha256=raw['fixture_sha256'],reference_log_sha256=raw['reference_log_sha256'],reference_version=raw['reference_version'],
        samples_per_facing=10000,tolerances=dict(maximum_direction_difference=MAX_DIRECTION_DIFFERENCE,maximum_total_variation=MAX_TOTAL_VARIATION),
        scenarios=scenarios,exact_sequence_match=False,
        exclusions=['Open terrain only. Original 5x5 edge-following is still unmatched.',
                    'The original wandering seed is not exposed by rand_seed; distribution matching does not certify identical sequences.'])
    (ROOT/'reports/wandering-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
