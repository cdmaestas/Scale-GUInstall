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
