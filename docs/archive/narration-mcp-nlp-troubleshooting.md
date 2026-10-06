# Narration Script — Debugging a Tool Through the Same MCP Server

> **Historical source material.** For the edited presentation, use the [curated recordings](../walkthroughs/README.md). Original recordings and narration are retained for provenance; see the [archive corrections](README.md) before reusing their examples.

Companion narration for
[`recordings/mcp-nlp-troubleshooting.cast`](recordings/mcp-nlp-troubleshooting.cast),
a terminal reenactment of one real debugging session: the `test_connection`
tool reported "SSH connection failed" on nodes that another tool reached fine.
Every call and result on screen is real, and the operator's words are their own
(the messages are quoted as sent). The agent's code reading and fix are shown as
short notes, since they are not MCP calls.

Narration-paced like the other recordings: read each section aloud while it is
on screen.

---

### Intro

"This is a short debugging session, run through the same MCP server. A tool the
agent had been using all along, test connection, kept saying SSH had failed,
while another tool reached the same machines fine. Here is how plain requests
and a few real calls found out why."

### `== 1. The symptom ==`

"The operator's request is four words: yes, fix the test connection. The agent
starts by reproducing it, on two nodes. Both say SSH connection failed, exit
two fifty-five, with no output at all. And by now GPFS is running on every
node, so the old explanation, that GPFS just isn't installed yet, is ruled
out."

### `== 2. Comparing the two tools ==`

"No tool calls here, just reading the backend code. The tool that works passes
no port and no user, so ssh's own configuration decides. The one that fails
forces port twenty-two and root, and it treats any non-zero exit from the
remote mmgetstate as an SSH failure. Two suspects."

### `== 3. Ground truth from the operator ==`

"The operator then runs the check by hand and pastes the result, after
correcting the agent's first version of the command. All seven nodes are
active. And in the ssh warning is the clue: the nodes are being reached on port
twenty-two twenty-three, not twenty-two."

### `== 4. Two experiments ==`

"Two read-only experiments with the existing tool. Port twenty-two twenty-three
works: the full table and both checks green. Then the same port with a regular
user instead of root: the tool says SSH connection failed, but the real message
is permission denied from mmgetstate. That proves the second suspect. A failing
remote command was being reported as an SSH failure."

### `== 5. The fix ==`

"The fix has two parts. Port and user become optional and are only passed to
ssh when someone supplies them, so the installer's own configuration decides,
the same as the tool that already worked. And reachability is checked first
with a plain true, then mmgetstate runs as its own step, so the two failures
can no longer be confused. Regression tests go in on both sides."

### `== 6. After the redeploy ==`

"After the operator redeploys the backend, the agent runs it again. The new
backend is clearly live, because the plain reachability step now appears. But
the command still shows port twenty-two and root. The agent's own tool client
is the old version and still sends those defaults. Passing empty values
explicitly exercises the new path, and all three nodes pass."

### `== 7. After the restart ==`

"The operator restarts the MCP server. Now the bare call, just a node name,
works. Ssh decides the port, SSH is reachable, and GPFS is active on all seven
nodes."

### Closing

"A symptom described in one sentence, a few read-only experiments, and one
confirmation from the operator turned a confusing exit two fifty-five into two
real bugs and a verified fix."
