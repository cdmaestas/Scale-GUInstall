"""
dry_run lets a caller (chiefly the MCP server) see what a mutating
endpoint would run without ever invoking subprocess/sudo. Two layers:

1. stream_process() itself — the shared short-circuit every v1 endpoint
   funnels through.
2. The 7 v1 endpoints (+ spectrumscale_kill's one-off, non-stream_process
   path) actually reading dry_run from the request and threading it
   through.

Endpoint-level tests monkeypatch _sudo_isfile to True (matching
test_config_persistence.py's approach of overriding module attributes
directly for a test) so they can reach the dry_run branch without a real
spectrumscale binary or passwordless sudo on the test machine — that
existence check is real validation, not something dry_run should have
to fake its way past, so the goal here is just to get past it, not to
test it.
"""
import json
import os
import time

import pytest


@pytest.fixture(autouse=True)
def _reset_operation_state(ss):
    ss._current_operation = None
    yield
    ss._current_operation = None


def _drain(gen):
    try:
        while True:
            next(gen)
    except StopIteration as e:
        return e.value


# --- stream_process() itself -------------------------------------------------

def test_stream_process_dry_run_never_spawns_a_process(ss):
    # "false" would return rc=1 if actually executed — dry_run must return 0
    # regardless, proving Popen was never called.
    gen = ss.stream_process(["false"], dry_run=True)
    events = list(gen)
    assert len(events) == 1
    assert '"type": "dryrun"' in events[0]
    assert "not executed" in events[0]


def test_stream_process_dry_run_returns_zero(ss):
    rc = _drain(ss.stream_process(["false"], dry_run=True))
    assert rc == 0


def test_stream_process_dry_run_does_not_touch_the_operation_buffer(ss):
    op, _ = ss._claim_operation("unrelated", "web")
    list(ss.stream_process(["false"], dry_run=True, op=op))
    # dry_run returns before ever reaching _append_operation_line
    assert op["lines"] == []


def test_stream_process_real_run_appends_to_op(ss):
    op, _ = ss._claim_operation("job", "mcp")
    rc = _drain(ss.stream_process(["echo", "hello"], op=op))
    assert rc == 0
    assert op["lines"] == ["hello"]


def test_stream_process_abandoned_generator_kills_the_child(ss):
    # Simulates what a fire-and-forget MCP client would do if it (or its
    # background drain task) died without properly closing the connection
    # — Python throws GeneratorExit into the generator at its suspended
    # yield with no other cleanup path. The finally: proc.kill() added
    # alongside dry_run (see stream_process's docstring) is what stands
    # between that and an orphaned child process.
    cmd = ["python3", "-c", "import os,sys,time; print(os.getpid()); sys.stdout.flush(); time.sleep(10)"]
    gen = ss.stream_process(cmd)
    first_event = next(gen)
    pid = int(json.loads(first_event.split("data: ", 1)[1])["line"])

    os.kill(pid, 0)  # no exception raised -> still alive

    gen.close()  # throws GeneratorExit at the suspended yield

    for _ in range(30):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        pytest.fail("child process was still alive 3s after the generator was abandoned")


# --- endpoint-level: dry_run reaches stream_process without real execution --

@pytest.fixture
def _fake_toolkit_exists(monkeypatch, ss):
    monkeypatch.setattr(ss, "_sudo_isfile", lambda path: True)


def test_nsd_add_dry_run_true_does_not_claim_operation(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/nsd-add",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "toolkit": "/tmp/spectrumscale",
            "nsds": [{"server": "node1", "disk": "/dev/sdb", "usage": "dataAndMetadata"}],
            "dry_run": True,
        },
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None  # never claimed — dry_run is functionally read-only


def test_nsd_add_defaults_to_dry_run_when_key_omitted(ss, _fake_toolkit_exists):
    """POST endpoints default dry_run=True per decision 6 — a caller (like a
    fresh MCP tool call) that omits the key entirely must get a preview,
    never a real execution, and must not claim the operation slot."""
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/nsd-add",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "toolkit": "/tmp/spectrumscale",
            "nsds": [{"server": "node1", "disk": "/dev/sdb", "usage": "dataAndMetadata"}],
        },
    )
    assert '"type": "dryrun"' in resp.get_data(as_text=True)
    assert ss._current_operation is None


def test_format_disk_dry_run_true(ss):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/format-disk",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"node": "node1", "device": "/dev/sdb", "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert "wipefs" in body
    assert ss._current_operation is None


def test_phase_dry_run_true_via_query_param(ss, _fake_toolkit_exists):
    """GET endpoints (phase, setup) read dry_run from the query string and
    default to real execution when absent, preserving the existing web
    UI's behavior with zero frontend changes for those two."""
    client = ss.app.test_client()
    resp = client.get(
        "/api/stream/phase",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"toolkit": "/tmp/spectrumscale", "phase": "install", "dry_run": "true"},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


def test_spectrumscale_kill_dry_run_true_does_not_send_signals(ss, monkeypatch):
    # dry_run returns before the function ever reaches its subprocess.run
    # calls (see spectrumscale_kill) — no need to mock subprocess itself,
    # matching this suite's existing convention of relying on that code
    # structure rather than mocking subprocess/ssh.
    monkeypatch.setattr(ss, "_running_spectrumscale", lambda: [(123, "spectrumscale install")])
    client = ss.app.test_client()
    resp = client.post(
        "/api/spectrumscale/kill",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"dry_run": True},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["dry_run"] is True
    assert body["would_kill"] == [{"pid": 123, "cmd": "spectrumscale install"}]
    assert ss._current_operation is None


def test_spectrumscale_kill_defaults_to_dry_run_when_key_omitted(ss, monkeypatch):
    monkeypatch.setattr(ss, "_running_spectrumscale", lambda: [(123, "spectrumscale install")])
    client = ss.app.test_client()
    resp = client.post("/api/spectrumscale/kill", headers={"X-Scale-Token": ss._AUTH_TOKEN}, json={})
    assert resp.get_json()["dry_run"] is True


# --- busy-claim path, exercised end-to-end through a real endpoint ---------

def test_nsd_add_returns_busy_when_operation_already_running(ss, _fake_toolkit_exists):
    ss._claim_operation("some-other-op", "web")
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/nsd-add",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "toolkit": "/tmp/spectrumscale",
            "nsds": [{"server": "node1", "disk": "/dev/sdb", "usage": "dataAndMetadata"}],
            "dry_run": False,
        },
    )
    body = resp.get_data(as_text=True)
    assert '"type": "busy"' in body
    assert "some-other-op" in body
