#!/usr/bin/env bash
# Start the Scale GUInstall backend server.
# Installs Flask if missing, then starts scale-server.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER="$SCRIPT_DIR/scale-server.py"
PORT="${PORT:-5001}"

if [[ ! -f "$SERVER" ]]; then
  echo "ERROR: scale-server.py not found at $SERVER" >&2
  exit 1
fi

# Ensure Flask is available
if ! python3 -c "import flask" 2>/dev/null; then
  echo "Flask not found — installing..."
  pip install "flask>=3.0,<4"
fi

# Verify Python >= 3.10
python3 - <<'EOF'
import sys
if sys.version_info < (3, 10):
    print(f"ERROR: Python 3.10+ required, found {sys.version}", file=sys.stderr)
    sys.exit(1)
EOF

echo ""
echo "Scale GUInstall — backend server"
echo "  URL : http://127.0.0.1:$PORT"
echo "  Open: Scale-GUInstall.html in your browser"
echo "  Stop: Ctrl+C"
echo ""

PORT="$PORT" python3 "$SERVER"
