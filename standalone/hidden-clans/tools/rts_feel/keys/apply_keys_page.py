#!/usr/bin/env python3
"""The 2006 letter keys off the keyboard, the page's half (rts-feel, 2026-10-25; the server's: apply_keys.py).
  - W, S and D don't pan (the user: "W/S/D don't pan"): the held-key pan (RF_PAN) and the old step pan take the arrows
    only. The window edge, the minimap and right-drag still pan.
  - R isn't a key: the menu's Choose your people keeps it.
  - C (cutaway) and X (x-ray) from the game window (skin.dmf, Remaster-3D-Key): the page's own keys.
  - The Shortcuts guide (F3) names C and X.
A is as it was. Exact-match edits, idempotent.
    python3 tools/rts_feel/keys/apply_keys_page.py <game folder>"""
import os, sys, tempfile
from pathlib import Path

EDITS = [
# W, S and D don't pan
("""const RF_PAN={arrowup:[0,1],w:[0,1],arrowdown:[0,-1],s:[0,-1],arrowleft:[-1,0],arrowright:[1,0],d:[1,0]};""",
 """const RF_PAN={arrowup:[0,1],arrowdown:[0,-1],arrowleft:[-1,0],arrowright:[1,0]};   /* the arrows: W, S and D don't pan (the user, 2026-10-25) */"""),
("""  const mv={w:[0,1],arrowup:[0,1],s:[0,-1],arrowdown:[0,-1],a:[-1,0],arrowleft:[-1,0],d:[1,0],arrowright:[1,0]}[k];if(!mv)return;""",
 """  const mv={arrowup:[0,1],arrowdown:[0,-1],arrowleft:[-1,0],arrowright:[1,0]}[k];if(!mv)return;"""),
# R isn't a key
("""// Control groups, Z, Ctrl+Z, F1, P, R, comma/period and the alert jump, while the HUD page has the keyboard (the game window's skin.dmf""",
 """// Control groups, Z, Ctrl+Z, F1, P, comma/period and the alert jump, while the HUD page has the keyboard (the game window's skin.dmf"""),
(""" if(!e.metaKey&&!e.ctrlKey&&!e.altKey){const a={p:'stop',',':'zup','.':'zdown',r:'race'}[e.key];if(a==='race'&&((model&&model.ask)||['askcard','usecard','menu3d'].some(id=>$(id)&&!$(id).hidden)))return;if(a){e.preventDefault();send('action',a);return}}   // P stops; , and . take the camera up or down a level; R: Choose your people / start again (the game window's keys)""",
 """ if(!e.metaKey&&!e.ctrlKey&&!e.altKey){const a={p:'stop',',':'zup','.':'zdown'}[e.key];if(a){e.preventDefault();send('action',a);return}}   // P stops; , and . take the camera up or down a level (the game window's keys). R: the menu's Choose your people only"""),
# C and X from the game window
("""if(String(k)==='escape'){document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',bubbles:true,cancelable:true}));return}return k3(k)}}   // Esc with the game window focused: the page's own Escape handling""",
 """if(String(k)==='escape'){document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',bubbles:true,cancelable:true}));return}const pk={c:['c','KeyC'],x:['x','KeyX']}[String(k)];if(pk){document.body.dispatchEvent(new KeyboardEvent('keydown',{key:pk[0],code:pk[1],bubbles:true,cancelable:true}));return}return k3(k)}}   // Esc, C and X with the game window focused: the page's own (rts-feel 2026-10-25)"""),
# the guide
("""<li><b>Camera:</b> arrow keys or the window edge pan, the wheel zooms, Q/E turn, N faces north, Z centres on the selection;""",
 """<li><b>Camera:</b> arrow keys or the window edge pan, the wheel zooms, Q/E turn, N faces north, Z centres on the selection, C cuts the rock away (or shows this layer only), X shows the layer above as a ghost;"""),
]


def main(game):
    p = Path(game)/'Interface/remastered.html'
    t = p.read_text(encoding='utf-8')
    done = 0
    for old, new in EDITS:
        if new in t: continue
        if t.count(old) != 1: sys.exit(f'remastered.html: no unique match for:\n{old[:200]}')
        t = t.replace(old, new); done += 1
    if done:
        fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.keys-'); os.write(fd, t.encode('utf-8')); os.close(fd)
        os.chmod(tmp, p.stat().st_mode); os.replace(tmp, p)
    print(f'remastered.html: {done} edit(s)' if done else 'remastered.html: already applied')


if __name__ == '__main__':
    main(sys.argv[1])
