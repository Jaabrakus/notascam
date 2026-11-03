# The HUD page's sources

`game/Interface/remastered.html` is built from the files in `src/` by `hud.py`, the same way `art/gear3d/install.py`
builds `gear3d.js`. The page the app loads is still one file, and `src/` joins back to it byte for byte.

- `src/` holds the page cut at its own edges: each `<style>` and `<script>` block, the main script at its
  `// =====` section headers, and the boot cover, with its logo as `assets/*.png`. `manifest.json` gives the order.
- **To change the page:** edit the file in `src/`, then run `python3 art/hud/hud.py build`.
- **If a land script patched `game/Interface/remastered.html` directly:** run `python3 art/hud/hud.py adopt`, which
  re-cuts `src/` from the page. It refuses if `src/` also has edits that were never built.
- **To check:** `python3 art/hud/hud.py status` (check_suite's `hudjoin` runs it). `tools/build_app.py` refuses to
  package a page that isn't the join of `src/`.
- **Old `src/` folders** that a re-cut replaces go to the Trash, never deleted.
