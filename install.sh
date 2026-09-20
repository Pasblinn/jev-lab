#!/bin/sh
# Installs the jev launchers, the fallback hooks and the jev-router 0.3.0 routing patch.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="${JEV_LAB_BIN:-$HOME/.local/bin}"
mkdir -p "$BIN" "$HOME/.jev"
for f in jev jev-health jev-down-hook jev-vscode-wrapper; do install -m 0755 "$HERE/bin/$f" "$BIN/$f"; done
install -m 0644 "$HERE/config/fallback-settings.json" "$HOME/.jev/fallback-settings.json"
[ -r "$HOME/.jev-router.env" ] || echo "warn: create ~/.jev-router.env with JEV_API_KEY=... (chmod 600)" >&2

# A mise shim resolves to mise itself, so ask mise for the real path first.
LAUNCHER="$(mise which jev-claude 2>/dev/null || command -v jev-claude)"
ROUTER="$(dirname "$(dirname "$(readlink -f "$LAUNCHER")")")"
[ -f "$ROUTER/src/proxy.mjs" ] || { echo "error: jev-router not found (got $ROUTER)" >&2; exit 1; }
TARGET="$ROUTER/src/proxy.mjs"
if grep -q 'SUGGESTION MODE' "$TARGET"; then
  echo "patch already applied"
else
  cp "$TARGET" "$TARGET.orig"
  # Upstream ships CRLF; normalise so the LF patch applies.
  sed -i.crlf 's/\r$//' "$TARGET" && rm -f "$TARGET.crlf"
  patch -p1 -d "$ROUTER" < "$HERE/patches/jev-router-0.3.0-routing-fixes.patch"
fi
"$BIN/jev-health" && echo "jev healthy - run: jev"
