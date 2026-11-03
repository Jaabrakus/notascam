"""Retain original DMF zero-size semantics before the client normalizes them."""
import hashlib
import json
from pathlib import Path
import re


def write_hints(skin: Path, output: Path):
    window = element = None
    controls = {}
    for line in skin.read_text(encoding='latin-1').splitlines():
        match = re.match(r'window "([^"]+)"', line)
        if match:
            window, element = match[1], None
        elif re.match(r'(macro|menu) ', line):
            window = element = None
        match = re.match(r'\s*elem "([^"]+)"', line)
        if match:
            element = match[1]
        match = re.match(r'\s*size = (\d+)x(\d+)', line)
        if match and window and element:
            controls[f'{window}.{element}'] = {'x': int(match[1]) == 0, 'y': int(match[2]) == 0}
    output.write_text(json.dumps({'skin_sha256': hashlib.sha256(skin.read_bytes()).hexdigest(),
                                 'controls': controls}, indent=2)+'\n')
