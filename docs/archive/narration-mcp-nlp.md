# Narration Script — MCP NLP-to-Tool-Call Walkthrough

> **Historical source material.** For the edited presentation, use the [curated recordings](../walkthroughs/README.md). Original recordings and narration are retained for provenance; see the [archive corrections](README.md) before reusing their examples.

Companion narration for
[`recordings/mcp-nlp-walkthrough.cast`](recordings/mcp-nlp-walkthrough.cast),
a scripted terminal reenactment of six real prompt → tool-call → result
exchanges from this project's TechZone sessions, pulled from
[`mcp-nlp-to-toolcall.md`](mcp-nlp-to-toolcall.md). Narration-paced the
same way as the other recordings in this project — read each section
aloud while its block is on screen.

---

### Intro

"This is a look at how plain-language requests to an AI agent become
real backend calls, through the Model Context Protocol. Every exchange
here is a real one, pulled from this project's own development
sessions against a live IBM Storage Scale cluster."

### `== 1. Staging the cluster nodes ==`

"The user describes what they want in plain English — two protocol
nodes, by hostname and IP. No toolkit syntax, no flags. The agent
turns that directly into a `start_node_config` call with the right
roles already filled in, then confirms the real result before
reporting back."

### `== 2. Disabling a known blocker mid-precheck ==`

"Here the agent had already explained that callhome was failing
precheck. The user's entire response is two words — 'disable it' —
and that's enough: the agent knows exactly which tool and which
parameter that maps to."

### `== 3. Resuming a long-running operation after a context gap ==`

"Long-running installs produce a lot of output — too much to read
back directly. The agent saves it to a file and greps for the lines
that actually matter, rather than flooding the conversation with a
wall of Ansible output."

### `== 4. Deciding on cluster roles from a one-line ask ==`

"Three words — 'yes deploy it' — and a real, seventeen-minute
protocol deploy starts. The agent only gets here because the
precheck already passed clean; the plain-language shorthand only
works because the groundwork was already verified."

### `== 5. Enabling a new protocol on an already-running cluster ==`

"Adding S3 to a cluster that already has NFS and SMB running. The
request comes in two parts, a few turns apart, and the agent chains
three separate tool calls — enable, precheck-deploy, deploy — to
actually get there."

### `== 6. Verifying a phase that had never been run before ==`

"And the last one: a question — 'should we patch in pre and post
checks?' — that the agent could have answered from documentation
alone, but didn't. It ran both phases live first, for real evidence,
before writing anything down."

### Closing

"The shape is the same every time: plain language in, the smallest
matching tool call out, and a real result read back in kind. The
person never has to know the tool exists, let alone what its
parameters are called."
