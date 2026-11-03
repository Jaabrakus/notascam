#!/usr/bin/env python3
"""Check the narrow source-direction Blend fix against retained BYOND outputs.

Audits all seven modes but only claims exact arithmetic for the six supported
modes in the original-art, single-frame direction matrix. Deferred expansion,
OR arithmetic, and partial-alpha color behavior stay explicitly separate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cells(states):
    return {(s['name'], s['movement'], c['frame'], c['direction']): c['sha256']
            for s in states for c in s['cells']}


def cell_pixels(path, direction):
    with Image.open(path) as im:
        return [p if p[3] else (0, 0, 0, 0) for p in im.convert('RGBA').crop(
            (direction * 32, 0, (direction + 1) * 32, 32)).getdata()]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before', default='before')
    p.add_argument('--candidate', default='candidate')
    p.add_argument('--real-before', default='blend-before')
    p.add_argument('--real-candidate', default='blend-candidate')
    p.add_argument('--label', default='source-direction')
    args = p.parse_args()
    for value in vars(args).values():
        if not re.fullmatch(r'[a-z0-9-]+', value):
            p.error('Use simple labels')
    files = {k: ROOT / 'reports' / ('icon-blend-' + v + '.json') for k, v in
             [('before', args.before), ('candidate', args.candidate)]}
    files.update({k: ROOT / 'reports' / ('icon-fallback-' + v + '.json') for k, v in
                  [('real_before', args.real_before), ('real_candidate', args.real_candidate)]})
    data = {k: json.loads(v.read_text()) for k, v in files.items()}
    checks = {k + '_audit_completed': v['audit_completed'] for k, v in data.items()}
    before = {c['id']: c for c in data['before']['cases']}
    cases = data['candidate']['cases']
    checks['same_114_cases'] = len(cases) == len(before) == 114 and set(before) == {c['id'] for c in cases}
    checks['same_original_art'] = data['before']['original_art'] == data['candidate']['original_art']
    checks['same_real_art_and_fixture'] = all(data['real_before'][k] == data['real_candidate'][k]
                                            for k in ('art_sha256', 'fixture_sha256', 'observations'))
    checks['same_candidate_runtime_for_matrix_and_real_game'] = data['candidate']['runtime_sha256'] == data['real_candidate']['runtime_sha256']
    eligible = []
    deferred = []
    for c in cases:
        name = c['id']
        b = before[name]
        checks[name + '_inputs_match_oracle_and_baseline'] = c['inputs'] == b['inputs'] and all(i['matches'] for i in c['inputs'].values())
        checks[name + '_reference_unchanged'] = c['reference'] == b['reference']
        # None of the destination metadata/shape or pixel arithmetic changed.
        checks[name + '_metadata_preserved'] = [dict(s, cells=[]) for s in c['replacement']] == [dict(s, cells=[]) for s in b['replacement']]
        actual, prior = cells(c['replacement']), cells(b['replacement'])
        if c['scope'] == 'color-control':
            checks[name + '_color_behavior_preserved'] = actual == prior
            deferred.append(name)
            continue
        source = c['inputs']['source']['replacement'][0]
        source_directions = {x['direction'] for x in source['cells']}
        checks[name + '_existing_source_directions_preserved'] = all(actual.get(key) == value for key, value in prior.items() if key[3] in source_directions)
        if c['scope'] == 'frames-deferred':
            deferred.append(name)
            continue
        destination = c['inputs']['destination']['replacement'][0]
        if destination['dirs'] < source['dirs']:
            checks[name + '_destination_expansion_unchanged'] = actual == prior
            deferred.append(name)
        elif c['mode'] != 'OR':
            checks[name + '_exact_reference_pixels'] = c['matches']
            eligible.append(name)
        else:
            deferred.append(name)
    checks['all_72_supported_direction_cases_covered'] = len(eligible) == 72
    checks['baseline_demonstrates_missing_source_directions'] = any(not before[name]['matches'] for name in eligible)
    # Real MakeBody remains unchanged and uses the actual original assets.
    # The female result is intentionally recorded as a partial improvement;
    # missing-state and destination expansion are not quietly called exact.
    real_root = ROOT / 'reference/icon-fallback-audit'
    real = []
    for path in sorted((real_root / args.real_candidate / 'replacement/outputs').glob('*-body.dmi')):
        rows = []
        for direction, name in enumerate(('south', 'north', 'east', 'west')):
            current = cell_pixels(path, direction)
            previous = cell_pixels(real_root / args.real_before / 'replacement/outputs' / path.name, direction)
            expected = cell_pixels(real_root / args.real_candidate / 'byond/outputs' / path.name, direction)
            bd = sum(a != b for a, b in zip(previous, expected))
            cd = sum(a != b for a, b in zip(current, expected))
            key = path.stem + '_' + name
            if not bd:
                checks[key + '_exact_control_preserved'] = cd == 0
            else:
                checks[key + '_fewer_mismatched_pixels'] = cd < bd
            rows.append(dict(direction=name, before_mismatched_pixels=bd,
                             candidate_mismatched_pixels=cd,
                             previously_correct_pixels_changed=sum(b == r and a != r for a, b, r in zip(current, previous, expected))))
        real.append(dict(name=path.stem, frames=rows))
    checks['all_seven_real_bodies_checked'] = len(real) == 7
    result = dict(passed=all(checks.values()), checks=checks, runtime_sha256=data['candidate']['runtime_sha256'],
                  evidence={k: dict(path=str(v), sha256=sha(v)) for k, v in files.items()},
                  eligible_cases=eligible, deferred_cases=deferred, real_bodies=real,
                  limitation='Source direction fallback only. Destination/frame expansion, missing-state constructors, OR arithmetic and partial-alpha arithmetic remain separate. Female corpses improve but do not fully match; one opaque east/west pixel per female control changes away from reference while total error decreases.')
    target = ROOT / 'reports' / ('icon-blend-' + args.label + '-checks.json')
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(report=str(target), passed=result['passed'], checks=len(checks),
                          failures=[k for k, v in checks.items() if not v]), indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
