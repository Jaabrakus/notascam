#!/usr/bin/env python3
"""A behaviour check (tools/check_NAME.py) made to run on a candidate game folder, at speed 4, without touching anyone
else's run of it:

    python3 tools/rts_feel/wild/check_copy.py NAME LABEL GAME_DIR PORT_OFFSET > /path/check_NAME_LABEL.py

The copy reads GAME_DIR for game/, runs the world on the app's engine at world.game_state = 4 (the house rule for
behaviour checks; checks on the replica's engine had no game clock), puts its arena in a temp folder, names its logs and
report NAME-LABEL-..., and moves its ports by PORT_OFFSET. Its arena folder is deleted when it ends. Everything else is the check as it is."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    name, label, game, off = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    s = (ROOT/f'tools/check_{name}.py').read_text()
    s = f"import sys as _rf_sys0; _rf_sys0.path.insert(0, {str(ROOT/'tools')!r})\n" + s   # its imports (check_engine) from tools/
    # its arena in a temp folder that goes when the check ends (they were left behind: 2.5 GB by 2026-10-25 01:xx)
    s = ("import atexit as _rf_atexit, shutil as _rf_shutil, tempfile as _rf_tempfile\n"
         "from pathlib import Path as _rf_Path\n"
         "def _rf_tmp(prefix):\n"
         "    d = _rf_tempfile.mkdtemp(prefix=prefix)\n"
         "    _rf_atexit.register(_rf_shutil.rmtree, d, True)\n"
         "    return _rf_Path(d)\n") + s
    s = s.replace("ROOT = Path(__file__).resolve().parents[1]",
                  f"ROOT = Path({str(ROOT)!r})\nimport sys as _rf_sys; _rf_sys.path.insert(0, str(ROOT/'tools'))\nGAME = Path({game!r})", 1)
    s = re.sub(r"ROOT\s*/\s*'game'", 'GAME', s)
    # the arena in a temp folder; logs and report labelled
    s = re.sub(r"ROOT\s*/\s*'tests/([a-z_]+)-arena'", lambda m: f"_rf_tmp('rf-{m.group(1)}-')/'arena'", s)
    s = re.sub(r"ROOT\s*/\s*'tests/([a-z_]+)-(compile\.log|server\.log|checks\.json|world\.log)'",
               lambda m: f"ROOT/'tests/{m.group(1)}-{label}-{m.group(2)}'", s)
    s = re.sub(r"(ROOT\s*/\s*f'tests/\{label\})-", r"\1-" + label + "-", s)
    # the app's engine (the game clock) for the world, the replica's compiler (the app ships none)
    if "RUNTIME = ROOT.parent/'replica/runtime/macos-x64'" in s:
        s = s.replace("RUNTIME = ROOT.parent/'replica/runtime/macos-x64'",
                      "RUNTIME = ROOT.parent/'replica/runtime/macos-x64'\nSERVER_RT = Path(os.environ.get('RM_SERVER_RT') or ROOT/'Dungeon Master Remastered.app/Contents/Resources/game/runtime')   # RM_SERVER_RT: a runtime copy with a candidate engine", 1)
        s = re.sub(r"\[str\(dotnet\), str\(RUNTIME/'server/Robust\.Server\.dll'\)",
                   "[str(SERVER_RT/'dotnet/dotnet'), str(SERVER_RT/'server/Robust.Server.dll')", s)
    # check_engine's runtime (combat): RM_SERVER_RT too
    s = s.replace("RUNTIME = check_engine.APP_RUNTIME", "RUNTIME = Path(os.environ.get('RM_SERVER_RT') or check_engine.APP_RUNTIME)")
    # speed 4
    s = re.sub(r"'\\tNew\(\)\\n\\t\\tspawn\(0\) ", r"'\\tNew()\\n\\t\\tgame_state = 4\\n\\t\\tspawn(0) ", s)
    s = re.sub(r"f'\\tNew\(\)\\n\\t\\tspawn\(0\) ", r"f'\\tNew()\\n\\t\\tgame_state = 4\\n\\t\\tspawn(0) ", s)
    # ports
    s = re.sub(r"(net\.port=|topic_port=)(\d{4,5})", lambda m: f"{m.group(1)}{int(m.group(2)) + off}", s)
    s = re.sub(r"(default=)(1\d{4})(\b)", lambda m: f"{m.group(1)}{int(m.group(2)) + off}{m.group(3)}", s)
    sys.stdout.write(s)


if __name__ == '__main__':
    main()
