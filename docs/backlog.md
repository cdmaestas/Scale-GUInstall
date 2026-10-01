# Backlog

## TechZone CES export IP discovery and validation

**Priority:** High  
**Status:** Reproduce and validate on the next TechZone reservation

The current TechZone runbook can configure the protocol nodes' `eth1`
addresses as the CES `export_ip_pool`. That is unsafe when those addresses
are already assigned to the interfaces by DHCP: CES requires separate,
resolvable, unclaimed floating addresses.

### Evidence from reservation `3ag73k3k`

- IBM Storage Scale 6.0.1.1 installed successfully on all seven nodes.
- Filesystems, GPFS, S3, SMB, performance monitoring, and the GUI became
  active.
- Deploy failed its final health checks with CES and NFS not active.
- Both protocol nodes reported `CES FAILED` with
  `ces_network_ips_not_assignable`, `nfsd_down`, and `portmapper_down`.
- CES was configured on `eth1` with `10.249.128.110` and
  `10.249.128.111`.
- `/etc/hosts` described those addresses both as protocol-node secondary
  addresses and as `ces-proto1.scale.lab` / `ces-proto2.scale.lab`.

### Work for the next reservation

1. Before `spectrumscale config protocols`, capture on both protocol nodes:
   `nmcli device status`, `ip -4 addr show dev eth1`, and routes to the
   proposed CES addresses.
2. Confirm whether bringing `eth1` up causes DHCP to claim either proposed
   CES address.
3. Identify two genuinely unused addresses on the `eth1` subnet and ensure
   they resolve through `/etc/hosts` or DNS before adding them to CES.
4. Add a read-only backend/MCP preflight that rejects an export IP when it
   is already assigned to any node or is not routable through the selected
   interface.
5. Update the main TechZone procedure so it never assumes that a
   `*-secondary` `/etc/hosts` entry is a free floating address.
6. Validate recovery after a failed deploy: correct the addresses, clear
   protocol-node `Failed` flags (suspend/resume if required), rerun deploy,
   and confirm CES and NFS are active.

### Acceptance criteria

- CES export addresses are proven unclaimed before deployment.
- The MCP/backend preflight catches the known bad-address configuration.
- Deploy finishes with filesystem, CES, NFS, SMB, S3, monitoring, and GUI
  all active.

## Client-side protocol sanity check after deploy

**Priority:** Medium
**Status:** Not started

Every walkthrough built so far (clean and real) stops at "the toolkit
reports every component `ACTIVE`" — none of them actually prove a client
can use NFS, SMB, or S3. `scale-client1`/`scale-client2` are staged in
the cluster but have never been touched after node config.

### Known gap before this can run

`spectrumscale enable nfs smb s3` only turns on the protocol daemons —
it does not create an actual NFS export or SMB share on `fs1`. An
export/share needs to be created first (`mmnfs export add`, `mmsmb
export add`) or a client mount attempt will fail with "no such export,"
which wouldn't prove anything about deploy quality, just that this
extra step was skipped.

### Work

1. Check current state: `mmnfs export list` / `mmsmb export list` on an
   admin node, to confirm whether an export/share already exists on
   `fs1` from the earlier sessions.
2. If none exists, create a minimal NFS export and SMB share on `fs1`.
3. From `scale-client1`, mount the NFS export, write/read/delete a test
   file, then unmount.
4. From `scale-client1` (or `scale-win-client1`), connect to the SMB
   share and confirm read/write.
5. Basic S3 sanity check (e.g. `curl`/`aws s3 ls` against the S3
   endpoint) if credentials/setup allow without excessive scope.
6. If all of the above pass, add this as a final section to the clean
   walkthrough (narration + recording), consistent with the live-first
   pattern used for S3 and the postchecks.

### Acceptance criteria

- A real client can mount/read/write NFS and SMB after deploy.
- The clean walkthrough's recording/narration reflects this as the
  actual proof-of-success step, not just toolkit-reported `ACTIVE`.
- The runbook contains one unambiguous, verified export-IP procedure.
