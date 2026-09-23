"""
`--ephemeral_port_range` was missing from `_ALLOWED_GPFS_FLAGS` — found live
while running `install --precheck` against a real cluster: the toolkit's own
WARN recommended `./spectrumscale config gpfs --ephemeral_port_range
60000-61000`, but this backend rejected that flag as "Unrecognised flag"
before the fix. `_ALLOWED_GPFS_FLAGS` is shared by both the single-flag
`config gpfs` endpoint and `apply-cluster-config`'s gpfs_flags loop.
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


def test_ephemeral_port_range_is_an_allowed_flag(ss):
    assert "--ephemeral_port_range" in ss._ALLOWED_GPFS_FLAGS


def test_apply_cluster_config_accepts_ephemeral_port_range(ss, monkeypatch, _fake_toolkit_exists):
    # apply-cluster-config always also runs callhome/perfmon/fileaudit
    # disable commands after the gpfs_flags loop, so collect every command
    # issued rather than asserting on a single captured value.
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
        json={
            "toolkit": "/tmp/spectrumscale",
            "gpfs_flags": [{"flag": "--ephemeral_port_range", "value": "60000-61000"}],
            "dry_run": False,
        },
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' not in body
    assert [
        "sudo", "-n", "/tmp/spectrumscale", "config", "gpfs",
        "--ephemeral_port_range", "60000-61000",
    ] in commands
