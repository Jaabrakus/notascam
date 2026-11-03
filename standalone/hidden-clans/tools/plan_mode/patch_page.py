#!/usr/bin/env python3
"""Patch Plan mode into the HUD page (ramps-gather, 2026-10-25).

Idempotent: hooks already present are skipped; the module (between its marker and its </script>) is replaced, and
placed before the page's last script (that one asks for the game and WebKit stops reading the page there).
  python3 tools/plan_mode/patch_page.py game/Interface/remastered.html tools/plan_mode/pm_module.js"""
import sys

START = '<script>\n/* Plan mode (ramps-gather, 2026-10-25'
END_TAG = '</script>\n'
HOOKS = [
    # the level slice: the whole view cut at the level looked at, a disc round the camera (no trench toward it)
    ("V3.mcR=(V3.mcR||0)+((inMt?8:0)-(V3.mcR||0))*Math.min(1,dt*4);if(V3.mcR<0.05)V3.mcR=0;",
     "if(V3.planCut!=null){V3.mcX=V3.cx;V3.mcY=V3.cy;V3.mcTop=V3.planCut;V3.mcR=V3.planR||26}else{V3.mcR=(V3.mcR||0)+((inMt?8:0)-(V3.mcR||0))*Math.min(1,dt*4);if(V3.mcR<0.05)V3.mcR=0}   // Plan mode cuts the whole view at its level (pm module)"),
    ("V3.mcDir=[Math.sin(V3.yaw)*Lc,Math.cos(V3.yaw)*Lc];V3.mcSlope=0;",
     "V3.mcDir=[Math.sin(V3.yaw)*Lc,Math.cos(V3.yaw)*Lc];V3.mcSlope=0;if(V3.planCut!=null)V3.mcDir=[0,0];"),
    # the queued plan blocks round the camera (View3D.dm D["plan"], Plans.dm)
    ("V3.blueprints=arr(m.blueprints);",
     "V3.blueprints=arr(m.blueprints);V3.planCells=arr(m.plan);"),
    # Plan mode's drawing, after rts-feel's
    ("if(typeof rfDraw==='function')try{rfDraw(a)}catch(err){if(!V3.rfErr){V3.rfErr=1;console.error(err)}}",
     "if(typeof rfDraw==='function')try{rfDraw(a)}catch(err){if(!V3.rfErr){V3.rfErr=1;console.error(err)}}if(typeof pmDraw==='function')try{pmDraw(a)}catch(err){if(!V3.pmErr){V3.pmErr=1;console.error(err)}}"),
]


def main(page, module):
    html = open(page, encoding='utf-8').read()
    mod = open(module, encoding='utf-8').read()
    assert mod.startswith(START), 'module must start with its marker'
    if not mod.endswith('\n'):
        mod += '\n'
    for old, new in HOOKS:
        if new in html:
            continue
        assert html.count(old) == 1, ('hook point not found once', old[:60], html.count(old))
        html = html.replace(old, new)
    if START in html:
        i = html.index(START)
        j = html.index(END_TAG, i) + len(END_TAG)
        html = html[:i] + mod + html[j:]
    else:
        last = html.rindex('<script>')
        assert "send('ready','')" in html[last:], 'the last script should be the one asking for the game'
        html = html[:last] + mod + html[last:]
    open(page, 'w', encoding='utf-8').write(html)
    print('patched', page)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
