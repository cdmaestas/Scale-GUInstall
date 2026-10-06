# Historical recording archive

These originals remain unchanged for provenance and existing links. Start with the [curated walkthroughs index](../walkthroughs/README.md) for a current presentation. Do not use these older examples as an unqualified setup recipe.

| Historical original | Cast | GIF | Replacement / context |
|---|---|---|---|
| Original fast runbook | [Source](recordings/techzone-runbook-walkthrough.cast) | [1:10](recordings/techzone-runbook-walkthrough.gif) | [Terminal overview](../walkthroughs/cli/overview.html); original failed run, compressed pacing |
| CES/NFS investigation | [Source](recordings/techzone-runbook-walkthrough-2.cast) | [5:35](recordings/techzone-runbook-walkthrough-2.gif) | [Condensed case](../walkthroughs/mcp/ces-nfs-case-study.html) |
| Clean instructional runbook | [Source](recordings/techzone-runbook-walkthrough-clean.cast) | [3:34](recordings/techzone-runbook-walkthrough-clean.gif) | [Updated overview](../walkthroughs/cli/overview.html) |
| Six MCP examples | [Source](recordings/mcp-nlp-walkthrough.cast) | [2:23](recordings/mcp-nlp-walkthrough.gif) | [Unique extra examples](../walkthroughs/mcp/extra-examples.html) |
| Full MCP installation | [Source](recordings/mcp-nlp-live-install.cast) | [5:04](recordings/mcp-nlp-live-install.gif) | [Combined install and debugging](../walkthroughs/mcp/install-and-debug.html) |
| MCP diagnostic repair | [Source](recordings/mcp-nlp-troubleshooting.cast) | [3:16](recordings/mcp-nlp-troubleshooting.gif) | [Combined install and debugging](../walkthroughs/mcp/install-and-debug.html) |

## Corrections to keep with historical material

- Original runbook: the storage-server role summary and displayed `-p` flag disagree; its export pool uses protocol-node addresses implicated in that failed run. Its postconfiguration example also has a duplicated prompt and PATH-expansion ambiguity. The bastion-local GPFS-command limitation remains documented in the runbook, but these old examples should not be copied as setup instructions.
- Second runbook: ping timeout does not prove an address free; unassigned addresses describe that failed run, not universal deployment behavior. Healthy SMB alone does not prove the network configuration correct. Its final successful deployment covers NFS and SMB only.
- Clean runbook: the sequence is a synthesized instructional reenactment with prerequisites omitted, not a literal complete live run. NSD failure groups and placement do not by themselves demonstrate replication. The old scratchpad narration from the earlier voice session does not match the added postcheck sections.
- MCP montage: section 4's “Deciding on cluster roles” heading actually describes starting deployment. The “two words” narration does not match the displayed four-word request. The current shortened reel omits those duplicate scenes.
- MCP live install: requests in original sections 2, 4 and 5 are reconstructed. `perfmon_node` is historical and no longer supported by the current MCP interface. The SSH test bug is historical and fixed. The account's task recap and final health checks must accompany its ASYNC FAILED line.
- MCP troubleshooting: shown commit/test counts describe the historical fix. Backend redeploy and MCP restart are distinct steps, preserved in the combined story.

The [capture log](nlp-capture-log.md) records provenance; the [cleanup report](recordings-cleanup-report.md) describes validation. Original binary history was neither removed nor rewritten.
