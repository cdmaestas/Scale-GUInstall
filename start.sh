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

# Ensure Flask is available under the chosen interpreter
if ! "$PYTHON" -c "import flask" 2>/dev/null; then
  echo "Flask not found — installing..."
  if ! "$PYTHON" -m pip install "flask>=3.0,<4" 2>/dev/null; then
    # pip not available — try to bootstrap it, then retry
    if command -v curl &>/dev/null; then
      curl -sSL https://bootstrap.pypa.io/get-pip.py | "$PYTHON"
    elif command -v wget &>/dev/null; then
      wget -qO- https://bootstrap.pypa.io/get-pip.py | "$PYTHON"
    else
      echo "ERROR: pip is not installed and neither curl nor wget is available." >&2
      echo "Install pip manually: sudo apt install python3-pip  OR  sudo yum install python3-pip" >&2
      exit 1
    fi
    "$PYTHON" -m pip install "flask>=3.0,<4"
  fi
fi

echo ""
echo "Scale GUInstall — backend server"
echo "  URL : http://127.0.0.1:$PORT"
echo "  Open: Scale-GUInstall.html in your browser"
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
