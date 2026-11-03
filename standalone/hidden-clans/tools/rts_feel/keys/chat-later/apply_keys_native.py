#!/usr/bin/env python3
"""One key map, the web view's half (rts-feel, 2026-10-25): Enter opens the chat line (the user: "enter opens chat box")
even while the game view has the keyboard, which it has after any click in the 3D view. The page could only hand the
keyboard back to the game ({focus:'game'}); now it can take it too ({focus:'page'}), as a click on the HUD does, and the
engine stops running its key macros while you type (MacWebViewManager.cs, focus 6 "1").
  mac-webview/WebKitBridge.swift   the {focus:'page'} request
Exact-match edit, idempotent.
    python3 tools/rts_feel/keys/apply_keys_native.py <remastered folder>              the edit
    python3 tools/rts_feel/keys/apply_keys_native.py <remastered folder> --dylib OUT   and build libdmwebkit.dylib to OUT
       (a test build: the same swiftc call as tools/build_webview.py, which builds engine/webview-webkit when it lands)"""
import argparse, os, subprocess, sys, tempfile
from pathlib import Path

OLD = """        // {"appActive": 1}: the page asks whether the app is in front (its sound mutes in the background); the answer"""
NEW = """        // {"focus": "page"}: the page takes the keyboard, as a click on it does: the chat line that Enter opens while the
        // game view has it (skin.dmf RETURN; rts-feel 2026-10-25). The engine drops its key macros while it's here.
        if let request = message.body as? [String: Any], request["focus"] as? String == "page" {
            guard let window = view.window, !view.isHidden else { return }
            let took = window.makeFirstResponder(view)
            if took && !lastFocused {
                lastFocused = true
                emit(id, 6, 0, "1")
            }
            emit(id, 5, 0, "focus page: took=\\(took) now=\\(window.firstResponder.map { String(describing: type(of: $0)) } ?? "none")")
            return
        }
""" + OLD


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    ap.add_argument('--dylib', type=Path)
    a = ap.parse_args()
    p = a.root/'mac-webview/WebKitBridge.swift'
    t = p.read_text(encoding='utf-8')
    if NEW in t: print('WebKitBridge.swift: already applied')
    else:
        if t.count(OLD) != 1: sys.exit('WebKitBridge.swift: no unique match')
        t = t.replace(OLD, NEW, 1)
        fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.keys-'); os.write(fd, t.encode('utf-8')); os.close(fd)
        os.chmod(tmp, p.stat().st_mode); os.replace(tmp, p)
        print('WebKitBridge.swift: 1 edit')
    if a.dylib:
        cache = a.dylib.parent/'swift-cache'
        subprocess.run(['swiftc', '-swift-version', '5', '-emit-library', '-O', '-target', 'x86_64-apple-macosx12.0',
                        '-module-cache-path', str(cache), '-framework', 'AppKit', '-framework', 'WebKit', str(p), '-o', str(a.dylib)], check=True)
        print(f'built {a.dylib}')


if __name__ == '__main__':
    main()
