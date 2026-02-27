#!/bin/sh
# HyprShare — agent installer
# Usage:
#   curl -sSf https://mv-c.onrender.com/get | sh           # download & install
#   curl -sSf https://mv-c.onrender.com/get | sh -s run    # download & run immediately
set -e

SERVER_URL="https://mv-c.onrender.com"
INSTALL_DIR="$HOME/.local/bin"
BINARY="$INSTALL_DIR/hyprshare"

# ── detect python ────────────────────────────────────────────────────────────
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" >/dev/null 2>&1; then
    PYTHON="$cmd"
    break
  fi
done
[ -z "$PYTHON" ] && { echo "[hyprshare] ERROR: python3 not found" >&2; exit 1; }

# ── install websockets (silent) ──────────────────────────────────────────────
$PYTHON -m pip install --quiet websockets 2>/dev/null || true

# ── download agent.py ────────────────────────────────────────────────────────
mkdir -p "$INSTALL_DIR"
echo "[hyprshare] Downloading agent …"
if   command -v curl >/dev/null 2>&1; then curl -sSf "$SERVER_URL/agent.py" -o "$BINARY"
elif command -v wget >/dev/null 2>&1; then wget  -q   "$SERVER_URL/agent.py" -O "$BINARY"
else { echo "[hyprshare] ERROR: curl or wget required" >&2; exit 1; }
fi
chmod +x "$BINARY"
echo "[hyprshare] Installed → $BINARY"

# ── run immediately when invoked as: sh -s run ───────────────────────────────
if [ "$1" = "run" ]; then
  exec $PYTHON "$BINARY" --server "$SERVER_URL"
fi

echo ""
echo "  Start a session:"
echo "    $PYTHON $BINARY --server $SERVER_URL"
echo ""
