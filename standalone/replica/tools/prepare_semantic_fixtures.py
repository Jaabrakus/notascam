#!/usr/bin/env python3
"""Retain original and explicitly indented parser comparison inputs."""
from pathlib import Path
from compact_conditionals import normalize

ROOT=Path(__file__).resolve().parents[1]

def main():
    text=(ROOT/'reference/fixtures/branching.dm').read_text()
    staged=normalize(text).replace('R=(Y=="num")?text2num(P) :(Y=="type")?text2path(P) :(Y=="ref")? locate(P) :I?I :P',
        'R=(Y=="num") ? text2num(P) : ((Y=="type") ? text2path(P) : ((Y=="ref") ? locate(P) : (I ? I : P)))')
    for engine,source in [('byond',text),('opendream',staged)]:
        target=ROOT/'reference'/f'branching-{engine}'
        target.mkdir(exist_ok=True)
        (target/'branching.dm').write_text(source)
        (target/'branching.dme').write_text('#include "branching.dm"\n')

if __name__=='__main__':main()
