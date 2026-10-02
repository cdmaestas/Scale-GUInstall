# From Plain English to Backend Action: MCP Tool Calls in Practice

A walkthrough of how natural-language requests, given to an AI agent
(Claude) connected to the [`scale-guinstall` MCP server](../mcp-server/),
turned into real `scale-server.py` backend calls during the live
TechZone sessions this project's other walkthroughs are built from.

Nothing here is paraphrased after the fact — every "User said" / "Claude
called" pair below is a real exchange from this project's development
sessions, reduced to the essential ask and the tool call it produced.
The full tool signatures are documented in
[`mcp-server/README.md`](../mcp-server/README.md); this doc is about the
*mapping* from intent to call, not the API reference.

## Why this matters

The MCP server is a thin client — every tool call is a stateless
HTTP/SSE request to the same backend the web UI talks to. The
interesting part isn't the wire protocol, it's that a person can drive
an entire cluster deployment by describing *what* they want, not *which
command* to run — the agent picks the tool, fills the parameters, and
reports back in plain language too.

---

### Staging the cluster nodes

**User said:**
> "ok the service is running on the zima cluster. let's take a look"
> ... (several turns later) "I do want to add two servers that will be
> protocol nodes. 172.16.0.21 zimabg1, 172.16.0.22 zimabg2."

**Claude called:**
```
start_node_config(
  toolkit="/usr/lpp/mmfs/6.0.1.1/ansible-toolkit/spectrumscale",
  nodes=[
    {"hostname": "zimabg1", "roles": ["protocol", "manager"]},
    {"hostname": "zimabg2", "roles": ["protocol", "manager"]}
  ],
  dry_run=false
)
```

**Result:** Both nodes added to the cluster definition with the
protocol and manager roles. The agent then used `check_operation` to
confirm the real run's output before reporting back.

---

### Disabling a known blocker mid-precheck

**User said:**
> "disable it for now" (in response to the agent explaining a callhome
> FATAL during `precheck-install`)

**Claude called:**
```
start_callhome(
  toolkit="/usr/lpp/mmfs/6.0.1.1/ansible-toolkit/spectrumscale",
  enable=false,
  dry_run=false
)
```

**Result:** `[ INFO ] Disabling the callhome.` — a two-word user
decision became the exact right toolkit call, with no need for the
user to know the underlying `spectrumscale callhome disable` command
existed.

---

### Resuming a long-running operation after a context gap

**User said:**
> "Check mcp__scale-guinstall__check_operation for the TechZone install
> run (new u6kj9s3k environment)."

**Claude called:**
```
check_operation()
```

**Result:** A large in-progress log (too big for one reply) was
automatically saved to a file; the agent then used `grep` against that
file for `FATAL|ERROR|PLAY RECAP|successful|status` rather than
re-reading the whole thing, and reported just the relevant lines back.
This pattern repeated dozens of times across both long `install` and
`deploy` runs in this project's sessions.

---

### Deciding on cluster roles from a one-line ask

**User said:**
> "yes deploy it"

**Claude called:**
```
start_phase(
  toolkit="/usr/lpp/mmfs/6.0.1.1/ansible-toolkit/spectrumscale",
  phase="deploy",
  dry_run=false
)
```

**Result:** The real, ~17-minute protocol deploy started. Three words
of user intent, confirmed as safe by the already-completed
`precheck-deploy`, became the actual production-affecting call —
no CLI syntax required from the user at any point.

---

### Enabling a new protocol on an already-running cluster

**User said:**
> "Test it live first on a fresh environment" ... "the old environment
> is still there. feel free to connect enable and capture it"

**Claude called:**
```
start_protocols_enable(
  toolkit="/usr/lpp/mmfs/6.0.1.1/ansible-toolkit/spectrumscale",
  protocols=["s3"],
  dry_run=false
)
```
followed by `start_phase(phase="precheck-deploy")` and
`start_phase(phase="deploy")` to actually activate it.

**Result:** S3 added cleanly to a cluster that already had NFS/SMB
`ACTIVE`, confirmed via `check_operation` showing `S3 ACTIVE` with
NFS/SMB undisturbed.

---

### Verifying a phase that had never been run before

**User said:**
> "should we patch in pre and post checks for install and deploy
> phases?" ... "Test live on u6kj9s3k first"

**Claude called:**
```
start_phase(toolkit=<toolkit>, phase="postcheck-install", dry_run=false)
# ...then, after confirming clean:
start_phase(toolkit=<toolkit>, phase="postcheck-deploy", dry_run=false)
```

**Result:** Both phases — never exercised anywhere in this project
before this request — ran clean on the first try, giving real captured
output to put in the walkthrough instead of guessed/illustrative text.
This is the pattern used throughout: when asked for something not yet
proven live, test it for real before writing it into documentation.

---

## The general shape

Across every example above, the same structure holds:

1. The user describes an outcome or a decision in plain language —
   never a `spectrumscale` flag or an MCP tool name.
2. The agent picks the smallest tool call that matches that intent,
   almost always previewing with `dry_run=true` first when the action
   is new or risky, then running for real once confirmed.
3. `check_operation` (or the tool's own return value for fast calls)
   closes the loop — the agent reads the real result and reports back
   in the same plain language the request came in.

The MCP layer never requires the user to know which of the ~43 tools
exists, what its parameters are called, or what the underlying
`spectrumscale`/`mm*` command looks like — that mapping is the agent's
job, every time.

## Watching the recording

[`recordings/mcp-nlp-walkthrough.cast`](recordings/mcp-nlp-walkthrough.cast)
is a scripted terminal reenactment of the six exchanges above, built
the same way as the TechZone terminal walkthroughs: narration-paced
(~2m24s total) so it can be played and talked over live. The companion
script is [`narration-mcp-nlp.md`](narration-mcp-nlp.md).

```bash
brew install asciinema   # if you don't already have it
asciinema play docs/recordings/mcp-nlp-walkthrough.cast
```

### A full install, end to end

[`recordings/mcp-nlp-live-install.cast`](recordings/mcp-nlp-live-install.cast)
(~5 minutes, narration in
[`narration-mcp-nlp-live-install.md`](narration-mcp-nlp-live-install.md))
walks one complete install on a fresh TechZone environment — setup, seven
nodes, NSDs, cluster settings, protocols from the web UI, then every
precheck, install, deploy, and postcheck phase. The calls and results are
real. The operator's wording is real for the prompts it quotes as theirs
(the backend check, the hosts paste, "add the storage for the NSDs", and
"keep going through the runbook") and reconstructed for steps the agent ran
on its own initiative. The two mistakes in the cluster-settings section
really happened and are left in.

```bash
asciinema play docs/recordings/mcp-nlp-live-install.cast
```

A silent animated rendering of the same cast is at
[`recordings/mcp-nlp-live-install.gif`](recordings/mcp-nlp-live-install.gif)
(~5.8 MB, 983×739, the same ~5-minute pacing, made with
`agg --idle-time-limit 60 --font-size 16 --last-frame-duration 16`), for
viewing without asciinema installed or for screen-recording under the
narration.

### Debugging a tool through the same server

[`recordings/mcp-nlp-troubleshooting.cast`](recordings/mcp-nlp-troubleshooting.cast)
(~3 minutes, narration in
[`narration-mcp-nlp-troubleshooting.md`](narration-mcp-nlp-troubleshooting.md))
follows one real debugging session from the same install: `test_connection`
kept reporting "SSH connection failed (exit 255)" on nodes that `list_devices`
reached fine. A few read-only calls and one pasted command from the operator
traced it to a forced `-p 22` / `root@` that overrode the installer's ssh
config (the nodes' sshd is on 2223), and to a failing remote `mmgetstate`
being reported as an SSH failure. The operator's messages are quoted as sent;
the code reading and fix are shown as notes since they are not MCP calls.

```bash
asciinema play docs/recordings/mcp-nlp-troubleshooting.cast
```
