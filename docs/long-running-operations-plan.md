# Long-running operations and workflow plan

## Status

Proposed implementation plan. This document describes the intended design; it
does not change the behavior of the backend, web UI, or MCP server by itself,
except for two pieces that close the specific danger (a real operation's
watcher losing its connection and, via `stream_process()`'s abandoned-
connection safety net, getting the still-running child killed) without
implementing any of the architecture below:

- The "interim guard" described under MCP changes has landed
  (`ScaleBackendClient.open_stream` now opens with no read timeout, connect/
  write/pool unchanged; `_drain_stream` logs instead of silently swallowing a
  lost connection).
- The same danger existed for the web UI via a different mechanism — not a
  client-side timeout (the web UI's `fetch()`-based streaming has none), but
  an idle NAT/firewall silently dropping the SSH tunnel itself during a long
  quiet phase. Every documented and generated tunnel command now includes
  `-o ServerAliveInterval=30 -o ServerAliveCountMax=3`.
- Both fixes were verified together against a real cluster on 2026-09-22: a
  `spectrumscale install` run over the MCP+tunnel path completed successfully
  after 27m23s of continuous streaming (5 nodes, zero Ansible failures, GPFS/
  perfmon/GUI all active at the end) with no connection drop and no premature
  kill. A `precheck-install` re-run immediately before it also completed
  cleanly. No further incident of the "broken cluster" symptom was observed.

Phases A–D are still unstarted.

## Problem statement

Long-running commands such as `spectrumscale install`, `deploy`, and their
pre/post checks currently run inside the Flask SSE response generator. The
backend only continues consuming the child process while an HTTP client keeps
that response open and reads it.

The MCP server tries to make this fire-and-forget by reading the first event,
returning from the tool call, and draining the remaining SSE response in an
in-process asyncio task. That arrangement has several failure modes:

- `ScaleBackendClient` constructs `httpx.AsyncClient` with a 30-second timeout,
  including the streaming read timeout. A quiet command can therefore terminate
  the MCP drain even while the backend command is healthy.
- If the MCP process exits, restarts, loses its tunnel, or sleeps, the drain is
  lost.
- If any HTTP/SSE consumer disconnects, the backend generator can be abandoned.
  `stream_process()` then kills its child in `finally`, so client lifetime and
  operation lifetime are unintentionally coupled.
- A disconnected response can leave `_current_operation` reporting `running`
  without making further progress, requiring manual reconciliation.
- The operation state exists only in memory and is lost on backend restart.
- The current buffer has no explicit cancellation, workflow step, heartbeat,
  bounded log policy, or recovery semantics.

The observed install test demonstrated this exact class of failure: the command
was accepted, the MCP drain raised `httpx.ReadTimeout`, and the backend operation
remained `running` with stale output while toolkit processes were still visible.

## Goals

1. A started operation continues independently of the HTTP client that started
   or watches it.
2. Starting a real operation returns promptly with a stable operation ID.
3. Web and MCP clients can reconnect and retrieve consistent progress.
4. Only one mutating operation can run at a time, as today.
5. Dry runs remain synchronous, side-effect-free previews.
6. Install, deploy, and upgrade can run as explicit precheck/main/postcheck
   workflows, with clear stop and resume behavior.
7. Cancellation is explicit, authenticated, and terminates the full process
   group rather than one wrapper PID.
8. Backend restarts produce a truthful recoverable state instead of silently
   reporting idle.
9. Existing web UI behavior can migrate without a flag day.

## Non-goals

- Running multiple mutating toolkit operations concurrently.
- A distributed job queue or external message broker.
- Automatically fixing cluster prerequisites or retrying failed toolkit steps.
- Automatically skipping SSH validation.
- Preserving an operation across a reboot by automatically relaunching its
  command. Recovery reports and reconciles state; it does not guess whether a
  command is safe to rerun.

## Proposed architecture

### 1. Backend-owned operation manager

Move ownership of real mutating commands out of request generators and into an
`OperationManager` in `scale-server.py` (it can be extracted into a module after
the behavior is stable).

The manager should:

- atomically validate and claim the single-operation slot;
- create an operation record before spawning work;
- start a managed worker thread for the operation and define graceful shutdown
  behavior explicitly;
- launch each child in a new process session/process group;
- continuously drain combined stdout/stderr into the operation log;
- record PID/process-group ID, current step, exit code, and timestamps;
- release the slot in a worker-level `finally`, independent of HTTP lifetime;
- expose immutable snapshots under the existing lock;
- enforce a bounded in-memory log while writing the complete log to disk.

The HTTP start request should never own the subprocess. It should return only
after the operation has been accepted and the worker has been created.

### 2. Operation record

Use a versioned record with at least:

```json
{
  "schema_version": 1,
  "id": "stable-random-id",
  "name": "workflow:install",
  "source": "mcp",
  "status": "queued|running|cancelling|success|error|cancelled|interrupted",
  "created_at": "ISO-8601",
  "started_at": "ISO-8601|null",
  "updated_at": "ISO-8601",
  "finished_at": "ISO-8601|null",
  "current_step": "precheck-install|null",
  "steps": [],
  "pid": 1234,
  "pgid": 1234,
  "rc": null,
  "message": "",
  "log_path": "/var/log/scale-guinstall/operations/<id>.log",
  "lines": [],
  "cancel_requested": false,
  "options": {
    "skip_ssh": true,
    "callhome": false
  }
}
```

Do not put secrets, auth tokens, environment dumps, or command input containing
credentials in the record or log.

Keep `lines` as a bounded tail for compatibility and add a monotonically
increasing line sequence number so clients can request only new output.

### 3. Persistence and restart reconciliation

Persist the current and most recent completed operation atomically to a backend
state directory, using write-to-temporary-file plus rename. The state directory
must be root-owned and not web-accessible.

On backend startup:

1. Load and validate the last operation record.
2. If it was terminal, expose it as history/current-most-recent.
3. If it was `queued`, `running`, or `cancelling`, inspect its recorded process
   group and the existing `_running_spectrumscale()` result.
4. Never silently relaunch it.
5. If no matching process remains, mark it `interrupted` with a recovery note.
6. If a matching process remains but the backend cannot safely reattach its
   output pipes, report `interrupted`/`external_process_running` and keep new
   mutations blocked until an operator reconciles or cancels it.

Persisting state does not make a `Popen` pipe reattachable. Correct status and a
safe lock after restart are the required first version.

### 4. Start and status API

Add JSON job endpoints and keep SSE as an optional observation transport:

- `POST /api/operations` validates and starts one command or workflow.
- `GET /api/operations/current` returns the current/most recent record.
- `GET /api/operations/<id>` returns a specific record.
- `GET /api/operations/<id>/lines?after=<sequence>&limit=<n>` returns incremental
  output without sending the full log every poll.
- `GET /api/operations/<id>/events?after=<sequence>` optionally streams stored
  and new events. Disconnecting this endpoint must not affect execution.
- `POST /api/operations/<id>/cancel` requests cancellation.

Return `202 Accepted` with `{ "started": true, "operation_id": "..." }` for a
new real operation. Return `409 Conflict` plus the active operation snapshot
when the slot is busy. Continue returning structured validation failures without
starting a worker.

Keep `/api/operation/current` as a compatibility alias during migration.

### 5. Cancellation

Start children in a new process session. Cancellation should:

1. change state to `cancelling` and persist it;
2. send SIGTERM to the recorded process group;
3. wait for a configurable grace period;
4. send SIGKILL to the process group if it remains alive;
5. drain/reap the child;
6. finish as `cancelled`, including the signal and timestamps.

Validate that the recorded PID/PGID and command identity still match before
signalling. Never target a PID obtained solely from stale persisted state.

The existing `kill_spectrumscale` tool remains an emergency recovery mechanism,
not the normal cancellation path.

## Workflow model

### Supported workflows

| Workflow | Precheck | Main | Postcheck |
|---|---|---|---|
| install | `precheck-install` | `install` | `postcheck-install` |
| deploy | `precheck-deploy` | `deploy` | `postcheck-deploy` |
| upgrade | `upgrade-precheck` | `upgrade-run` | `upgrade-postcheck` |

Keep `enable-daemon`, `nodeid-define`, and `upgrade-showversions` as individual
operations unless a documented toolkit workflow requires otherwise.

### Workflow request

Expose an MCP/backend request shaped approximately as:

```json
{
  "workflow": "install",
  "run_precheck": true,
  "run_main": true,
  "run_postcheck": true,
  "skip_ssh": false,
  "expected_callhome": false,
  "dry_run": true
}
```

Semantics:

- At least one phase must be selected.
- Execute selected phases serially in their canonical order.
- Stop on the first nonzero exit code.
- Do not automatically continue past a failed precheck or main phase.
- Record each step's status, timestamps, command, and return code.
- `skip_ssh` must be explicit and is passed only to phases that support it.
- `expected_callhome` is a precondition, not an instruction to silently change
  cluster configuration. Refuse to start if observed configuration differs.
- A dry run returns the complete ordered command preview synchronously and does
  not claim the operation slot.
- A real run returns one workflow operation ID immediately.

### Resume behavior

Do not implement blind automatic retry. Provide a new request that names the
desired starting phase, or let the caller select only the remaining phases.
Include `resumes_operation_id` in the new record for auditability. Revalidate
cluster state and all safety preconditions before resuming.

## MCP changes

Replace the current `_mutate()` streaming/drain pattern for real operations:

- dry run: retain the synchronous preview response;
- real run: send the JSON start request and return its operation ID;
- progress: poll `get_operation(operation_id, after_line=...)`;
- cancellation: add an explicitly mutating `cancel_operation` tool with
  `dry_run=True` by default;
- workflow: add `start_workflow` while retaining `start_phase` for advanced or
  recovery use.

Remove `_background_tasks` and `_drain_stream()` after all real mutating
endpoints use backend-owned jobs.

As an interim guard before that migration is complete, configure streaming
requests with `read=None` and catch/log drain task exceptions. This mitigation
must not be treated as completion of the design because MCP process lifetime
would still control the connection.

## Web UI changes

- Start operations through the JSON job endpoint.
- Render progress by polling incremental lines or subscribing to the observer
  SSE endpoint.
- On page reload, retrieve the current operation and resume observation.
- Display workflow and per-step status, not just a flat stream.
- Show explicit controls for precheck/main/postcheck and `skip_ssh`.
- Make cancellation a separate confirmation flow.
- Clearly distinguish `error`, `cancelled`, and `interrupted/reconciliation
  required`.

## Compatibility and migration

Implement in stages so the web UI and MCP server can migrate independently:

1. Add the operation manager, persistence, job status API, and tests without
   changing existing endpoints.
2. Add a backend adapter that runs one existing phase through the manager.
3. Migrate `start_phase`/install-deploy-upgrade first because they are the
   longest-running and reproduced the failure.
4. Add workflow orchestration and migrate the MCP tools.
5. Migrate the web UI to job start plus detached observation.
6. Migrate the other mutating endpoints (`setup`, node config, NSD operations,
   cluster config, and format disk).
7. Retire real-run execution through request-owned SSE generators. Retain SSE
   only as an observer of backend-owned state.

During migration, both old and new paths must use the same single-operation
manager and `_running_spectrumscale()` guard so they cannot race.

## Test plan

### Unit tests

- atomic claim rejects a second operation;
- worker continues after the start request returns;
- disconnecting an SSE observer does not stop or signal the child;
- quiet child output exceeding 30 seconds does not fail the operation;
- output sequence numbers are ordered and incremental reads have no gaps;
- log tail is bounded while the complete file is retained;
- success, nonzero exit, exception, cancellation, and forced-kill transitions;
- worker `finally` always releases or terminally marks the operation;
- persisted records use atomic writes and reject invalid schema/content;
- restart reconciliation covers terminal, missing-process, matching-process,
  and PID-reuse/identity-mismatch cases;
- workflow stops after a failed phase;
- workflow executes selected phases in canonical order;
- `skip_ssh` is included only when explicitly requested and supported;
- Call Home precondition mismatch refuses to start;
- dry run neither spawns a worker nor claims the slot.

### Integration tests

- start a test command that emits output, pauses longer than 30 seconds, then
  exits successfully; verify polling sees completion;
- close the initiating HTTP connection immediately after acceptance and verify
  the job completes;
- disconnect and reconnect an SSE observer without affecting the job;
- restart the MCP server during a backend job and verify observation resumes;
- simulate backend restart with a stale running record and verify safe
  reconciliation;
- run install/deploy workflow fixtures with pre/main/post success and failure
  combinations;
- ensure the web and MCP clients receive the same operation snapshot;
- verify busy responses include the active operation ID, source, and step.

Avoid using real Storage Scale installation in automated tests. Add a controlled
test command/runner injection so lifecycle behavior can be tested with local
short-lived subprocesses.

### Manual cluster acceptance

Before release, verify on a non-production cluster:

1. dry-run previews for install and deploy workflows;
2. install precheck/main/postcheck with and without explicit `skip_ssh`;
3. deploy precheck/main/postcheck with and without explicit `skip_ssh`;
4. an MCP restart and SSH-tunnel interruption during a long phase;
5. a browser refresh during a long phase;
6. cancellation during a safe test phase;
7. backend restart reconciliation;
8. Call Home remains at the required state throughout;
9. no duplicate toolkit command starts after timeout, refresh, or retry.

## Implementation sequence and completion criteria

### Phase A: operation engine

- Introduce `OperationManager` and immutable snapshots.
- Add process-group ownership, bounded logs, persistence, and reconciliation.
- Add JSON start/status/line/cancel endpoints.
- Complete lifecycle unit and integration tests.

Complete when a client can disconnect immediately after starting a quiet
long-running test job and later observe its correct terminal state.

### Phase B: phase and workflow migration

- Route install/deploy/upgrade phases through the operation engine.
- Add workflow validation and serial step execution.
- Add Call Home precondition checks and explicit `skip_ssh` recording.
- Add resume lineage.

Complete when every selected phase is represented in one durable workflow record
and failure prevents later phases from starting.

### Phase C: clients

- Change MCP real mutations to job-start requests; remove background drains.
- Add operation-specific status and cancellation tools.
- Change the web UI to detached observation and reconnection.
- Update user documentation and examples.

Complete when neither client needs to hold the starting HTTP request open.

### Phase D: remaining mutations and cleanup

- Migrate all remaining mutating endpoints.
- Remove request-owned real subprocess execution.
- Keep or version compatibility aliases as documented.
- Run the complete automated and manual acceptance suites.

Complete when every real mutation is backend-owned and an observer disconnect
cannot stop, stall, or orphan it.

## Operational handling of the currently stalled install

Do not automatically kill, clear, or replace the currently reported operation.
Before testing the new implementation, an operator must:

1. inspect the toolkit processes and installation log;
2. decide whether to let them finish or terminate them explicitly;
3. verify package/install state on every node;
4. reconcile the backend operation slot;
5. run the appropriate precheck before any retry.

This is deliberately outside automated migration because the install may have
already made partial changes to cluster nodes.
