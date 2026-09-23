"""
/api/stream/phase's `confirm` param — discovered as a real bug live: `upgrade
run` prompts "Do you want to continue the parallel offline upgrade process?
[y/N]" when every node is designated offline (via nsd `upgrade config
offline`), and stream_process's default /dev/null stdin means that prompt
hits EOF and the toolkit fails with "An unexpected error occurred" instead
of running. confirm=true answers "y" to that prompt.
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


def test_confirm_true_sends_y_as_stdin(ss, _fake_toolkit_exists, monkeypatch):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["stdin_text"] = kwargs.get("stdin_text")
        yield ss.sse("normal", "upgrading")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.get(
        "/api/stream/phase",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={
            "toolkit": "/tmp/spectrumscale", "phase": "upgrade-run",
            "confirm": "true", "dry_run": "false",
        },
    )
    resp.get_data()
    assert captured["stdin_text"] == "y\n"


def test_confirm_absent_sends_no_stdin(ss, _fake_toolkit_exists, monkeypatch):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["stdin_text"] = kwargs.get("stdin_text")
        yield ss.sse("normal", "installing")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.get(
        "/api/stream/phase",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"toolkit": "/tmp/spectrumscale", "phase": "install", "dry_run": "false"},
    )
    resp.get_data()
    assert captured["stdin_text"] is None
