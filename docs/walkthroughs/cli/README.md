# CLI walkthrough

The raw `spectrumscale` toolkit sequence on the installer node, in order, with the verification at each stage. It is what the GUI and the MCP tools run underneath. Follow the [TechZone runbook](../../techzone-runbook.md) for the real procedure and its gotchas.

| Recording | Length | Chapters | Watch | Narration |
|---|---:|---:|---|---|
| **Clean terminal installation overview** | 3:01 | 9 | [Player](overview.html) · [GIF](overview.gif) · [cast](overview.cast) | [Script](overview.narration.md) |

## The sequence it follows

1. Start the toolkit setup service
2. Configure seven nodes
3. Define NSDs and filesystem placement
4. Precheck and install
5. Verify the installation
6. Configure and precheck the protocols
7. Deploy the services
8. Verify the final state

## Read this before trusting a detail

This is an **instructional reenactment** with prerequisites assumed, not a literal complete run. Disk placement is not proof of replication, so check replica settings separately, and a silent `ping` does not prove an address is free.

The original terminal recordings it replaces, including two from failed or troubleshooting runs, are kept unchanged in the [archive](../../archive/README.md) with their corrections listed.
