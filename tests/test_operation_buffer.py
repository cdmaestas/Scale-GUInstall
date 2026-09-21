"""
_current_operation is a single module-level slot shared by every request
(and, since the `ss` fixture is session-scoped, every test in this
session) — reset it before each test so one test's leftover state can't
make another test's claim/busy assertion order-dependent.
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_operation_state(ss):
    ss._current_operation = None
    yield
    ss._current_operation = None


def test_claim_when_idle_succeeds(ss):
    op, busy = ss._claim_operation("test-op", "mcp")
    assert busy is None
    assert op["name"] == "test-op"
    assert op["source"] == "mcp"
    assert op["status"] == "running"
    assert op["lines"] == []


def test_claim_while_running_returns_busy_and_does_not_replace_it(ss):
    op1, _ = ss._claim_operation("first", "web")
    op2, busy = ss._claim_operation("second", "mcp")
    assert op2 is None
    assert busy["name"] == "first"
    assert busy["source"] == "web"
    # the busy dict is a copy — mutating op1 further must not affect it
    assert busy is not op1


def test_release_then_claim_again_succeeds(ss):
    op1, _ = ss._claim_operation("first", "web")
    ss._release_operation(op1, "success")
    assert op1["status"] == "success"
    assert op1["finished_at"] is not None

    op2, busy = ss._claim_operation("second", "mcp")
    assert busy is None
    assert op2["name"] == "second"


def test_release_with_rc_records_it(ss):
    op, _ = ss._claim_operation("job", "web")
    ss._release_operation(op, "error", rc=1)
    assert op["status"] == "error"
    assert op["rc"] == 1


def test_append_operation_line_appends_in_order(ss):
    op, _ = ss._claim_operation("job", "mcp")
    ss._append_operation_line(op, "first line")
    ss._append_operation_line(op, "second line")
    assert op["lines"] == ["first line", "second line"]


def test_append_operation_line_is_a_noop_for_none(ss):
    ss._append_operation_line(None, "should not raise")  # op=None is the default for read-only/dry-run calls


def test_operation_current_endpoint_idle(ss):
    client = ss.app.test_client()
    resp = client.get("/api/operation/current", headers={"X-Scale-Token": ss._AUTH_TOKEN})
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "idle"}


def test_operation_current_endpoint_running(ss):
    op, _ = ss._claim_operation("nsd-add", "mcp")
    ss._append_operation_line(op, "$ sudo -n /path/spectrumscale nsd add ...")
    client = ss.app.test_client()
    resp = client.get("/api/operation/current", headers={"X-Scale-Token": ss._AUTH_TOKEN})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "running"
    assert body["name"] == "nsd-add"
    assert body["source"] == "mcp"
    assert body["lines"] == ["$ sudo -n /path/spectrumscale nsd add ..."]
    assert body["started_at"] is not None
    assert body["finished_at"] is None


def test_operation_current_endpoint_requires_token(ss):
    client = ss.app.test_client()
    resp = client.get("/api/operation/current")
    assert resp.status_code == 401
