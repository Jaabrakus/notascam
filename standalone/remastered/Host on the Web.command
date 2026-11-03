#!/bin/zsh
# Double-click to see the address friends open to play in their browser. Host the world in the app first ("Host for
# friends"): since 2026-10-30 that world serves browsers itself, on port 8080. For an older app, the old way is
# tools/web_host.py --relay (a game client per friend on this Mac); keep its window open while they play.
cd "$(dirname "$0")" || exit 1
printf '\033]0;Banners of the Deep — Host on the Web\007'
if [[ " $* " == *" --relay "* && ! -f engine/webview-relay/Robust.Client.WebView.dll ]]; then
  echo "Building the web relay first (one time)…"
  python3 tools/build_web_relay.py || { echo; echo "The build failed. Press Return to close."; read; exit 1; }
fi
python3 -u tools/web_host.py "$@"
status=$?
echo
if (( status != 0 )); then echo "That didn't work (see above)."; fi
echo "Press Return to close this window."
read
