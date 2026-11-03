#!/usr/bin/env python3
"""Verify individual workshop/recipe costs from a retained native Work trace.
This is post-run analysis only; it never starts a game or rewrites its input.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    output=args.output or args.report.with_name(args.report.stem.replace('-checks','')+'-effects.json')
    if output.exists():parser.error('output exists; preserve existing evidence or choose another path')
    data=json.loads(args.report.read_text());actor=data['actor'];events=[]
    def worker(sample):return next(u for u in sample['units'] if u['ref']==actor)
    def compact(sample):
        unit=worker(sample)
        return dict(time=sample['time'],wood_alive=sum(w['alive'] for w in sample['woods']),weight=unit['weight'],craft_skill=unit['craftSkill'],queue=unit['production'],products=sample['products'],workshops=sample['workshops'],status=unit['workStatus'])
    for before,after in zip(data['observations'],data['observations'][1:]):
        if len(after['workshops'])!=len(before['workshops']):
            events.append(dict(kind='construction',before=compact(before),after=compact(after)))
        elif len(after['workshops']) and len(worker(after)['production'])<len(worker(before)['production']):
            events.append(dict(kind=worker(before)['production'][0],before=compact(before),after=compact(after)))
    checks={}
    kinds=[e['kind'] for e in events]
    expected={'bucket':('/obj/Items/Shafts/WoodenBucket',7),'spike':('/obj/Items/Traps/Spikes/WoodenSpike',5),'spade':('/obj/Items/Shafts/WoodenSpade',5)}
    for kind in ['construction',*expected]:
        candidates=[e for e in events if e['kind']==kind]
        valid=len(candidates)==1
        if valid:
            before,after=candidates[0]['before'],candidates[0]['after']
            valid=before['wood_alive']-after['wood_alive']==1 and before['weight']==105 and after['weight']==85
            if kind=='construction':
                valid=valid and before['craft_skill']==25 and after['craft_skill']==26 and before['queue']==after['queue']==['bucket','spike','spade'] and not before['products'] and not after['products'] and not before['workshops'] and len(after['workshops'])==2
            else:
                previous={p['token'] for p in before['products']}
                created=[p for p in after['products'] if p['token'] not in previous]
                valid=valid and len(created)==1 and (created[0]['type'],created[0]['weight'])==expected[kind] and after['craft_skill']==before['craft_skill']+.5 and after['queue']==before['queue'][1:]
        checks[kind+'_original_cost_and_skill']=bool(valid)
    result=dict(scope=__doc__,source_report=str(args.report.resolve()),source_report_sha256=sha(args.report),analyzer_sha256=sha(Path(__file__)),source_report_passed=data['passed'],checks=checks,events=events,sequence=kinds,passed=data['passed'] and kinds==['construction','bucket','spike','spade'] and all(checks.values()),limitations=['Post-run analysis of recorded actual native object states; no additional game run.', 'Original Human woodcraft25 naturally gives100% recipe success; this trace does not exercise failed crafting.'])
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'checks':checks,'output':str(output)},indent=2))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
