#!/usr/bin/env python3
"""Match private BYOND RenderIcon captures to unchanged original sprite cells."""
import json
from pathlib import Path
import re
import statistics
from PIL import Image
from check_generated_icons import read_states,pixel_hash

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reference/dmi-rewind-audit'


def captures(directory,label,source,state=None):
    candidates=[]
    for item in read_states(directory/source):
        if state is not None and item['name']!=state:continue
        for cell in item['cells']:
            if cell['direction']=='south':candidates.append((item['name'],cell['frame'],cell['sha256']))
    rows=[];transitions=[]
    pattern=re.compile(r'REWIND\|sample\|'+re.escape(label)+r'\|(\d+)\|([.\d]+)\|([.\d]+)\|1')
    for match in pattern.finditer((directory/'server.log').read_text()):
        index,start,end=match.groups()
        with Image.open(directory/(label+'-'+index+'.dmi'))as image:digest=pixel_hash(image)
        matches=[dict(state=s,frame=f)for s,f,h in candidates if h==digest]
        row=dict(sample=int(index),start_deciseconds=float(start),end_deciseconds=float(end),matches=matches)
        rows.append(row)
        if not transitions or transitions[-1]['matches']!=matches:transitions.append(row)
    durations={}
    for a,b in zip(transitions,transitions[1:]):
        if len(a['matches'])!=1:continue
        key=str(a['matches'][0]['frame'])
        durations.setdefault(key,[]).append(b['start_deciseconds']-a['start_deciseconds'])
    return dict(samples=rows,transitions=transitions,
        median_durations_deciseconds={k:statistics.median(v)for k,v in durations.items()})


def main():
    normal=BASE/'native-byond';edges=BASE/'native-edges-byond'
    data={
        'uniform':captures(normal,'uniform','uniform-source.dmi'),
        'unequal':captures(normal,'unequal','unequal-source.dmi'),
        'original':captures(normal,'original','tapestry.dmi','Retribution'),
        'one':captures(edges,'one','one-source.dmi'),
        'two':captures(edges,'two','two-source.dmi'),
        'flash':captures(edges,'flash','flash-source.dmi'),
    }
    checks={}
    for label,result in data.items():
        checks[label+'_all_captures_match_original_visible_pixels']=bool(result['samples'])and all(r['matches']for r in result['samples'])
    for label in ('uniform','unequal'):
        frames=[r['matches'][0]['frame']for r in data[label]['transitions']if r['matches']]
        cycles=sum(frames[i:i+5]==[0,1,2,1,0]for i in range(len(frames)-4))
        checks[label+'_repeated_forward_reverse_cycles']=cycles>=3
        expected={'0':5,'1':5,'2':5}if label=='uniform'else{'0':3,'1':5,'2':8}
        checks[label+'_each_displayed_frame_uses_own_delay']=all(abs(data[label]['median_durations_deciseconds'].get(k,-99)-v)<=1 for k,v in expected.items())
    frames=[r['matches'][0]['frame']for r in data['original']['transitions']if r['matches']]
    checks['original_tapestry_visibly_reverses']=sum(a-b==1 and a not in (0,44)for a,b in zip(frames,frames[1:]))>=20
    checks['one_frame_stays_static']=len(data['one']['transitions'])==1
    checks['two_frame_own_endpoint_delays']=all(abs(data['two']['median_durations_deciseconds'].get(k,-99)-v)<=1 for k,v in {'0':3,'1':8}.items())
    flash=[r['matches'][0]for r in data['flash']['transitions']if r['matches']]
    checks['flick_ignores_rewind_and_restores_base']=flash==[dict(state='flash',frame=0),dict(state='flash',frame=1),dict(state='flash',frame=2),dict(state='',frame=0)]
    start=re.search(r'REWIND\|flick-start\|([.\d]+)',(edges/'server.log').read_text())
    returned=data['flash']['transitions'][-1]['start_deciseconds']
    checks['flick_finishes_after_forward_delays_only']=bool(start)and abs(returned-float(start[1])-16)<=1
    for label,directory in [('normal',normal),('edges',edges)]:
        run=json.loads((directory/'run.json').read_text())
        checks[label+'_completed_no_input_no_errors_stable_sources']=run['passed']
    report=dict(reference='BYOND 516.1655 server and private DreamSeeker RenderIcon; exact client binary hash in run.json',
        pixel_comparison='Visible RGBA, with hidden RGB normalized only for alpha-zero pixels',
        clock_limit='Server request times are quantized and can jitter; turnaround order is exact, delay checks use medians of repeated cycles.',
        conclusions=dict(looping_sequence='0..N-1,N-2..1',endpoint_repetition=False,
            reverse_delay='The delay of the displayed source frame',flick='Forward only, then base appearance'),
        checks=checks,passed=all(checks.values()),cases=data)
    (BASE/'native-reference-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    directory=BASE/'native-phase-byond'
    if (directory/'run.json').exists():
        phase={label:captures(directory,label,source)for label,source in [
            ('early','early-source.dmi'),('shared','early-source.dmi'),
            ('unique','unique-source.dmi'),('switched','switched-source.dmi')]}
        early={row['sample']:row for row in phase['early']['samples']}
        events=dict((name,float(t))for name,t in re.findall(r'REWIND\|phase\|([^|\n]+)\|([.\d]+)',(directory/'server.log').read_text()))
        settled=events['switched-motion']+5
        phase_checks={'no_input_errors_or_source_changes':json.loads((directory/'run.json').read_text())['passed']}
        comparison={}
        for label in ('shared','unique','switched'):
            rows=[r for r in phase[label]['samples']if r['start_deciseconds']>=settled]
            exact=nearby=0
            for row in rows:
                if not row['matches']:continue
                value=row['matches'][0]['frame'];index=row['sample']
                if early[index]['matches'][0]['frame']==value:exact+=1
                if any(early[i]['matches'][0]['frame']==value for i in (index-1,index,index+1)if i in early):nearby+=1
            comparison[label]=dict(samples=len(rows),same_iteration_matches=exact,within_neighboring_early_capture=nearby)
            phase_checks[label+'_joins_existing_cycle_within_capture_interval']=len(rows)>=50 and nearby==len(rows)
        phase_checks['shared_resource_exact_same_iteration']=comparison['shared']['same_iteration_matches']==comparison['shared']['samples']
        phase_report=dict(checks=phase_checks,passed=all(phase_checks.values()),events=events,comparison=comparison,cases=phase,
            conclusion='Late shared and distinct resources and restored appearances join the ongoing infinite-loop cycle rather than restart it.',
            limitations='Newly loaded resources can briefly show frame0. Sequential RenderIcon calls straddle frame boundaries; distinct resources agree within one neighboring capture. No claim of cross-client absolute-clock phase parity.')
        (BASE/'native-phase-checks.json').write_text(json.dumps(phase_report,indent=2)+'\n')
        if not phase_report['passed']:raise AssertionError('Phase reference review failed')
    print(json.dumps({k:v for k,v in report.items()if k!='cases'},indent=2));return 0 if report['passed']else 1


if __name__=='__main__':raise SystemExit(main())
