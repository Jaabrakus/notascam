#!/usr/bin/env python3
"""One key map, the page's half (rts-feel, 2026-10-25; the server's: apply_keys.py, the web view's: apply_keys_native.py).
  - W, S and D don't pan (the user: "no wsd to pan camera"): the held-key pan (RF_PAN) and the old step pan take the
    arrows only. The window edge, the minimap and right-drag still pan.
  - R isn't a key (the user: "Menu only"): the menu's Choose your people keeps it.
  - C (cutaway), X (x-ray) and Enter (the chat line) from the game window (skin.dmf, Remaster-3D-Key): the page's own keys.
  - The chat line (the user: "enter opens chat box"): Enter opens it at the bottom right, over the chat lines. Plain text
    shouts to everyone, /c to the clan, /w name to whisper (HUD.dm RmChatLine); the label says which. Enter sends,
    Escape closes, Up and Down bring back what you sent; the keyboard goes back to the game after.
  - Attack-move (A, as now): a red banner while it's on, "Attack-move: click a target or the ground · Esc cancels".
  - The Shortcuts guide (F3): the chat line, and C and X.
Exact-match edits, idempotent.
    python3 tools/rts_feel/keys/apply_keys_page.py <game folder>"""
import os, sys, tempfile
from pathlib import Path

EDITS = [
# W, S and D don't pan
("""const RF_PAN={arrowup:[0,1],w:[0,1],arrowdown:[0,-1],s:[0,-1],arrowleft:[-1,0],arrowright:[1,0],d:[1,0]};""",
 """const RF_PAN={arrowup:[0,1],arrowdown:[0,-1],arrowleft:[-1,0],arrowright:[1,0]};   /* the arrows: W, S and D don't pan (the user, 2026-10-25: "no wsd to pan camera") */"""),
("""  const mv={w:[0,1],arrowup:[0,1],s:[0,-1],arrowdown:[0,-1],a:[-1,0],arrowleft:[-1,0],d:[1,0],arrowright:[1,0]}[k];if(!mv)return;""",
 """  const mv={arrowup:[0,1],arrowdown:[0,-1],arrowleft:[-1,0],arrowright:[1,0]}[k];if(!mv)return;"""),
# R isn't a key
("""// Control groups, Z, Ctrl+Z, F1, P, R, comma/period and the alert jump, while the HUD page has the keyboard (the game window's skin.dmf""",
 """// Control groups, Z, Ctrl+Z, F1, P, comma/period and the alert jump, while the HUD page has the keyboard (the game window's skin.dmf"""),
(""" if(!e.metaKey&&!e.ctrlKey&&!e.altKey){const a={p:'stop',',':'zup','.':'zdown',r:'race'}[e.key];if(a==='race'&&((model&&model.ask)||['askcard','usecard','menu3d'].some(id=>$(id)&&!$(id).hidden)))return;if(a){e.preventDefault();send('action',a);return}}   // P stops; , and . take the camera up or down a level; R: Choose your people / start again (the game window's keys)""",
 """ if(!e.metaKey&&!e.ctrlKey&&!e.altKey){const a={p:'stop',',':'zup','.':'zdown'}[e.key];if(a){e.preventDefault();send('action',a);return}}   // P stops; , and . take the camera up or down a level (the game window's keys). R is the menu's only (the user: "Menu only")"""),
# C, X and Enter from the game window
("""if(String(k)==='escape'){document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',bubbles:true,cancelable:true}));return}return k3(k)}}   // Esc with the game window focused: the page's own Escape handling""",
 """if(String(k)==='escape'){document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',bubbles:true,cancelable:true}));return}const pk={c:['c','KeyC'],x:['x','KeyX'],enter:['Enter','Enter']}[String(k)];if(pk){document.body.dispatchEvent(new KeyboardEvent('keydown',{key:pk[0],code:pk[1],bubbles:true,cancelable:true}));return}return k3(k)}}   // Esc, C, X and Enter with the game window focused: the page's own (one key map, rts-feel 2026-10-25)"""),
# the banner and the chat line: markup
("""<div id="pausebanner" hidden>Paused <small>Space to carry on · orders still work</small></div>""",
 """<div id="pausebanner" hidden>Paused <small>Space to carry on · orders still work</small></div><div id="amovebar" hidden>Attack-move <small>click a target or the ground · Esc cancels</small></div><form id="chatline" hidden autocomplete="off"><b id="chatTo">Shout</b><input id="chatIn" maxlength="300" spellcheck="false" autocomplete="off" aria-label="Chat: Enter sends, Escape closes" placeholder="to everyone · /c clan · /w name"></form>"""),
# the banner shows with Attack mode, in the top-centre stack
("""document.body.classList.toggle('attacking',!!m.attackMode)}""",
 """document.body.classList.toggle('attacking',!!m.attackMode);{const amb=$('amovebar');if(amb&&amb.hidden===!!m.attackMode){amb.hidden=!m.attackMode;hcStackNotices()}}}"""),
(""" for(const id of ['lockbar','warbar','pausebanner','attack','foodalert','build3d','useon3d','hoverbar']){""",
 """ for(const id of ['lockbar','warbar','pausebanner','amovebar','attack','foodalert','build3d','useon3d','hoverbar']){"""),
# the guide
("""Ctrl+Z undoes the last plan or order.""", """Ctrl+Z undoes the last plan or order (an attack too)."""),
("""<li><b>Camera:</b> arrow keys or the window edge pan, the wheel zooms, Q/E turn, N faces north, Z centres on the selection;""",
 """<li><b>Camera:</b> arrow keys or the window edge pan, the wheel zooms, Q/E turn, N faces north, Z centres on the selection, C cuts the rock away (or shows this layer only), X shows the layer above as a ghost;"""),
("""<li><b>Finding people:</b> F1 selects the next idle unit; Backspace goes to the unit under attack.</li>""",
 """<li><b>Finding people:</b> F1 selects the next idle unit; Backspace goes to the unit under attack.</li><li><b>Chat:</b> Enter opens the chat line: type to shout to everyone, /c for your clan, /w and a name to whisper. Enter sends, Escape closes.</li>"""),
]

CSS = """
/* attack-move's banner (A; rts-feel 2026-10-25) and the chat line (Enter) */
#amovebar{position:fixed;top:56px;left:50%;transform:translateX(-50%);z-index:35;padding:5px 22px 6px;font:17px var(--mfont,Georgia,serif);color:#ffd2c4;border-radius:2px;background:linear-gradient(rgba(120,20,10,.25),rgba(0,0,0,.45)),var(--mpane,#181e30);box-shadow:0 0 0 1px #000,inset 0 0 0 1px #d8573f,0 6px 14px rgba(0,0,0,.5);text-shadow:1px 1px 0 #000;pointer-events:none;text-align:center;white-space:nowrap}
#amovebar[hidden]{display:none}
#amovebar small{display:block;font:12px -apple-system,sans-serif;color:var(--mink,#ddd);opacity:.85}
body.cb #amovebar{color:#ffe0c2;box-shadow:0 0 0 1px #000,inset 0 0 0 1px #d55e00,0 6px 14px rgba(0,0,0,.5)}
#chatline{position:fixed;right:6px;bottom:6px;width:268px;box-sizing:border-box;z-index:60;display:flex;align-items:center;gap:7px;padding:5px 6px 5px 9px;border-radius:2px;background:color-mix(in srgb,var(--mpane,#14110c) 94%,transparent);border:1px solid color-mix(in srgb,var(--macc,#b08a3e) 55%,#000);box-shadow:0 0 0 1px #000,0 4px 14px rgba(0,0,0,.45)}
#chatline[hidden]{display:none}
#chatTo{font:12px var(--mfont,Georgia,serif);color:var(--macc,#f2d27a);white-space:nowrap;min-width:52px}
#chatIn{flex:1 1 auto;min-width:0;font:12px -apple-system,sans-serif;color:var(--mink,#efe3c2);background:rgba(0,0,0,.4);border:1px solid var(--mband,#3a3020);border-radius:2px;padding:4px 6px;outline:none}
#chatIn:focus{border-color:var(--macc,#f2d27a)}
#chatIn::placeholder{color:var(--mink,#efe3c2);opacity:.45}
#chatline.nokeys::after{content:'Click to type';position:absolute;right:10px;bottom:calc(100% + 4px);font:12px -apple-system,sans-serif;color:var(--mink,#efe3c2);background:var(--mpane,#14110c);padding:2px 6px;border-radius:2px;box-shadow:0 0 0 1px #000}
body.chatting #toasts{bottom:46px}
body.overlay.cine #amovebar,body.overlay.cine #chatline{display:none!important}
"""
CSS_ANCHOR = """#pausebanner small{display:block;font:11px -apple-system,sans-serif;color:var(--mink,#ddd);opacity:.8}
"""

JS = """
// The chat line (Enter; rts-feel 2026-10-25, the user: "enter opens chat box"). Plain text shouts to everyone, /c goes to
// the clan, /w name whispers (HUD.dm RmChatLine). Enter sends, Escape closes, Up and Down bring back what you sent; the
// keyboard goes back to the game after. With the game window holding the keyboard (skin.dmf RETURN), the web view takes
// it ({focus:'page'}, WebKitBridge.swift); a web view without that says "Click to type".
const CHAT={hist:[],at:-1};
function chatMode(v){const h=String(v||'').slice(0,3).toLowerCase();return h==='/c '?'Clan':h==='/w '?'Whisper':'Shout'}
function chatOpen(){const f=$('chatline'),i=$('chatIn');if(!f||!i)return;f.hidden=false;document.body.classList.add('chatting');text($('chatTo'),chatMode(i.value));
 if(overlayHost)try{window.webkit.messageHandlers.dmOverlay.postMessage({focus:'page'})}catch(e){}
 i.focus();setTimeout(()=>{if(f.hidden)return;i.focus();f.classList.toggle('nokeys',!document.hasFocus())},150);queueRegions()}
function chatClose(back){const f=$('chatline'),i=$('chatIn');if(!f||f.hidden)return;f.hidden=true;f.classList.remove('nokeys');document.body.classList.remove('chatting');CHAT.at=-1;if(i){i.value='';i.blur()}queueRegions();if(back)gameFocus()}
{const i=$('chatIn');if(i){
 i.addEventListener('input',()=>{text($('chatTo'),chatMode(i.value));$('chatline').classList.remove('nokeys')});
 i.addEventListener('mousedown',()=>$('chatline').classList.remove('nokeys'));
 i.addEventListener('keydown',e=>{e.stopPropagation();
  if(e.key==='Enter'){e.preventDefault();const v=i.value.trim();if(v){send('chatline',v);if(CHAT.hist[CHAT.hist.length-1]!==v)CHAT.hist.push(v);if(CHAT.hist.length>20)CHAT.hist.shift()}chatClose(true);return}
  if(e.key==='Escape'){e.preventDefault();chatClose(true);return}
  if((e.key==='ArrowUp'||e.key==='ArrowDown')&&CHAT.hist.length){e.preventDefault();CHAT.at=e.key==='ArrowUp'?(CHAT.at<0?CHAT.hist.length-1:Math.max(0,CHAT.at-1)):(CHAT.at<0?-1:CHAT.at+1);if(CHAT.at>=CHAT.hist.length)CHAT.at=-1;i.value=CHAT.at<0?'':CHAT.hist[CHAT.at];text($('chatTo'),chatMode(i.value))}});
 i.addEventListener('blur',()=>setTimeout(()=>{if(document.activeElement!==i&&!i.value.trim())chatClose(false)},0))}}
// Enter anywhere but a text field (a press another part of the HUD hasn't taken) opens it
addEventListener('keydown',e=>{if(e.key!=='Enter'||e.metaKey||e.ctrlKey||e.altKey||e.repeat||e.defaultPrevented)return;const t=e.target;if(t&&t.closest&&t.closest('input,select,textarea,[contenteditable]'))return;if(document.querySelector('dialog[open]'))return;e.preventDefault();chatOpen()});
"""
JS_ANCHOR = """// A jump the game made (Z, a control group's second tap, the last alert): the 3D camera goes there now (Attack.dm RemasterCamTo)."""


def main(game):
    p = Path(game)/'Interface/remastered.html'
    t = p.read_text(encoding='utf-8')
    done = 0
    for old, new in EDITS:
        if new in t: continue
        if t.count(old) != 1: sys.exit(f'remastered.html: no unique match for:\n{old[:200]}')
        t = t.replace(old, new); done += 1
    for anchor, add in ((CSS_ANCHOR, CSS.lstrip('\n')), (JS_ANCHOR, JS.lstrip('\n'))):
        if add in t: continue
        if t.count(anchor) != 1: sys.exit(f'remastered.html: no unique anchor:\n{anchor[:200]}')
        t = t.replace(anchor, anchor + add if anchor is CSS_ANCHOR else add + anchor); done += 1
    if done:
        fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.keys-'); os.write(fd, t.encode('utf-8')); os.close(fd)
        os.chmod(tmp, p.stat().st_mode); os.replace(tmp, p)
    print(f'remastered.html: {done} edit(s)' if done else 'remastered.html: already applied')


if __name__ == '__main__':
    main(sys.argv[1])
