#!/usr/bin/env python3
"""
Extract the changelog section for a given version tag and append
standard install instructions, writing the result to /tmp/release_body.md.

Usage (called by the Release workflow):
    VERSION=1.0.2 python3 .github/scripts/build_release_body.py
"""
import os
import re
import sys

tag = os.environ.get("VERSION", "").strip()
if not tag:
    print("ERROR: VERSION env var is required", file=sys.stderr)
    sys.exit(1)

repo = os.environ.get("GITHUB_REPOSITORY", "cdmaestas/Scale-GUInstall")

try:
    with open("CHANGELOG.md") as f:
        text = f.read()
except FileNotFoundError:
    text = ""

pattern = rf"## \[{re.escape(tag)}\][^\n]*\n(.*?)(?=\n## \[|\Z)"
m = re.search(pattern, text, re.DOTALL)
if m:
    body = m.group(1).strip()
else:
    print(f"No changelog entry found for {tag} — using generic body", file=sys.stderr)
    body = f"See [CHANGELOG](https://github.com/{repo}/blob/main/CHANGELOG.md) for details."

rpm_name = f"scale-guinstall-{tag}-1.noarch.rpm"
deb_name = f"scale-guinstall_{tag}-1_all.deb"

body += f"""

---

### Install on the IBM Storage Scale installer node

**RHEL / CentOS / Fedora:**
```bash
# Download both files from the release assets, then:
sudo rpm --import RPM-GPG-KEY-scale-guinstall
sudo dnf install ./{rpm_name}
```

**Debian / Ubuntu:**
```bash
sudo apt install ./{deb_name}
```

Then start the server:
```bash
scale-guinstall
# or as a service:
sudo systemctl enable --now scale-guinstall
```

### Connect from your workstation
```bash
ssh -L 5001:127.0.0.1:5001 user@installer-node
```
Open `Scale-GUInstall.html` in your browser — the SSH tunnel connects it to the installer node automatically.

---
See [README](https://github.com/{repo}/blob/main/README.md) for full documentation."""

out = "/tmp/release_body.md"
with open(out, "w") as f:
    f.write(body)
print(f"Wrote release body to {out}")
