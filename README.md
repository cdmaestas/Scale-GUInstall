# Scale GUInstall — IBM Storage Scale Installation Toolkit GUI

A single-file web frontend for the IBM Storage Scale Installation Toolkit (`spectrumscale`). Open [Scale-GUInstall.html](Scale-GUInstall.html) in any modern browser to get a guided, form-driven interface for installing, deploying, and upgrading IBM Storage Scale clusters.

> **Disclaimer:** This is an unofficial community helper tool. It is not an IBM product or service. All operations target real cluster infrastructure — read every command preview before executing.

---

## Features

| Section | What it does |
|---|---|
| **Dashboard** | Live summary of configured nodes, NSDs, filesystems, and protocols; workflow progress tracker |
| **Prepare Software** | Extract the Scale zip package, verify checksum, run the installer, and start the `spectrumscale` setup service |
| **Node Configuration** | Add nodes one at a time or via bulk import; assign roles (NSD, Manager, Quorum, Admin, Protocol/CES, GUI, EMS, Call Home); generates `spectrumscale node add` commands |
| **Cluster Settings** | Set GPFS cluster name, I/O profile, remote shell/copy binaries, port range, call home, performance monitoring, and file audit logging via `spectrumscale config gpfs` |
| **NSD Storage** | Define Network Shared Disks with server, disk path, failure group, usage type, and size; generates the NSD stanza file; discover partitions on a node via `/proc/partitions` |
| **Filesystem** | Configure GPFS filesystem name, mount point, block size, replication, metadata replication, inodes, and advanced options (quotas, compression, encryption, IAM) |
| **Protocol Services** | Enable and configure NFS (v3/v4/v4.1), SMB/Samba, Object Storage (Swift), and CES floating IPs |
| **Install & Deploy** | Guided pre-check → install → post-check → deploy → verify flow using `spectrumscale install` / `spectrumscale deploy` |
| **Post Configuration** | Set up GPFS PATH, create GUI admin users, tune `mmchconfig` performance parameters, configure health monitoring intervals, and set up AFM gateways (NFS or S3) |
| **Populate from Cluster** | Pull an existing cluster's configuration into the toolkit via `spectrumscale config populate` |
| **Upgrade** | Online (rolling, no downtime) or offline cluster upgrade via `spectrumscale upgrade` |
| **Pre/Post Checks** | Run standalone pre-checks and post-checks at any time |
| **Settings** | Toggle dry run mode, set toolkit binary path |

---

## Requirements

- **IBM Storage Scale** — Developer Edition (free, up to 12 TB) or licensed. [Download →](https://www.ibm.com/products/storage-scale)
- **`spectrumscale` toolkit** — installed and accessible on the installer node
- **Python 3.10+** — required on the installer node for the setup service
- **SSH key-based auth** — from the installer node to all target nodes before running setup
- **`unzip`** — needed for the package extraction step (`sudo apt install unzip` / `sudo yum install unzip`)
- **A local backend server** (optional) — the Prepare Software page connects to `http://127.0.0.1:5001` to execute shell commands. Without a backend, all other pages work as a command generator and the commands must be run manually.

---

## Quick Start

### New cluster installation

1. Open `Scale-GUInstall.html` in a browser and accept the disclaimer.
2. **Dry Run mode is on by default** — commands are previewed only. Disable in Settings when you're ready to execute.
3. Go to **Prepare Software** and work through Steps 1–4 to get `spectrumscale` installed and the setup service running.
4. Follow the sidebar workflow in order:

```
Node Configuration → Cluster Settings → NSD Storage → Filesystem → Protocol Services → Install & Deploy
```

5. On the **Install & Deploy** page, run Pre-check, then Install, then Post-check, then Deploy.
6. Use **Post Configuration** for environment PATH, GUI admin user, and tuning.

### Existing cluster

- Use **Populate from Cluster** to pull the current cluster state into the toolkit.
- Then use **Upgrade Cluster** for rolling or offline upgrades.

---

## Workflow Reference

```
spectrumscale setup -s <installer-ip>           # Step 4 of Prepare Software
spectrumscale node add <hostname> -r <roles>    # Node Configuration
spectrumscale config gpfs -c <cluster-name>     # Cluster Settings
spectrumscale nsd add -F <stanza-file>          # NSD Storage
spectrumscale install --precheck                # Install & Deploy
spectrumscale install
spectrumscale install --postcheck
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

## File Structure

```
Scale-GUInstall/
└── Scale-GUInstall.html   # Self-contained single-file app (HTML + CSS + JS)
```

The entire tool is one HTML file — no build step, no dependencies, no install. Copy it anywhere and open it in a browser.

---

## Notes

- The GUI uses IBM Carbon Design System tokens and IBM Plex fonts for a native-looking IBM interface.
- The tool targets IBM Storage Scale 6.x and the `spectrumscale` Installation Toolkit.
- Official IBM documentation: [IBM Storage Scale docs →](https://www.ibm.com/docs/en/storage-scale)
