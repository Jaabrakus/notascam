#!/bin/zsh
set -e
cd -- "$(dirname -- "$0")"
exec python3 tools/local_runtime.py server "$@"
