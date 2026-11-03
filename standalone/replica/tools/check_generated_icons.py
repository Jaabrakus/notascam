#!/usr/bin/env python3
"""Check icon()/fcopy DMI output against source direction/frame pixels, headlessly."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'runtime/macos-x64'
DIRS = ['south', 'north', 'east', 'west', 'southeast', 'southwest', 'northeast', 'northwest']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixel_hash(image):
    rgba = bytearray(image.convert('RGBA').tobytes())
    # Hidden RGB can legitimately change after an icon operation. Compare all
    # visible color channels and alpha; invisible color cannot change facing.
    for i in range(0, len(rgba), 4):
        if rgba[i + 3] == 0:
            rgba[i:i + 3] = b'\0\0\0'
    return hashlib.sha256(rgba).hexdigest()


def read_states(path, turn_clockwise=False):
    with Image.open(path) as image:
        description = image.info.get('Description', '')
        states, current, w, h = [], None, 32, 32
        for line in description.splitlines():
            match = re.match(r'\s*(\w+)\s*=\s*(.*)', line)
            if not match:
                continue
            key, value = match.groups()
            if key == 'state':
                current = {'name': json.loads(value), 'dirs': 1, 'frames': 1, 'movement': 0}
                states.append(current)
            elif current is None:
                if key == 'width': w = int(value)
                if key == 'height': h = int(value)
            elif key in ('dirs', 'frames', 'movement'):
                current[key] = int(value)
        offset = 0
        columns = image.width // w
        if not columns or image.width % w or image.height % h:
            raise ValueError('Invalid DMI sheet dimensions: ' + str(path))
        for state in states:
            state['cells'] = []
            for frame in range(state['frames']):
                for direction in range(state['dirs']):
                    index = offset + frame * state['dirs'] + direction
                    x, y = index % columns * w, index // columns * h
                    if y + h > image.height:
                        raise ValueError('Missing DMI frame: ' + str(path))
                    cell = image.crop((x, y, x + w, y + h))
                    if turn_clockwise:
                        cell = cell.transpose(Image.Transpose.ROTATE_270)
                    state['cells'].append(dict(frame=frame, direction=DIRS[direction], sha256=pixel_hash(cell)))
            offset += state['frames'] * state['dirs']
        return states


def synthetic(path, dirs, frames):
    size = 8
    image = Image.new('RGBA', (size * dirs, size * frames), (0, 0, 0, 0))
    for frame in range(frames):
        for direction in range(dirs):
            # Distinct hues for directions and distinct values for each frame.
            color = ((direction * 31 + 19) % 256, frame * 73 + 17, direction * 19 + frame * 7, 255)
            for y in range(size):
                for x in range(size):
                    image.putpixel((direction * size + x, frame * size + y), color)
    info = PngImagePlugin.PngInfo()
    info.add_text('Description', '# BEGIN DMI\nversion = 4.0\nwidth = 8\nheight = 8\nstate = ""\ndirs = %d\nframes = %d\ndelay = %s\n# END DMI\n' %
                  (dirs, frames, ','.join(str(i + 1) for i in range(frames))), zip=True)
    image.save(path, format='PNG', pnginfo=info)


def prepare(arena):
    cases = []
    for label, dirs, frames in [('four-directions', 4, 3), ('eight-directions', 8, 3),
                                ('one-direction-control', 1, 3), ('one-frame-control', 4, 1)]:
        synthetic(arena / (label + '.dmi'), dirs, frames)
        cases.append(dict(name=label, source=label + '.dmi', state='', mode='all'))
    cases += [dict(name='selected-east-control', source='four-directions.dmi', state='', mode='east'),
              dict(name='selected-frame-control', source='four-directions.dmi', state='', mode='frame'),
              dict(name='white-blend', source='four-directions.dmi', state='', mode='blend')]
    # A second state with a different direction/frame count exercises the
    # state offset, independently of correct ordering within the first state.
    synthetic(arena / 'second-state.dmi', 8, 2)
    multi = Image.new('RGBA', (28 * 8, 8))
    cursor = 0
    for source, dirs, frames in [('four-directions.dmi', 4, 3), ('second-state.dmi', 8, 2)]:
        with Image.open(arena / source) as image:
            for frame in range(frames):
                for direction in range(dirs):
                    multi.paste(image.crop((direction * 8, frame * 8, (direction + 1) * 8, (frame + 1) * 8)), (cursor * 8, 0))
                    cursor += 1
    info = PngImagePlugin.PngInfo()
    info.add_text('Description', '# BEGIN DMI\nversion = 4.0\nwidth = 8\nheight = 8\nstate = "first"\ndirs = 4\nframes = 3\nstate = "second"\ndirs = 8\nframes = 2\n# END DMI\n', zip=True)
    multi.save(arena / 'multiple-states.dmi', format='PNG', pnginfo=info)
    cases.append(dict(name='multiple-states', source='multiple-states.dmi', state=None, mode='all'))
    # Add asymmetric pixels so rotation cannot pass merely because each cell
    # was a solid color. Compare with independently rotated source rectangles.
    with Image.open(arena / 'four-directions.dmi') as image:
        turned_source = image.convert('RGBA')
        description = image.info['Description']
    for frame in range(3):
        for direction in range(4):
            turned_source.putpixel((direction * 8, frame * 8 + 1), (241, 73, 19, 255))
            turned_source.putpixel((direction * 8 + 5, frame * 8 + 7), (16, 35, 193, 127))
    info = PngImagePlugin.PngInfo()
    info.add_text('Description', description, zip=True)
    turned_source.save(arena / 'asymmetric.dmi', format='PNG', pnginfo=info)
    cases.append(dict(name='turn-90-animation', source='asymmetric.dmi', state='', mode='turn'))
    for name, asset, state in [('real-human', 'Humans.dmi', ''),
                               ('real-chestplate', 'MetalObjects.dmi', 'Metal ChestPlate')]:
        source = ROOT.parent / 'remastered/game/Icons' / asset
        shutil.copyfile(source, arena / asset)
        cases.append(dict(name=name, source=asset, state=state, mode='all',
                          original_source=str(source), original_sha256=sha(source)))
    lines = ['world', '\tNew()', '\t\t..()']
    for i, case in enumerate(cases):
        args = "'%s'" % case['source']
        if case['state'] is not None: args += ',' + json.dumps(case['state'])
        if case['mode'] == 'east': args += ',EAST'
        if case['mode'] == 'frame': args += ',0,2'
        lines.append('\t\tvar/icon/I%d = icon(%s)' % (i, args))
        if case['mode'] == 'blend': lines.append('\t\tI%d.Blend("#ffffff",ICON_MULTIPLY)' % i)
        if case['mode'] == 'turn': lines.append('\t\tI%d.Turn(90)' % i)
        lines.append('\t\tworld.log << "GENERATED_ICON|%s|copied=[fcopy(I%d,\"%s-generated.dmi\")]"' %
                     (case['name'], i, case['name']))
    lines.extend(['\t\tworld.log << "GENERATED_ICON|complete"', '\t\tshutdown()'])
    (arena / 'generated_icons.dm').write_text('\n'.join(lines) + '\n')
    (arena / 'generated_icons.dme').write_text('#include "generated_icons.dm"\n')
    return cases


def compare(arena, case):
    originals = [s for s in read_states(arena / case['source'], turn_clockwise=case['mode'] == 'turn')
                 if case['state'] is None or s['name'] == case['state']]
    generated_path = arena / (case['name'] + '-generated.dmi')
    actual_states = read_states(generated_path)
    mismatches, expected_count, actual_count = [], 0, 0
    movement_metadata_matches = True
    structure_matches = bool(originals) and len(originals) == len(actual_states)
    for original, actual_state in zip(originals, actual_states):
        movement_metadata_matches &= original['movement'] == actual_state['movement']
        expected = [dict(c) for c in original['cells']]
        if case['mode'] == 'east':
            expected = [{**c, 'direction': 'south'} for c in expected if c['direction'] == 'east']
        if case['mode'] == 'frame':
            expected = [{**c, 'frame': 0} for c in expected if c['frame'] == 1]
        actual = actual_state['cells']
        expected_count += len(expected)
        actual_count += len(actual)
        if case['state'] is None and original['name'] != actual_state['name']: structure_matches = False
        for index, (want, got) in enumerate(zip(expected, actual)):
            if want != got:
                matching_sources = [dict(frame=c['frame'], direction=c['direction'])
                                    for c in original['cells'] if c['sha256'] == got['sha256']]
                mismatches.append(dict(state=original['name'], index=index, expected=want, actual=got, actual_matches_source=matching_sources))
    return dict(name=case['name'], passed=structure_matches and expected_count == actual_count and not mismatches and movement_metadata_matches,
                movement_metadata_matches=movement_metadata_matches,
                expected_cells=expected_count, actual_cells=actual_count, mismatches=mismatches,
                expected_states=len(originals), actual_states=len(actual_states),
                source_sha256=sha(arena / case['source']), generated_sha256=sha(generated_path),
                original_source=case.get('original_source'), original_sha256=case.get('original_sha256'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-dir', type=Path, default=RUNTIME / 'server')
    parser.add_argument('--label', default='current')
    parser.add_argument('--port', type=int, default=12179)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.label): parser.error('Invalid label')
    arena = ROOT / 'reference/generated-icons' / args.label
    arena.mkdir(parents=True, exist_ok=True)
    for old in arena.glob('*-generated.dmi'): old.unlink()
    cases = prepare(arena)
    dotnet = RUNTIME / 'dotnet/dotnet'
    env = dict(os.environ, DOTNET_ReadyToRun='0')
    runtime_dll = args.server_dir / 'Resources/Assemblies/OpenDreamRuntime.dll'
    runtime_hash = sha(runtime_dll)
    with (arena / 'compile.log').open('w') as log:
        subprocess.run([str(dotnet), str(RUNTIME / 'compiler/DMCompiler.dll'), str(arena / 'generated_icons.dme')],
                       env=env, stdout=log, stderr=subprocess.STDOUT, timeout=90, check=True)
    with tempfile.TemporaryDirectory(prefix='dm-generated-icons-') as data, (arena / 'server.log').open('w') as log:
        process = subprocess.Popen([str(dotnet), str(args.server_dir / 'Robust.Server.dll'), '--data-dir', data,
                                    '--cvar', 'opendream.json_path=' + str(arena / 'generated_icons.json'),
                                    '--cvar', 'opendream.topic_port=' + str(args.port + 13500),
                                    '--cvar', 'net.port=' + str(args.port), '--cvar', 'net.bindto=127.0.0.1',
                                    '--cvar', 'status.enabled=false', '--cvar', 'hub.advertise=false',
                                    '--cvar', 'auth.mode=0', '--cvar', 'game.auto_pause_empty=false'],
                                   env=env, stdout=log, stderr=subprocess.STDOUT, cwd=arena)
        try:
            process.wait(timeout=45)
        except subprocess.TimeoutExpired:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    output = (arena / 'server.log').read_text(errors='replace')
    errors = re.findall(r'^.*(?:\[(?:ERRO|FATL)\]|runtime error|Exception occurred).*$', output, flags=re.I | re.M)
    complete = 'GENERATED_ICON|complete' in output
    results = [compare(arena, case) for case in cases] if complete else []
    originals_unchanged = all(sha(Path(c['original_source'])) == c['original_sha256'] for c in cases if 'original_source' in c)
    report = dict(passed=complete and not errors and all(r['passed'] for r in results) and originals_unchanged,
                  runtime_sha256=runtime_hash, runtime_unchanged_during_run=runtime_hash == sha(runtime_dll),
                  fixture_sha256=sha(arena / 'generated_icons.dm'), original_art_unchanged=originals_unchanged,
                  completed=complete, errors=errors, cases=results,
                  comparison='Actual headless icon()/fcopy output parsed frame-major, compared to original direction/frame pixels',
                  exclusions=['Movement-only activation/animation scheduling are checked by check_movement_animation.py; loop/rewind metadata and GUI rendering remain separate checks'])
    report['passed'] = report['passed'] and report['runtime_unchanged_during_run']
    target = ROOT / 'reports' / ('generated-icons-' + args.label + '-checks.json')
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({**{k: v for k, v in report.items() if k != 'cases'},
                      'cases': [{'name': r['name'], 'passed': r['passed'], 'mismatched_cells': len(r['mismatches'])}
                                for r in results], 'report': str(target)}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
