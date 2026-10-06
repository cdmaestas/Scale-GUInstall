# Narration Script — GUI Click-Through Walkthrough

Companion narration for
[`recordings/gui-walkthrough.html`](player.html), a
self-paced slideshow of the nine screenshots in
[`gui-walkthrough.md`](README.md). Open the recording in a
browser and screen-record it while reading this aloud — each slide
holds for roughly as long as its narration takes to read, the same
pacing convention used for the terminal `.cast` recordings.

---

### Intro

"This is a guided tour of the IBM Storage Scale installation interface. We’ll
look at the settings and controls you would use to prepare and configure a
cluster. These screens use a static demo, so no installation commands are
running."

### 1. Dashboard

"This is the toolkit’s dashboard — zero nodes, zero NSDs, zero filesystems,
and zero protocols configured. The workflow outlines Cluster Settings, Node
Configuration, NSD Storage, Filesystem, Protocols, and Install and Deploy.
The command preview on the right shows the commands the interface generates
as you configure the cluster."

### 2. Prepare Software

"We begin by preparing the installer node. This page brings together the
software download, working directory, and prerequisite checks. Before
installing, use these controls to check the Ansible version and locale, and
review the compatibility guidance shown here."

### 3. Cluster Settings

"Cluster-wide GPFS parameters, set once before anything else runs. Notice the
ephemeral port range is already defaulted to 60000 to 61000 — that's the fix
for the callhome and port-range precheck failure the real walkthroughs hit
on the first attempt, baked into the UI's defaults instead of left as a
trap."

### 4. Node Configuration

"Here are all seven nodes with their assigned roles: the two storage servers
as NSD, quorum, and manager nodes; the GUI node as quorum, admin, and the
GUI server; the two protocol nodes as manager and protocol; and the two
clients as client-only."

### 5. NSD Storage

"Next, we define the shared disks, or NSDs. Scan Block Devices lets you
discover disks across the storage nodes before choosing which ones to use.
In this example, filesystem configuration is set to happen later in the IBM
Storage Scale GUI, so this installer skips its filesystem step."

### 6. Protocol Services

"Here we prepare NFS, SMB, and S3. The command preview shows all three
selected. We’ve entered the shared root filesystem name, network interface,
and floating IP addresses. Review those commands before choosing Apply
Protocols. In live mode, configuration runs first, followed by protocol
enablement if configuration succeeds."

### 7. Install and Deploy — the install half

"This page brings the installation stages together. Start with the pre-check,
run the installation, then use the post-check to verify the result. The
command previews show what each button will run. The workflow also includes
enabling the admin daemon before moving on to deployment."

### 8. Post Configuration

"Once the cluster is installed, this page lets you save performance settings
for its caches, memory, and throughput. Saving them does not activate them
immediately. As the note explains, activation requires unmounting the
affected filesystems and restarting the GPFS daemon during a planned
maintenance window."

### 9. Install and Deploy — the protocol deploy half

"Back on Install and Deploy, these controls handle protocol deployment:
pre-check, Run Deploy, and post-check. Before a live deployment, make sure
the shared root filesystem and protocol prerequisites are ready. If you use
the Grafana Bridge, the note here explains why it needs to be enabled before
deployment."

### Closing

"That completes our tour of the installation interface: preparing software,
defining nodes and storage, configuring protocols, and reviewing the
controls for installation and deployment. The previews and guidance help you
check each step before running it against a live cluster."
