#!/bin/sh
# Captures the opening request Claude Code sends from the current directory and breaks it down.
# Bodies only: the proxy never writes headers, so no credential touches the disk.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"; OUT="$(mktemp -d)"
node "$HERE/dump-proxy.mjs" "$OUT" > "$OUT/port" & PID=$!; trap 'kill $PID 2>/dev/null' EXIT
sleep 1
ANTHROPIC_BASE_URL="http://127.0.0.1:$(cat "$OUT/port")" claude -p "say only: ok" >/dev/null 2>&1 || true
python3 "$HERE/base-breakdown.py" "$OUT"
