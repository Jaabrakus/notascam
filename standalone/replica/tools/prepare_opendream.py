#!/usr/bin/env python3
"""Stage syntax adaptations from the frozen original; never alter source/.

These transformations are compatibility candidates. Gameplay equivalence still
requires comparison with the original BYOND runtime.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from compact_conditionals import compact_else_heads, split_outer_if

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent/'tools'))
from legacy_dmi import decode as decode_legacy


def prepare():
    baseline = json.loads((ROOT/'reports/source-baseline.json').read_text())
    for entry in baseline:
        path = ROOT/'source'/entry['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'Frozen source differs from baseline: {entry["path"]}')
    target = ROOT/'opendream'
    shutil.copytree(ROOT/'source', target, dirs_exist_ok=True)
    changes = []
    for path in target.rglob('*.dm'):
        raw = path.read_bytes()
        source_lines = raw.decode('latin-1').splitlines()
        else_heads = compact_else_heads(source_lines)
        out, scopes = [], []
        file_changes = []
        for number, line in enumerate(source_lines, 1):
            indent = len(line) - len(line.lstrip('\t'))
            body = line.lstrip('\t')
            if body.strip():
                scopes = [depth for depth in scopes if indent > depth]
            extra = len(scopes)
            rendered = '\t' * extra + line
            if path.name == 'plugin.dm' and 'O.vars[W]=(Y==' in body:
                rendered = '\t' * (indent+extra) + 'O.vars[W] = (Y == "num") ? text2num(P) : ((Y == "type") ? text2path(P) : ((Y == "ref") ? locate(P) : (I ? I : P)))'
            # Same-indent else belongs to the outer compact control in BYOND.
            # Preserve that binding and the indentation of its entire body.
            # All structural forms are compared in the branching fixture.
            if number in else_heads:
                first, tail = split_outer_if(body)
                rendered = '\t'*(indent+extra)+first+'\n'+'\t'*(indent+extra+1)+tail
                scopes.append(indent)
            match = re.search(r'\bswitch\([^\n)]*\)\s+(?=if\()', body)
            if match and number not in else_heads:
                cut = match.end()
                rendered = '\t' * (indent+extra) + body[:cut].rstrip() + '\n' + '\t' * (indent+extra+1) + body[cut:]
                scopes.append(indent)
            elif re.match(r'^(Down|Up|GoldNeckGuard|MetalNeckGuard)\s+(icon_state|icon)\s*=', body):
                subtype, assignment = body.split(None, 1)
                rendered = '\t' * (indent+extra) + subtype + '\n' + '\t' * (indent+extra+1) + assignment
            if rendered != line:
                file_changes.append({'path': str(path.relative_to(target)), 'source_line': number,
                                     'before': line, 'after': rendered})
            out.append(rendered)
        if file_changes:
            newline = '\r\n' if b'\r\n' in raw else '\n'
            path.write_bytes((newline.join(out)+newline).encode('latin-1'))
            changes.extend(file_changes)
    (ROOT/'reports/opendream-syntax-adaptations.json').write_text(json.dumps(changes, indent=2))
    resource_changes = []
    for path in target.rglob('*.dmi'):
        original = path.read_bytes()
        if original.startswith(b'\x04DMI'):
            converted = decode_legacy(original)
            path.write_bytes(converted)
            resource_changes.append({'path': str(path.relative_to(target)),
                                     'original_sha256': hashlib.sha256(original).hexdigest(),
                                     'png_sha256': hashlib.sha256(converted).hexdigest(),
                                     'conversion': 'legacy DMI pixels, palette, names, directions, frames and delays to PNG-backed DMI'})
    # Sounds/P1-P3.wav are MP3 data under a .wav name. BYOND's audio library plays
    # them by content; the replacement client reads only RIFF WAV and Ogg, so the
    # staged copy gets the same audio decoded to PCM WAV by macOS afconvert.
    sound_changes = []
    for path in sorted(target.rglob('*.wav')):
        original = path.read_bytes()
        # Only MP3 content (ID3 tag or MPEG frame sync). The unused root
        # "Futurama Soundtrack.wav" holds Ogg Vorbis data and is left as supplied.
        if not (original[:3] == b'ID3' or (original[0] == 0xFF and original[1] & 0xE0 == 0xE0)):
            continue
        source = path.with_name(path.stem + '.decode.mp3')
        decoded = path.with_name(path.stem + '.decode.wav')
        try:
            source.write_bytes(original)
            subprocess.run(['/usr/bin/afconvert', '-f', 'WAVE', '-d', 'LEI16', str(source), str(decoded)],
                           check=True, capture_output=True)
            converted = decoded.read_bytes()
        finally:
            source.unlink(missing_ok=True)
            decoded.unlink(missing_ok=True)
        path.write_bytes(converted)
        sound_changes.append({'path': str(path.relative_to(target)),
                              'original_sha256': hashlib.sha256(original).hexdigest(),
                              'wav_sha256': hashlib.sha256(converted).hexdigest(),
                              'conversion': 'MP3 content in a .wav file decoded to 16-bit PCM WAV (afconvert)'})
    (ROOT/'reports/opendream-sound-adaptations.json').write_text(json.dumps(sound_changes, indent=2))
    # OpenDream skips legacy .dms files. Carry over the exact command strings
    # into the already-used .dmf macro group; retain the DMS file for auditing.
    macro_text = (target/'BackGrounds.dms').read_text(encoding='latin-1')
    macros = re.findall(r'^\s*(\S+)\s+return\s+"([^"]+)"', macro_text, re.M)
    skin = target/'skin.dmf'
    skin_text = skin.read_bytes().decode('latin-1')
    newline = '\r\n' if '\r\n' in skin_text else '\n'
    entries = []
    for key, command in macros:
        entries.append(newline.join(['\telem ', f'\t\tname = "{key.upper()}"',
                                     f'\t\tcommand = "{command}"', '\t\tis-disabled = false', '']))
    skin.write_bytes(skin_text.replace('menu "menu"', newline.join(entries) + newline + 'menu "menu"', 1).encode('latin-1'))
    (ROOT/'reports/opendream-resource-adaptations.json').write_text(json.dumps(resource_changes, indent=2))
    (ROOT/'reports/opendream-macro-adaptations.json').write_text(json.dumps([{'key': k, 'command': v} for k, v in macros], indent=2))
    print(f'Checked {len(baseline)} frozen files; staged {len(changes)} line adaptations.')
    print(f'Converted {len(resource_changes)} legacy DMI files; transferred {len(macros)} original macro bindings.')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet', type=Path)
    parser.add_argument('--compiler', type=Path)
    args = parser.parse_args()
    target = prepare()
    if args.dotnet and args.compiler:
        with (ROOT/'reports/opendream-adapted-compile.log').open('w') as log:
            result = subprocess.run([str(args.dotnet), str(args.compiler), str(target/'Cave Crawlers.dme')],
                                    stdout=log, stderr=subprocess.STDOUT)
        raise SystemExit(result.returncode)
