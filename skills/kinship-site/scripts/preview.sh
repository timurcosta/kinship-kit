#!/bin/zsh
# Stages the public copy (with versions from git) into a temp folder and serves it on localhost.
# Usage: zsh preview.sh <case dir> [port]   → http://localhost:<port>/ ; stop with: pkill -f "http.server <port>"
set -e
CASE=${1:A}
PORT=${2:-8765}
STAGE=${TMPDIR:-/tmp}/kinship-site-preview-$PORT
pkill -f "http.server $PORT" 2>/dev/null || true
python3 -I "$HOME/.claude/skills/kinship-site/scripts/stage_public.py" "$CASE" "$STAGE"
(cd "$STAGE" && python3 -m http.server "$PORT" >/dev/null 2>&1 &)
sleep 1
echo "http://localhost:$PORT/"
