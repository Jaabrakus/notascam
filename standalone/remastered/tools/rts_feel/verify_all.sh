#!/bin/zsh
# Everything rts-feel checks without the app lock (overnight polish 2026-10-22/23): the page's hooks and block are in
# place, every script parses, game/ compiles, the headless suite, the same page in a real WKWebView, the arena tests.
#   zsh tools/rts_feel/verify_all.sh
cd "$(dirname "$0")/../.." || exit 1
fail=0
step() { echo "== $1"; shift; "$@" || { echo "FAILED: $*"; fail=1; } }
step "hooks and block present (idempotent re-apply)" python3 tools/rts_feel/patch_hooks.py game/Interface/remastered.html tools/rts_feel/rf_module.js
step "ready request is the page's last script" python3 -c "
import re,sys
h=open('game/Interface/remastered.html',encoding='utf-8').read()
last=re.findall(r'<script>(.*?)</script>',h,flags=re.S)[-1]
sys.exit(0 if \"send('ready','')\" in last and h.count(\"send('ready','');\")==1 else 1)"
step "script blocks parse" python3 tools/rts_feel/check_scripts.py
step "game compiles" python3 tools/rts_feel/compile_check.py
step "skin macro names unique" zsh -c "test -z \"\$(/usr/bin/grep -o 'name = \"[^\"]*\"' game/skin.dmf | sort | uniq -d)\""
step "headless suite" python3 tools/rts_feel/headless_feel.py
step "WebKit check" zsh -c "python3 tools/rts_feel/wk_feel.py > reports/polish-2026-10-22/rts-feel/wk-feel.txt 2>&1; grep -q 'RESULT {' reports/polish-2026-10-22/rts-feel/wk-feel.txt && ! grep -q 'ERROR\|console.error' reports/polish-2026-10-22/rts-feel/wk-feel.txt"
step "arena: first step" python3 tools/rts_feel/check_step.py --test step --label rts-step-verify
step "arena: workshop walk" python3 tools/rts_feel/check_step.py --test station --label rts-station-verify
step "arena: mined stone carried (check_breaking)" python3 tools/check_breaking.py
step "arena: villager priority 1 first (check_settlement)" python3 tools/check_settlement.py
[ $fail = 0 ] && echo "ALL OK" || echo "SOME FAILED"
exit $fail
