"""
/api/stream/test-connection's `mmgetstate -a` call — discovered as a real
bug live: a bare "mmgetstate" over non-interactive ssh fails with "command
not found" because that session never sources the profile that puts
MMFS_BIN on PATH. Confirmed against the real cluster (mmgetstate works fine
when run directly on the node, but not through this endpoint's ssh call).
Fixed by using the full MMFS_BIN path, same as every other mm* invocation
in this file.
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_operation_state(ss):
    ss._current_operation = None
    yield
    ss._current_operation = None


def test_uses_full_path_to_mmgetstate(ss, monkeypatch):
    captured = {}

    def fake_run_cmd(cmd, **kwargs):
        captured["cmd"] = cmd
        return "", 0

    monkeypatch.setattr(ss, "_run_cmd", fake_run_cmd)
    client = ss.app.test_client()
    resp = client.get(
        "/api/stream/test-connection",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"node": "zima1"},
    )
    resp.get_data()
    assert captured["cmd"][-2:] == [f"{ss.MMFS_BIN}/mmgetstate", "-a"]


def _run_endpoint(ss, monkeypatch, responses):
    """responses: list of (stdout, rc), consumed in order by successive _run_cmd calls."""
    commands = []
    queue = list(responses)

    def fake_run_cmd(cmd, **kwargs):
        commands.append(cmd)
        return queue.pop(0)

    monkeypatch.setattr(ss, "_run_cmd", fake_run_cmd)
    client = ss.app.test_client()
    resp = client.get(
        "/api/stream/test-connection",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"node": "scale-server1"},
    )
    return resp.get_data(as_text=True), commands


def test_ssh_failure_is_reported_and_mmgetstate_is_not_run(ss, monkeypatch):
    body, commands = _run_endpoint(ss, monkeypatch, [("ssh: connect to host x port 22: Refused", 255)])
    assert "SSH connection to scale-server1 failed (exit 255)" in body
    assert "Refused" in body
    assert len(commands) == 1 and commands[0][-1] == "true"


def test_mmgetstate_failure_is_not_reported_as_an_ssh_failure(ss, monkeypatch):
    """The regression: ssh passes the remote command's exit status through, so a
    non-zero mmgetstate (GPFS absent/down on the node) used to be reported as
    "SSH connection failed" even though SSH worked."""
    body, commands = _run_endpoint(
        ss, monkeypatch, [("", 0), ("mmgetstate: Command failed.", 255)]
    )
    assert "SSH connection to scale-server1 successful" in body
    assert "SSH connection to scale-server1 failed" not in body
    assert "mmgetstate -a` on scale-server1 exited 255" in body
    assert "mmgetstate: Command failed." in body
    assert commands[1][-2:] == [f"{ss.MMFS_BIN}/mmgetstate", "-a"]


def test_active_gpfs_reports_both_ok(ss, monkeypatch):
    table = " Node number  Node name  GPFS state\n 1  scale-server1  active"
    body, _ = _run_endpoint(ss, monkeypatch, [("", 0), (table, 0)])
    assert "SSH connection to scale-server1 successful" in body
    assert "GPFS is running on target node" in body


def _ssh_target_args(cmd):
    """Everything from the 'ssh' token up to (not including) the remote command."""
    return cmd[cmd.index("ssh") + 1:]


def test_no_user_or_port_means_ssh_config_decides(ss, monkeypatch):
    """Forcing -p 22 / root@ overrode the ssh config that list_devices relies on
    and failed outright where the nodes' sshd is on another port (TechZone: 2223),
    surfacing as exit 255 with no output."""
    _, commands = _run_endpoint(ss, monkeypatch, [("", 0), ("x active", 0)])
    for cmd in commands:
        assert "-p" not in cmd
        assert not any(a.startswith("root@") for a in cmd)
        assert "scale-server1" in cmd


def _run_endpoint_with(ss, monkeypatch, **query):
    commands = []

    def fake_run_cmd(cmd, **kwargs):
        commands.append(cmd)
        return "", 0

    monkeypatch.setattr(ss, "_run_cmd", fake_run_cmd)
    client = ss.app.test_client()
    resp = client.get(
        "/api/stream/test-connection",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"node": "scale-server1", **query},
    )
    return resp.get_data(as_text=True), commands


def test_explicit_port_and_user_are_passed_through(ss, monkeypatch):
    _, commands = _run_endpoint_with(ss, monkeypatch, port="2223", user="itzuser")
    args = _ssh_target_args(commands[0])
    assert args[args.index("-p") + 1] == "2223"
    assert "itzuser@scale-server1" in args


def test_invalid_port_and_user_are_still_rejected(ss, monkeypatch):
    body, commands = _run_endpoint_with(ss, monkeypatch, port="70000")
    assert "Invalid port" in body and commands == []
    body, commands = _run_endpoint_with(ss, monkeypatch, user="bad user;rm")
    assert "Invalid SSH user" in body and commands == []
