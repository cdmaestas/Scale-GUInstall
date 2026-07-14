#!/bin/bash
# Enable local SSH port forwarding for the Scale GUInstall tunnel.
#
# Fixes: "channel N: open failed: administratively prohibited: open failed"
#
# sshd applies the FIRST value it sees for a keyword, and the stock
# /etc/ssh/sshd_config starts with "Include /etc/ssh/sshd_config.d/*.conf".
# A drop-in file therefore takes precedence over any AllowTcpForwarding
# setting later in the main config — appending to sshd_config does not.
#
# Usage: sudo ./enable-ssh-forwarding.sh

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: run as root (sudo $0)" >&2
    exit 1
fi

SSHD_CONFIG="/etc/ssh/sshd_config"
DROPIN_DIR="/etc/ssh/sshd_config.d"
DROPIN="$DROPIN_DIR/60-scale-guinstall.conf"

if [ ! -f "$SSHD_CONFIG" ]; then
    echo "ERROR: $SSHD_CONFIG not found — is OpenSSH server installed?" >&2
    exit 1
fi

if [ -d "$DROPIN_DIR" ] && grep -qiE "^\s*Include\s+.*sshd_config\.d" "$SSHD_CONFIG"; then
    # Preferred: drop-in file, included before the main config so it wins
    printf '# Installed by Scale GUInstall — allow ssh -L tunnels for the GUI\nAllowTcpForwarding local\n' > "$DROPIN"
    chmod 0644 "$DROPIN"
    echo "Wrote $DROPIN"
else
    # No drop-in support: edit the directive in place (first match wins,
    # so appending to the end of the file would NOT override an existing
    # 'AllowTcpForwarding no' above it)
    if grep -qiE "^\s*#?\s*AllowTcpForwarding" "$SSHD_CONFIG"; then
        sed -i 's/^[[:space:]]*#\{0,1\}[[:space:]]*AllowTcpForwarding.*/AllowTcpForwarding local/I' "$SSHD_CONFIG"
        echo "Updated AllowTcpForwarding directive in $SSHD_CONFIG"
    else
        printf '\n# Added by Scale GUInstall — allow ssh -L tunnels for the GUI\nAllowTcpForwarding local\n' >> "$SSHD_CONFIG"
        echo "Appended AllowTcpForwarding local to $SSHD_CONFIG"
    fi
fi

# Validate before reloading — never leave sshd unable to restart
if ! sshd -t; then
    echo "ERROR: sshd config validation failed — reverting is recommended, sshd NOT reloaded" >&2
    exit 1
fi

if command -v systemctl >/dev/null 2>&1; then
    systemctl reload sshd 2>/dev/null || systemctl reload ssh
else
    service sshd reload 2>/dev/null || service ssh reload
fi

echo "OK: local TCP forwarding enabled. Verify with:"
echo "    sudo sshd -T | grep -i allowtcpforwarding"
