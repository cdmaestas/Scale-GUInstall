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

# Find the best available Python >= 3.10 (prefer highest version)
PYTHON=""
for minor in 14 13 12 11 10; do
  for candidate in "python3.$minor" "/usr/bin/python3.$minor" "/usr/local/bin/python3.$minor"; do
    if command -v "$candidate" &>/dev/null 2>&1; then
      PYTHON="$candidate"
      break 2
    fi
  done
done

# Fall back to python3 if it meets the requirement
if [[ -z "$PYTHON" ]]; then
  if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    PYTHON="python3"
  fi
fi

if [[ -z "$PYTHON" ]]; then
  echo "ERROR: Python 3.10+ is required but not found." >&2
  echo "Available: python3.10, python3.11, python3.12, python3.13, or python3.14" >&2
  echo "Install:   sudo apt install python3.11  OR  sudo yum install python3.11" >&2
  exit 1
fi

echo "Using $PYTHON ($(${PYTHON} --version 2>&1))"

# Ensure Flask and waitress are available under the chosen interpreter.
# Deliberately does NOT fall back to piping get-pip.py from the network
# into the interpreter on failure — that's an unverified remote script
# execution with no integrity check, not appropriate to run automatically.
# If pip itself is missing, install it via the OS package manager instead.
if ! "$PYTHON" -c "import flask, waitress" 2>/dev/null; then
  echo "Flask/waitress not found — installing..."
  if ! "$PYTHON" -m pip install "flask>=3.0,<4" "waitress>=3.0,<4"; then
    echo "" >&2
    echo "ERROR: pip install failed — is pip installed for $PYTHON?" >&2
    echo "Install pip via your OS package manager, then re-run this script:" >&2
    echo "  sudo apt install python3-pip  OR  sudo yum install python3-pip" >&2
    exit 1
  fi
fi

echo ""
echo "Scale GUInstall — backend server"
echo "  URL : http://127.0.0.1:$PORT"
echo "  Open: http://127.0.0.1:$PORT in your browser — not Scale-GUInstall.html directly"
echo "        (the server injects an auth token into the page as it serves it;"
echo "         a copy opened straight from disk can't make real backend calls)"
echo "  Stop: Ctrl+C"
echo ""
echo "  SSH tunnel (from your workstation):"
echo "    ssh -L $PORT:127.0.0.1:$PORT <user>@<scale-node>"
echo "  Then open http://127.0.0.1:$PORT in your local browser."
echo ""
echo "  If you see 'channel X: open failed: administratively prohibited',"
echo "  enable local port forwarding on the Scale node:"
echo "    sudo ./packaging/enable-ssh-forwarding.sh"
echo "  (writes an sshd_config.d drop-in, validates, and reloads sshd)"
echo ""

PORT="$PORT" "$PYTHON" "$SERVER"
