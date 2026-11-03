#!/bin/zsh
cd "$(dirname "$0")/../standalone/goa-races/armory" || exit 1
exec python3 serve.py --open
