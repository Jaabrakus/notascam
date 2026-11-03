#!/bin/zsh
# The installed game uses only bundled executables and macOS system utilities.
set -u
umask 077
resources="${0:A:h}"
game="$resources/game"
data="${DM_STANDALONE_DATA_DIR:-$HOME/Library/Application Support/Hidden Clans}"
# Saves are keyed by this name. "@login" (shared builds) uses the Mac account name.
username="$(cat "$game/player-name" 2>/dev/null)"
if [[ -z "$username" || "$username" == @login ]]; then
  username="${$(/usr/bin/id -un 2>/dev/null)//[^A-Za-z0-9]/}"
  [[ -n "$username" ]] || username=Player
fi
smoke_seconds=0
# Multiplayer (same network): --host opens this world to other Macs on the network,
# --join ADDRESS plays on someone else's world. The password comes in
# DM_JOIN_PASSWORD (never on the command line, where other users could read it).
mode=solo
join_address=""
# Which world (the launcher's world list, 10-31): "world" (the first one, where every world was before) or
# "worlds/<id>". --prepare-only gets the world and profiles ready and stops (checks; the launcher never passes it).
world_rel=world
prepare_only=0
while (( $# )); do
  case "$1" in
    --username) username="$2"; shift 2 ;;
    --smoke-seconds) smoke_seconds="$2"; shift 2 ;;
    --host) mode=host; shift ;;
    --join) mode=join; join_address="$2"; shift 2 ;;
    --world) world_rel="${2:-}"; shift $(( $# > 1 ? 2 : 1 )) ;;
    --prepare-only) prepare_only=1; shift ;;
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
  fail 'Rosetta is not installed. Open Terminal, run: softwareupdate --install-rosetta, then open Hidden Clans again.'
fi
[[ "$world_rel" =~ '^(world|worlds/[A-Za-z0-9_-]{1,40})$' ]] || fail 'That world folder does not look right. Choose the world again in the list.'
world="$data/$world_rel"
print -- "World: $world_rel"
build_id="$(cat "$game/build-id")"
# Each world keeps the build its game files came from in .build-id. The first world's starts as the data folder's
# build-id, which stamped it until now, so it updates exactly when it did before.
if [[ "$world_rel" == world && -d "$world" && ! -f "$world/.build-id" && -f "$data/build-id" ]]; then
  cp "$data/build-id" "$world/.build-id"
fi
if [[ ! -f "$world/.build-id" || "$(cat "$world/.build-id")" != "$build_id" ]]; then
  mkdir -p "$world"
  # Packaged world has no mutable saves or logs; updating it preserves them. A clone where the disk can (APFS: no
  # room taken until a file changes), else a copy.
  /bin/cp -cR "$game/world/." "$world/" 2>/dev/null || cp -R "$game/world/." "$world/" || fail 'Could not copy the game into the world folder.'
  print -r -- "$build_id" > "$world/.build-id"
fi
# The game window natively on Apple silicon too (10-31, reports/load-asleep-1030). Only when this Mac is arm64 and the
# app has the arm64 runtime and window (tools/build_app.py); otherwise, or with RM_ARM64_CLIENT=0, the x86-64 window
# under Rosetta as before. Its arm64 files are laid over the player's copy of the client, copied again when this changes.
client_arch=x86_64
if [[ "${RM_ARM64_CLIENT:-1}" != 0 && "$(/usr/bin/uname -m)" == arm64 && -x "$game/runtime/dotnet-arm64/dotnet" && -f "$game/runtime/client-arm64/Robust.Client.dll" && -f "$game/runtime/webview-webkit-arm64/libdmwebkit.dylib" ]]; then
  client_arch=arm64
fi
if [[ ! -f "$data/build-id" || "$(cat "$data/build-id")" != "$build_id" || "$(cat "$data/client-arch" 2>/dev/null || print x86_64)" != "$client_arch" || ! -f "$data/client/Space Station 14.app/Contents/Resources/Robust.Client.dll" ]]; then
  mkdir -p "$data/client"
  cp -R "$game/runtime/client/." "$data/client/" || fail 'Could not copy the game client into Application Support.'
  if [[ "$client_arch" == arm64 ]]; then
    cp "$game/runtime/client-arm64/"* "$data/client/Space Station 14.app/Contents/Resources/" || fail 'Could not copy the game client into Application Support.'
  fi
  # A downloaded app's quarantine flag would otherwise follow the copied client.
  /usr/bin/xattr -dr com.apple.quarantine "$data/client" 2>/dev/null
  print -r -- "$client_arch" > "$data/client-arch"
  print -r -- "$build_id" > "$data/build-id"
fi
if [[ "$world_rel" == world && ! -f "$data/initial-saves-imported" ]]; then
  for kind in units players; do
    if [[ -d "$game/initial-saves/$kind" && ! -d "$world/$kind" ]]; then
      cp -R "$game/initial-saves/$kind" "$world/$kind" || exit 1
    fi
  done
  touch "$data/initial-saves-imported"
fi
# One profile per player for every world on this Mac: sound and HUD settings, achievements, saved designs (Rarity.dm
# RemasterProfilePath). The first world's profiles are copied once, never moved, so an older build still finds its own.
profiles="$data/profiles"
mkdir -p "$profiles" || fail 'Could not make the profiles folder.'
if [[ ! -f "$profiles/.imported" ]]; then
  for profile in "$data/world/units"/remaster_profile_*.sav(N); do
    [[ -e "$profiles/${profile:t}" ]] || cp -p "$profile" "$profiles/" || fail 'Could not copy your profile.'
  done
  touch "$profiles/.imported"
fi
export RM_PROFILE_DIR="$profiles"
if (( prepare_only )); then
  print -- "Prepared: $world"
  print -r -- stopped > "$status_file"
  exit 0
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
    print -- 'Hidden Clans is already running.'; exit 0
  fi
  rm -f "$lock/pid"; rmdir "$lock" 2>/dev/null
  mkdir "$lock" || exit 1
fi
print -- $$ > "$lock/pid"
# Precompiled framework code, .NET's default. Off since the replica's first tools (10-15) with no reason recorded
# anywhere; on since 10-31 (reports/load-asleep-1030): the world ready ~5 s sooner under Rosetta, load peak ~40 MB
# lower, the same world; the game window ran cleanly with it in the real app.
export DOTNET_ReadyToRun=1
# No profile-guided re-compiling: under Rosetta every compiled version of a method is translated again; with it off
# the game window holds ~27 MB less of compiled code, no CPU cost measured (load-asleep-1030, 10-30 night).
export DOTNET_TieredPGO=0
# Workstation GC, not the runtime config's Server GC: on the user's world (4 layers of 1000x1000 tiles) Server GC held
# a 6.7 GB footprint that swapped out and stalled the world; workstation GC holds 3.3 GB with no extra CPU (2026-10-23).
export DOTNET_gcServer=0
# Compact the heap when it fills with free room: 200 units on the user's world ended at 1.43 GB, not 1.95 GB (2026-10-26,
# devlog/2026-10-26/memgc.md).
export DOTNET_GCConserveMemory=5
client_dotnet="$runtime/dotnet/dotnet"
export ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW="$runtime/webview-webkit"
if [[ "$client_arch" == arm64 ]]; then
  client_dotnet="$runtime/dotnet-arm64/dotnet"
  export ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW="$runtime/webview-webkit-arm64"
fi
export DM_SKIN_LAYOUT_HINTS="$game/skin-layout-hints.json"
export DM_LOCAL_SERVER_READY_FILE="$ready"
export DM_LOCAL_SERVER_PORT=12171
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
if [[ "$mode" == join ]]; then
  [[ "$join_address" =~ '^[A-Za-z0-9.:-]+$' ]] || fail 'That host address does not look right. Use the address the host sees in their game, for example 192.168.1.20.'
  client_dir="$data/client/Space Station 14.app/Contents/Resources"
  cd "$client_dir" || exit 1
  "$client_dotnet" "$client_dir/Robust.Client.dll" \
    --mount-zip "$runtime/server/Content.Client.zip" --connect \
    --connect-address "udp://$join_address:12171" --username "$username" --self-contained \
    --cvar web.headless=false --cvar discord.enabled=false > "$client_log" 2>&1 &
  client_pid=$!
  print -r -- playing > "$status_file"
  wait "$client_pid"
  result=$?
  client_pid=0
  exit "$result"
fi
# Hosting: the world listens on every network interface, and the game reads the
# join password and this Mac's addresses from the world folder. Solo play removes
# them and listens on this Mac only.
bind=127.0.0.1
web=()
rm -f "$world/join-password" "$world/host-addresses" "$world/host-name"
if [[ "$mode" == host ]]; then
  [[ -n "${DM_JOIN_PASSWORD:-}" ]] || fail 'Hosting needs a password for your friends to join with.'
  bind=0.0.0.0
  print -rn -- "$DM_JOIN_PASSWORD" > "$world/join-password"
  print -rn -- "$username" > "$world/host-name"
  for interface in en0 en1 en2 en3; do /usr/sbin/ipconfig getifaddr "$interface" 2>/dev/null; done > "$world/host-addresses"
  # Friends can also play in a web browser, on the world's own web link (U4, reports/u4-web-1030): http://<this
  # Mac>:8080/. They type a name, and the world asks them the same password it asks a friend's Mac.
  web=(RM_WEB_PORT=8090 RM_WEB_PAGE=mapwindow.hud 'RM_WEB_BIND=*' RM_WEB_OPEN=1)
fi
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
  # The server natively on Apple silicon (10-31, reports/load-asleep-1030): ~130 MB lighter, a third less CPU, in game
  # sooner. Only when this Mac is arm64 and the app has the arm64 runtime and server (tools/build_app.py);
  # otherwise, or with RM_ARM64_SERVER=0, the x86-64 server under Rosetta as before.
  server_dotnet="$runtime/dotnet/dotnet"
  server_dir="$runtime/server"
  if [[ "${RM_ARM64_SERVER:-1}" != 0 && "$(/usr/bin/uname -m)" == arm64 && -x "$runtime/dotnet-arm64/dotnet" && -f "$runtime/server-arm64/Robust.Server.dll" ]]; then
    server_dotnet="$runtime/dotnet-arm64/dotnet"
    server_dir="$runtime/server-arm64"
  fi
  while true; do
    rm -f "$ready" "$reboot"
    # The server's objects up to 4 MB are made with the small ones (the runtime's line is 85 KB): a player's join made
    # hundreds of MB of big short-lived strings and arrays whose room the large-object heap kept (~0.4 GB free after the
    # join, the server ~170 MB higher in play); now they die young (2026-10-30, reports/load-asleep-1030).
    # .NET's shared buffer pool keeps spare buffers for every core (10 here, 32 of each size): 14-22 MB in the server.
    # Two sets of 8 hold ~10 MB, with the same allocation rate and GC time (2026-10-31, reports/load-asleep-1030).
    /usr/bin/env "${web[@]}" DOTNET_GCLOHThreshold=0x400000 DOTNET_SYSTEM_BUFFERS_SHAREDARRAYPOOL_MAXPARTITIONCOUNT=2 \
      DOTNET_SYSTEM_BUFFERS_SHAREDARRAYPOOL_MAXARRAYSPERPARTITION=8 "$server_dotnet" "$server_dir/Robust.Server.dll" \
      --data-dir "$data/server-data" \
      --cvar "opendream.json_path=$world/Cave Crawlers.json" \
      --cvar "net.bindto=$bind" --cvar net.port=12171 \
      --cvar opendream.topic_port=25671 \
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
"$client_dotnet" "$client_dir/Robust.Client.dll" \
  --mount-zip "$runtime/server/Content.Client.zip" --connect \
  --connect-address udp://127.0.0.1:12171 --username "$username" --self-contained \
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
