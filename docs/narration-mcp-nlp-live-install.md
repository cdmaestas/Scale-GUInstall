# Narration Script — A Live Install, Driven in Plain Language

> **Historical source material.** For the edited presentation, use the [curated recordings](recordings/README.md). Original recordings and narration are retained for provenance; see the [archive corrections](recordings/ARCHIVE.md) before reusing their examples.

Companion narration for
[`recordings/mcp-nlp-live-install.cast`](recordings/mcp-nlp-live-install.cast),
a terminal reenactment of one real end-to-end install on a fresh TechZone
environment: seven nodes, IBM Storage Scale 6.0.1.1, NFS, SMB, and S3, driven
by plain-language requests to an AI agent connected to the `scale-guinstall`
MCP server. Every call and result on screen is real. The operator's wording is
real for the prompts quoted in the capture log as the operator's own, and
reconstructed for steps the agent ran on its own initiative. The two mistakes
in section 7 actually happened and are left in on purpose.

Narration-paced like the other recordings: read each section aloud while it is
on screen.

---

### Intro

"This is a real install, driven by plain-language requests to an AI agent
connected to the scale-guinstall MCP server. Seven nodes, IBM Storage Scale
6.0.1.1, NFS, SMB and S3, on a fresh TechZone environment. Everything on
screen is a real call and a real result. The operator says what they want, and
the agent picks the tool."

### `== 1. Pre-flight check ==`

"The operator's first message is five words: the backend is up, check it. The
agent runs a handful of read-only calls: ping, which toolkit is installed,
ansible and locale, and what the cluster definition looks like. It's a fresh
environment. No nodes, no cluster, and callhome still on by default."

### `== 2. Nodes and disks ==`

"Next the operator wants to know the machines are usable. The agent lists block
devices on every node over SSH. The two storage servers each have three unused
hundred-gigabyte disks, and the other five have only their OS disk. One honest
wrinkle: the connection-test tool reported an SSH error on two hosts, even
though the device listing reached them fine, so the agent trusted the working
path and moved on."

### `== 3. The hosts file ==`

"Then the operator pastes the environment's hosts file and says the S3 media is
present. There's no tool call here, because the agent just reads it. It picks
out the two pre-allocated addresses named ces dot scale dot lab as the protocol
floating IPs, notes that they sit on the second interface, and leaves the
Windows client out."

### `== 4. Toolkit setup ==`

"Setting up the toolkit. The agent previews with a dry run first, inputs
validated and nothing executed, then runs it for real. A few seconds later the
install service is ready."

### `== 5. Seven nodes ==`

"Seven nodes with their roles: two storage servers that are also quorum and
manager, one GUI and admin node, two protocol nodes, and two plain clients. The
dry run shows exactly which toolkit flags each role becomes. The live run
prints a FATAL for each node that doesn't exist yet. That's expected, because
it's a delete before the add."

### `== 6. Storage ==`

"Here is a request in the operator's own words: add the storage for the NSDs.
The agent turns that into six NSDs. One disk per server goes to a small shared
root filesystem, two go to the main one, and the two servers sit in separate
failure groups so everything mirrors."

### `== 7. Cluster settings, and two real mistakes ==`

"Keep going through the runbook. And here is a real mistake, left in. The agent
asks for a profile with the wrong spelling, and a performance monitoring node
flag that this toolkit version doesn't have. The toolkit refuses both, in plain
terms. The agent reads the errors, sees the profile was already set
automatically, drops both arguments, and the rerun succeeds. Callhome is off
and the port range is set."

### `== 8. Protocols from the web UI ==`

"Protocols come from the web UI this time. The Apply Protocols panel sends two
requests to the same backend: configure the shared root, mountpoint, interface
and the two floating addresses, then enable NFS, SMB and S3. Both succeed, and
the cluster definition now shows all three protocols enabled."

### `== 9. Precheck and install ==`

"The precheck passes on the first try with nothing but expected warnings.
Install then runs about twenty-six minutes. The log is far too large to read,
so the agent saves it to a file and searches for failures and the final recap,
and a cheap process check tells it when the run is done."

### `== 10. Postcheck and deploy precheck ==`

"The postcheck confirms GPFS, the NSDs, performance monitoring and the GUI are
really up. The deploy precheck then clears the protocol checks for S3, SMB and
NFS, which is exactly where a missing rpcbind would have shown up."

### `== 11. Deploy ==`

"Deploy takes seventeen and a half minutes. Filesystem, Cluster Export
Services, S3, SMB, NFS, performance monitoring and the GUI all come up active,
with zero failures on any node. One log line says async failed. The agent
checks the context, sees the task still reports changed and the recap is clean,
and moves on."

### `== 12. Final postcheck ==`

"One last postcheck for the deploy confirms every protocol independently. All
services running."

### Closing

"Start to finish: a full install, one web page, and a handful of plain
sentences from the operator. The agent picked the tools, caught its own two
mistakes from the toolkit's error messages, and no command was typed by hand."
