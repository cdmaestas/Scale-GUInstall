# Narration Script — GUI Click-Through Walkthrough

Companion narration for
[`recordings/gui-walkthrough.html`](recordings/gui-walkthrough.html), a
self-paced slideshow of the nine screenshots in
[`gui-walkthrough.md`](gui-walkthrough.md). Open the recording in a
browser and screen-record it while reading this aloud — each slide
holds for roughly as long as its narration takes to read, the same
pacing convention used for the terminal `.cast` recordings.

---

### Intro

"This is the same golden path as the terminal walkthrough, but from
the web UI — `Scale-GUInstall.html` — driven and filled out exactly
as a real operator would, against a static demo server with no live
backend attached."

### 1. Dashboard

"This is the toolkit's dashboard — zero nodes, zero NSDs, zero
filesystems, zero protocols configured. The six-step installation
workflow across the top is the same golden path as the terminal
walkthrough: Cluster Settings, Node Configuration, NSD Storage,
Filesystem, Protocols, Install and Deploy. The command preview panel
on the right already shows the exact `spectrumscale` commands this UI
is going to generate."

### 2. Prepare Software

"Before touching the cluster at all, the toolkit itself needs to be
on the installer node. This page extracts the Developer Edition
package and runs the same ansible-core and locale prerequisite checks
the real runbook calls out — the ansible-core 2.23 pin and the
`LC_ALL` / `python3-apt` warning that trip up Ubuntu installer nodes."

### 3. Cluster Settings

"Cluster-wide GPFS parameters, set once before anything else runs.
Notice the ephemeral port range is already defaulted to
60000 to 61000 — that's the fix for the callhome and port-range
precheck failure the real walkthroughs hit on the first attempt,
baked into the UI's defaults instead of left as a trap."

### 4. Node Configuration

"All seven nodes, bulk-imported by hostname and then given their
golden-path roles: the two storage servers as NSD, quorum, and
manager nodes; the GUI node as quorum, admin, and the GUI server; the
two protocol nodes as manager and protocol; the two clients left as
client-only. Same role layout as every terminal walkthrough in this
project."

### 5. NSD Storage

"Disk discovery and NSD definition — this is also where the
filesystem layout happens, since NSDs are assigned to a filesystem as
they're created. Scan Block Devices runs `lsblk` across every
NSD-server node in parallel to list what's actually free, rather than
asking the operator to go find device paths by hand."

### 6. Protocol Services

"All three protocols enabled together — NFS, SMB, and S3 — with the CES
shared root filesystem, interface, and floating IP addresses filled in.
The Apply Protocols panel previews the exact config protocols and enable
commands, and in live mode runs them in that order, skipping enable if
config fails. Notice the inline warning under NFS: it calls out the
rpcbind package requirement directly, the exact root cause the second
terminal walkthrough spent an entire investigation uncovering."

### 7. Install and Deploy — the install half

"The six-stage pipeline: pre-check, install, post-check, enable
daemon, deploy, verify — laid out as a single flow instead of
separate pages, so it's obvious post-check isn't optional cleanup,
it's a first-class step between install and deploy. Each stage's real
`spectrumscale` command is shown before it runs."

### 8. Install and Deploy — the protocol deploy half

"Further down the same page: deploying the protocol services
configured earlier. Same pre-check, run, post-check shape as install.
The callout about the Grafana Bridge is another lesson learned baked
directly into the UI — enabling it alone doesn't activate it, only
this Deploy step does."

### 9. Post Configuration

"And last, the GPFS performance tunables — max files to cache, max
stat cache, pagepool, max MB per second — applied here because this
is the earliest point in the whole flow where a cluster and
filesystem actually exist to apply them to, right after install and
before deploy brings the protocols up."

### Closing

"The terminal walkthroughs prove the backend sequence is correct.
This one proves the UI asks for the same inputs in the same order,
and surfaces the same hard-won lessons right where an operator would
actually need them."
