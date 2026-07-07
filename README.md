# Scale GUInstall — IBM Storage Scale Installation Toolkit GUI

A single-file web frontend for the IBM Storage Scale Installation Toolkit (`spectrumscale`). Open [Scale-GUInstall.html](Scale-GUInstall.html) in any modern browser to get a guided, form-driven interface for installing, deploying, and upgrading IBM Storage Scale clusters.

> **Disclaimer:** This is an unofficial community helper tool. It is not an IBM product or service. All operations target real cluster infrastructure — read every command preview before executing.

---

## Installing via Package (RPM / DEB)

For production installer nodes, use the pre-built packages instead of running from source. The package installs Flask into a self-contained virtual environment — no manual pip, no cloning, no Python version hunting.

Download the package from the [GitHub Releases page](https://github.com/cdmaestas/Scale-GUInstall/releases) and install it on the installer node:

**RHEL / CentOS / Fedora — with GPG verification (recommended):**
```bash
# Download both files from the release assets, then:
sudo rpm --import RPM-GPG-KEY-scale-guinstall
sudo dnf install ./scale-guinstall-<version>-1.noarch.rpm
```

**RHEL / CentOS / Fedora — skip GPG check (air-gapped or quick install):**
```bash
sudo dnf install --nogpgcheck ./scale-guinstall-<version>-1.noarch.rpm
```

> **RHEL 8/9 note:** Python 3.10+ may need to come from AppStream before installing:
> ```bash
> sudo dnf install python3.11
> ```

**Debian / Ubuntu:**
```bash
sudo apt install ./scale-guinstall_<version>-1_all.deb
```

The post-install script automatically creates a virtual environment at `/usr/lib/scale-guinstall/venv` and installs Flask into it — no additional steps needed.

After install:
```bash
scale-guinstall          # run in foreground (prints the SSH tunnel command)

# Or as a persistent service:
sudo systemctl enable --now scale-guinstall
```

**Build the packages yourself:**
```bash
./packaging/build-pkg.sh        # builds both RPM and DEB into dist/
./packaging/build-pkg.sh --rpm  # RPM only (requires rpmbuild)
./packaging/build-pkg.sh --deb  # DEB only (requires dpkg-deb)
```

Prerequisites: `sudo dnf install rpm-build` (RPM) or `sudo apt install dpkg-dev` (DEB).

---

## Getting Started (from source)

The GUI has two components: the HTML file (runs in your browser) and a lightweight backend server (`scale-server.py`) that executes commands on the installer node. The HTML alone works as a command generator in dry-run mode — you only need the server when you're ready to run real commands.

### 1. Install dependencies

On the installer node (the machine that will run `spectrumscale`):

```bash
pip install "flask>=3.0,<4"
```

### 2. Start the backend server

```bash
python3 scale-server.py
```

Or use the convenience script that handles the pip install automatically:

```bash
chmod +x start.sh
./start.sh
```

The server listens on `http://127.0.0.1:5001` — loopback only, not accessible from the network.

### 3. Open the GUI

Open `Scale-GUInstall.html` in a browser on the same machine. On most Linux systems:

```bash
xdg-open Scale-GUInstall.html
```

Or open `Scale-GUInstall.html` on your local workstation and connect to the installer node remotely via an SSH tunnel (recommended):

```bash
ssh -L 5001:127.0.0.1:5001 user@installer-node
```

Leave the Backend URL in the GUI as `http://127.0.0.1:5001` — SSH forwards it transparently. To tunnel in the background without keeping a shell open:

```bash
ssh -fNL 5001:127.0.0.1:5001 user@installer-node
```

> **Why a tunnel?** The backend server has no authentication and executes privileged commands. Binding it to `0.0.0.0` would expose those endpoints to anyone on the network. The tunnel keeps the server loopback-only while still allowing remote access over an encrypted channel.

> **Dry Run mode is on by default.** Every button shows the command it would run without executing anything. Disable it in Settings only when you're ready to apply changes to the cluster.

### 4. Work through the pages in order

```
Prepare Software → Node Configuration → Cluster Settings → NSD Storage → Filesystem → Protocol Services → Install & Deploy → Post Configuration
```

---

## Features

| Section | What it does |
|---|---|
| **Dashboard** | Live summary of configured nodes, NSDs, filesystems, and protocols; workflow progress tracker |
| **Prepare Software** | Extract the Scale zip package, verify checksum, run the installer, check Ansible and locale prerequisites, and start the `spectrumscale` setup service |
| **Node Configuration** | Add nodes one at a time or via bulk import; assign roles (NSD, Manager, Quorum, Admin, Protocol/CES, GUI, EMS, Call Home, Archive EE); generates `spectrumscale node add` commands |
| **Cluster Settings** | Set GPFS cluster name, I/O profile, remote shell/copy binaries, port range, GPL binary directory, call home, performance monitoring, and file audit logging |
| **NSD Storage** | Define Network Shared Disks with server, disk path, failure group, usage type, and size; inline edit and remove; discover partitions on a node |
| **Filesystem** | Configure GPFS filesystem name, mount point, block size, replication, metadata replication, inodes, and advanced options (quotas, compression, encryption, IAM) |
| **Protocol Services** | Enable and configure NFS (v3/v4/v4.1), SMB/Samba, Object Storage (Swift), and CES floating IPs |
| **Install & Deploy** | Guided pre-check → install → enable daemon → deploy → verify flow using `spectrumscale install` / `spectrumscale deploy` / `scaleadmd enable` |
| **Post Configuration** | Set up GPFS PATH, create GUI admin users, tune `mmchconfig` performance parameters, configure health monitoring, NFS core dump collection, and AFM gateways (NFS or S3) |
| **Populate from Cluster** | CCR status check, then pull an existing cluster's configuration via `spectrumscale config populate` |
| **Upgrade** | Online (rolling, no downtime) or offline cluster upgrade via `spectrumscale upgrade` |
| **Pre/Post Checks** | Run standalone pre-checks and post-checks at any time |
| **Settings** | Toggle dry run mode, set toolkit binary path |

---

## Requirements

**On the installer node:**

- **IBM Storage Scale** — Developer Edition (free, up to 12 TB) or licensed. [Download →](https://www.ibm.com/products/storage-scale)
- **`spectrumscale` toolkit** — installed and accessible (produced by the Prepare Software steps)
- **Python 3.10+** — required for the setup service and the backend server
- **Flask 3.x** — `pip install "flask>=3.0,<4"` (backend server only)
- **SSH key-based auth** — from the installer node to all target nodes before running setup
- **`unzip`** — needed for package extraction (`sudo apt install unzip` / `sudo yum install unzip`)
- **Ansible compatibility** — ansible-core **2.23 or earlier** is required; ansible-core 2.24+ is incompatible with the toolkit

**On Ubuntu specifically:**

```bash
export LC_ALL=en_US.UTF-8      # set before installing
sudo apt install python3-apt   # required by the toolkit's Ansible playbooks
```

---

## Workflow Reference

```bash
# Prepare
spectrumscale setup -s <installer-ip>

# Build cluster definition
spectrumscale node add <hostname> -r <roles>
spectrumscale config gpfs -c <cluster-name>
spectrumscale nsd add -F <stanza-file>

# Install
spectrumscale install --precheck
spectrumscale install
spectrumscale install --postcheck

# Enable daemon (6.0.1+)
spectrumscale scaleadmd enable
spectrumscale nodeid define

# Deploy protocols
spectrumscale deploy --precheck
spectrumscale deploy
spectrumscale deploy --postcheck
```

Node role flags: `-n` NSD server, `-m` Manager, `-q` Quorum, `-a` Admin, `-p` Protocol (CES), `-g` GUI, `-e` EMS, `-c` Call Home

---

## Dry Run Mode

Dry Run is enabled by default. In this mode every button generates and displays the command that *would* run — nothing is sent to the cluster. Disable it in **Settings** once the command previews look correct.

> NSD creation and filesystem operations are **destructive and irreversible**. Always run pre-checks before disabling Dry Run.

---

## Backend Server

`scale-server.py` is a Flask app that runs locally on the installer node. It provides SSE-streaming endpoints that the GUI calls to execute `spectrumscale` commands and stream output back to the browser terminal.

**Security properties:**
- Binds to `127.0.0.1` only — not reachable from the network
- CORS restricted to `localhost`, `127.0.0.1`, and `file://` origins
- Credentials (GUI user passwords, S3 secret keys) are sent in POST request bodies, never in URLs or query strings
- All executed commands are explicit and allowlisted — no generic shell execution endpoint
- `config gpfs` flags are validated against an explicit allowlist — unrecognised flags are rejected before reaching the subprocess
- Node hostnames are validated against a strict regex (`[a-zA-Z0-9._-]`) before use in subprocess arguments or file paths
- `mmchconfig` values are validated to contain only alphanumeric characters and dots
- All user-supplied filesystem paths are validated against an allowlist of safe roots (`/tmp`, `/opt`, `/usr`, `/home`, etc.) to prevent path traversal
- `binpath` inputs for profile.d setup are restricted to safe characters via regex before use in any file operation
- SSH host key checking uses `accept-new` (new hosts accepted once; changed keys rejected) rather than disabling verification entirely

**The server is only needed for live execution.** In Dry Run mode the GUI generates command previews entirely in the browser with no server required.

---

## Connecting Remotely (SSH Tunnel)

The backend server binds to `127.0.0.1` only. To use the GUI from your workstation, forward the port over SSH:

```bash
# Interactive (tunnel closes when terminal closes)
ssh -L 5001:127.0.0.1:5001 user@installer-node

# Background (stays open)
ssh -fNL 5001:127.0.0.1:5001 user@installer-node
```

Then open `Scale-GUInstall.html` locally and leave the Backend URL as `http://127.0.0.1:5001`. The **Settings** page has a tunnel helper that generates the command for you and tests the connection.

### Firewall requirements

The SSH tunnel only requires **port 22 (SSH)** to be reachable on the installer node — no other ports need to be opened. If the node's firewall blocks SSH from your workstation, allow it:

**RHEL / CentOS / Fedora (firewalld):**
```bash
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
sudo firewall-cmd --list-all   # verify
```

**Ubuntu / Debian (ufw):**
```bash
sudo ufw allow ssh
sudo ufw status
```

> **Direct access without a tunnel (not recommended):** If you need to reach the server without SSH, you can open port 5001 and start the server bound to `0.0.0.0` — but this exposes an unauthenticated command-execution endpoint to the network. Only do this on an isolated management network with no untrusted access.
>
> ```bash
> # Open port 5001 (firewalld)
> sudo firewall-cmd --permanent --add-port=5001/tcp
> sudo firewall-cmd --reload
>
> # Start server on all interfaces
> PORT=5001 python3 scale-server.py --host 0.0.0.0   # requires modifying scale-server.py host binding
> ```

---

## File Structure

```
Scale-GUInstall/
├── Scale-GUInstall.html        # Self-contained single-file app (HTML + CSS + JS)
├── scale-server.py             # Backend server (Flask) for live command execution
├── start.sh                    # Convenience script: finds Python, installs Flask, starts server
├── CHANGELOG.md                # Release history (Keep a Changelog format)
└── packaging/
    ├── build-pkg.sh            # Builds RPM and DEB packages into dist/
    ├── scale-guinstall.spec    # RPM spec
    ├── scale-guinstall.service # systemd unit (installed but not enabled by default)
    ├── scale-guinstall-wrapper # /usr/bin/scale-guinstall installed by package
    ├── scale-guinstall.1       # man page source (troff)
    └── debian/                 # DEB control files (control, postinst, prerm, postrm)
```

---

## Notes

- The GUI uses IBM Carbon Design System tokens and IBM Plex fonts for a native-looking IBM interface.
- The tool targets IBM Storage Scale 6.0.1 and the `spectrumscale` Installation Toolkit.
- Official IBM documentation: [IBM Storage Scale 6.0.1 docs →](https://www.ibm.com/docs/en/storage-scale/6.0.1)
