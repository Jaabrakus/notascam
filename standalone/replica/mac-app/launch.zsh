#!/bin/zsh
# The installed game uses only bundled executables and macOS system utilities.
set -u
umask 077
resources="${0:A:h}"
game="$resources/game"
data="${DM_STANDALONE_DATA_DIR:-$HOME/Library/Application Support/Dungeon Master Standalone}"
# Saves are keyed by this name. "@login" (shared builds) uses the Mac account name.
username="$(cat "$game/player-name" 2>/dev/null)"
if [[ -z "$username" || "$username" == @login ]]; then
  username="${$(/usr/bin/id -un 2>/dev/null)//[^A-Za-z0-9]/}"
  [[ -n "$username" ]] || username=Player
fi
smoke_seconds=0
while (( $# )); do
  case "$1" in
    --username) username="$2"; shift 2 ;;
    --smoke-seconds) smoke_seconds="$2"; shift 2 ;;
    *) print -u2 -- "Unknown option: $1"; exit 2 ;;
  esac
done
mkdir -p "$data/reports" "$data/server-data"
exec >"$data/reports/launcher.log" 2>&1
print -- "Packaged game: $game"
print -- "Player data: $data"
status_file="${DM_LAUNCH_STATUS:-$data/reports/launch-status}"
print -r -- preparing > "$status_file"
# The launcher shows "error:" status text to the player when the script fails.
fail() { print -- "$1"; print -r -- "error:$1" > "$status_file"; exit 1; }
source "$resources/local_save.zsh" || fail 'The local save helper is missing from this app. Reinstall the app.'
# The bundled engine is Intel (x64); Apple Silicon runs it through Rosetta 2.
if [[ "$(/usr/bin/uname -m)" == arm64 ]] && ! /usr/bin/arch -x86_64 /usr/bin/true 2>/dev/null; then
  fail 'Rosetta is not installed. Open Terminal, run: softwareupdate --install-rosetta, then open Dungeon Master again.'
fi
world="$data/world"
build_id="$(cat "$game/build-id")"
if [[ ! -f "$data/build-id" || "$(cat "$data/build-id")" != "$build_id" || ! -f "$data/client/Space Station 14.app/Contents/Resources/Robust.Client.dll" ]]; then
  mkdir -p "$world"
  # Packaged world has no mutable saves or logs; updating it preserves them.
  cp -R "$game/world/." "$world/" || exit 1
  mkdir -p "$data/client"
  cp -R "$game/runtime/client/." "$data/client/" || fail 'Could not copy the game client into Application Support.'
  # A downloaded app's quarantine flag would otherwise follow the copied client.
  /usr/bin/xattr -dr com.apple.quarantine "$data/client" 2>/dev/null
  print -r -- "$build_id" > "$data/build-id"
fi
if [[ ! -f "$data/initial-saves-imported" ]]; then
  for kind in units players; do
    if [[ -d "$game/initial-saves/$kind" && ! -d "$world/$kind" ]]; then
      cp -R "$game/initial-saves/$kind" "$world/$kind" || exit 1
    fi
  done
  touch "$data/initial-saves-imported"
fi
runtime="$game/runtime"
ready="$data/reports/server-ready"
reboot="$data/reports/reboot-request"
server_log="$data/reports/server.log"
client_log="$data/reports/client.log"
# A package instance owns its data directory. A second launch opens the existing app.
lock="$data/launcher.lock"
if ! mkdir "$lock" 2>/dev/null; then
  owner="$(cat "$lock/pid" 2>/dev/null)"
  if [[ -n "$owner" ]] && kill -0 "$owner" 2>/dev/null; then
    print -- 'Dungeon Master is already running.'; exit 0
  fi
  rm -f "$lock/pid"; rmdir "$lock" 2>/dev/null
  mkdir "$lock" || exit 1
fi
print -- $$ > "$lock/pid"
export DOTNET_ReadyToRun=0
export ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW="$runtime/webview-webkit"
export DM_SKIN_LAYOUT_HINTS="$game/skin-layout-hints.json"
export DM_LOCAL_SERVER_READY_FILE="$ready"
export DM_LOCAL_SERVER_PORT=12121
export DM_REBOOT_REQUEST="$reboot"
save_request="$data/reports/save-request"
export DM_LOCAL_SAVE_REQUEST="$save_request"
rm -f "$save_request" "$save_request.ack" "$save_request.error"
client_pid=0
supervisor_pid=0
cleaned=0
save_failed=0
cleanup() {
  (( cleaned )) && return
  cleaned=1
  if [[ -f "$ready" ]] && (( supervisor_pid > 0 )) && kill -0 "$supervisor_pid" 2>/dev/null; then
    if ! dm_request_local_save "$save_request"; then
      save_failed=1
      print -- 'The final save was not acknowledged. Inspect reports/save-request.error and server.log.'
      print -r -- save-failed > "$data/reports/save-status"
      print -r -- 'error:The final save was not acknowledged. Your latest progress may not have been saved. Check save-request.error and server.log in the reports folder.' > "$status_file"
    else
      print -r -- saved > "$data/reports/save-status"
    fi
  fi
  if (( client_pid > 0 )) && kill -0 "$client_pid" 2>/dev/null; then
    kill -INT "$client_pid" 2>/dev/null
    for attempt in {1..5}; do
      kill -0 "$client_pid" 2>/dev/null || break
      sleep 1
    done
    kill -TERM "$client_pid" 2>/dev/null || true
  fi
  # Let the original Logout()/save complete before stopping the world.
  sleep 2
  if (( supervisor_pid > 0 )); then
    kill -TERM "$supervisor_pid" 2>/dev/null || true
    wait "$supervisor_pid" 2>/dev/null || true
  fi
  rm -f "$ready" "$reboot" "$lock/pid"
  rmdir "$lock" 2>/dev/null || true
  [[ "$(cat "$status_file" 2>/dev/null)" == error:* ]] || print -r -- stopped > "$status_file"
  (( save_failed )) && exit 1
  return 0
}
trap 'cleanup' EXIT
trap 'exit 130' INT TERM
rm -f "$ready" "$reboot"
print -r -- starting > "$status_file"
(
  trap - EXIT
  server_pid=0
  stop_server() {
    if (( server_pid > 0 )); then
      kill -INT "$server_pid" 2>/dev/null || true
      for attempt in {1..10}; do
        kill -0 "$server_pid" 2>/dev/null || break
        sleep 1
      done
      kill -TERM "$server_pid" 2>/dev/null || true
      wait "$server_pid" 2>/dev/null || true
    fi
    rm -f "$ready"
  }
  trap 'stop_server; exit 0' INT TERM
  while true; do
    rm -f "$ready" "$reboot"
    "$runtime/dotnet/dotnet" "$runtime/server/Robust.Server.dll" \
      --data-dir "$data/server-data" \
      --cvar "opendream.json_path=$world/Cave Crawlers.json" \
      --cvar net.bindto=127.0.0.1 --cvar net.port=12121 \
      --cvar "log.path=$data/reports/engine-logs" \
      --cvar net.max_connections=16 --cvar status.enabled=false \
      --cvar hub.advertise=false --cvar auth.mode=0 \
      --cvar game.auto_pause_empty=false > "$server_log" 2>&1 &
    server_pid=$!
    while kill -0 "$server_pid" 2>/dev/null; do
      if /usr/bin/grep -q -- ' -> Ready' "$server_log"; then
        /usr/bin/uuidgen > "$ready.pending"
        mv "$ready.pending" "$ready"
        break
      fi
      sleep 1
    done
    wait "$server_pid"
    result=$?
    server_pid=0
    rm -f "$ready"
    [[ -f "$reboot" ]] || exit "$result"
  done
) &
supervisor_pid=$!
for attempt in {1..180}; do
  [[ -f "$ready" ]] && break
  kill -0 "$supervisor_pid" 2>/dev/null || exit 1
  sleep 1
done
[[ -f "$ready" ]] || fail 'The game world did not finish starting.'
client_dir="$data/client/Space Station 14.app/Contents/Resources"
cd "$client_dir" || exit 1
"$runtime/dotnet/dotnet" "$client_dir/Robust.Client.dll" \
  --mount-zip "$runtime/server/Content.Client.zip" --connect \
  --connect-address udp://127.0.0.1:12121 --username "$username" --self-contained \
  --cvar web.headless=false --cvar discord.enabled=false > "$client_log" 2>&1 &
client_pid=$!
print -r -- playing > "$status_file"
elapsed=0
while kill -0 "$client_pid" 2>/dev/null; do
  kill -0 "$supervisor_pid" 2>/dev/null || fail 'The game world stopped unexpectedly.'
  if (( smoke_seconds > 0 && elapsed >= smoke_seconds )); then
    print -- 'Timed package verification completed.'
    exit 0
  fi
  sleep 1
  (( elapsed += 1 ))
done
wait "$client_pid"
result=$?
client_pid=0
exit "$result"
