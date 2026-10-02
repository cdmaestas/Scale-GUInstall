"""
`/api/stream/apply-cluster-config`'s `perfmon` param now defaults to True
(performance monitoring on) instead of False — the user's explicit
preference, requested live: every gpfs_flags/callhome/perfmon/fileaudit
value this endpoint touches is always applied explicitly on the given call
(not left unchanged), so a call made only to set a gpfs flag was silently
also turning performance monitoring off. callhome and fileaudit still
default to False (off) — only perfmon's default changed.
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_operation_state(ss):
    ss._current_operation = None
    yield
    ss._current_operation = None


@pytest.fixture
def _fake_toolkit_exists(monkeypatch, ss):
    monkeypatch.setattr(ss, "_sudo_isfile", lambda path: True)


def test_perfmon_defaults_to_on_when_omitted(ss, monkeypatch, _fake_toolkit_exists):
    commands = []

    def fake_stream_process(cmd, **kwargs):
        commands.append(cmd)
        yield ss.sse("normal", "applying")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/apply-cluster-config",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "dry_run": False},
    )
    resp.get_data()
    assert ["sudo", "-n", "/tmp/spectrumscale", "config", "perfmon", "-r", "on"] in commands


def test_perfmon_false_still_turns_it_off_explicitly(ss, monkeypatch, _fake_toolkit_exists):
    commands = []

    def fake_stream_process(cmd, **kwargs):
        commands.append(cmd)
        yield ss.sse("normal", "applying")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/apply-cluster-config",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "perfmon": False, "dry_run": False},
    )
    resp.get_data()
    assert ["sudo", "-n", "/tmp/spectrumscale", "config", "perfmon", "-r", "off"] in commands


def test_callhome_and_fileaudit_still_default_to_off(ss, monkeypatch, _fake_toolkit_exists):
    commands = []

    def fake_stream_process(cmd, **kwargs):
        commands.append(cmd)
        yield ss.sse("normal", "applying")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/apply-cluster-config",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "dry_run": False},
    )
    resp.get_data()
    assert ["sudo", "-n", "/tmp/spectrumscale", "callhome", "disable"] in commands
    assert ["sudo", "-n", "/tmp/spectrumscale", "fileauditlogging", "disable"] in commands


def test_perfmon_node_is_rejected_before_anything_runs(ss, monkeypatch, _fake_toolkit_exists):
    """`config perfmon -N <node>` is rejected by toolkit 6.0.1.1 ("Unrecognized
    arguments"), so a supplied perfmon_node must fail loudly up front — before
    claiming the operation slot or running any command — instead of being passed
    through (the old behavior) or silently dropped."""
    commands = []

    def fake_stream_process(cmd, **kwargs):
        commands.append(cmd)
        yield ss.sse("normal", "applying")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/apply-cluster-config",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "perfmon_node": "scale-gui1", "dry_run": False},
    )
    body = resp.get_data(as_text=True)
    assert "perfmon_node is not supported" in body
    assert commands == []
    assert ss._current_operation is None


def test_config_perfmon_never_gets_a_node_flag(ss, monkeypatch, _fake_toolkit_exists):
    commands = []

    def fake_stream_process(cmd, **kwargs):
        commands.append(cmd)
        yield ss.sse("normal", "applying")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    for perfmon in (True, False):
        client.post(
            "/api/stream/apply-cluster-config",
            headers={"X-Scale-Token": ss._AUTH_TOKEN},
            json={"toolkit": "/tmp/spectrumscale", "perfmon": perfmon, "dry_run": False},
        ).get_data()
    perfmon_cmds = [c for c in commands if c[3:5] == ["config", "perfmon"]]
    assert len(perfmon_cmds) == 2
    assert all("-N" not in c for c in perfmon_cmds)
