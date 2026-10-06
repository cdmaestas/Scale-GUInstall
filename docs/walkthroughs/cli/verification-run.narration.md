# Narration script: verification recording

Companion to [`verification-run.gif`](verification-run.gif) and [`verification-run.cast`](verification-run.cast). Each command holds for about seven seconds after its output appears, so read the passage for a command while it is on screen.

**How it was made.** The recording script ran six read-only Cluster commands live, over SSH from the operator's Mac through the installer node to `scale-proto1`, about an hour after the deploy. The output is real and unedited. The prompt and the typing are drawn by the recording script, and the screen is cleared between commands; the SSH hops themselves are not shown.

### 1. `mmgetstate -a`

"All seven nodes report GPFS active: the GUI node, both storage servers, both clients and both protocol nodes."

### 2. `mmlsfs all -T`

"Two filesystems exist and are mounted by default: cesSharedRoot, which holds the shared protocol state, and fs1."

### 3. `mmces address list`

"Both export addresses are assigned, one to each protocol node. An unassigned address is the failure the runbook warns about, and it did not happen here."

### 4. `mmces service list -a`

"NFS, SMB and S3 are enabled and running on both protocol nodes."

### 5. `mmhealth node show`

"The node's overall status is still TIPS, but only because of GPFS: the maximum files to cache and the total memory are small, which is a consequence of the lab machines. CES, the network, the filesystem and performance monitoring are healthy."

### 6. `mmhealth node show SMB -v`

"SMB is healthy. The events show the SMB perfmon sensors became active at 18:58:27, fifty minutes after the earlier TIPS status began at 18:08:27. Nothing was changed in between, so that TIPS cleared on its own."
