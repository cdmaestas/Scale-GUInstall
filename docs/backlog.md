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
- The runbook contains one unambiguous, verified export-IP procedure.
