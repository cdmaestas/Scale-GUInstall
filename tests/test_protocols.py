"""
/api/stream/protocols/config (`spectrumscale config protocols -f <fs> -m
<mountpoint> [-i <interface>] [-e <export_ip_pool>]`) and
/api/stream/protocols/enable (`spectrumscale enable <protocol> ...`) — found
as a genuine gap live: a successful `spectrumscale deploy` only installs and
activates CES infrastructure (packages, CES daemon, GUI, perfmon) — it never
runs `config protocols` or `enable <protocol>` itself, so NFS/SMB/S3 stay
"Disabled" in `node list` even after a clean install+deploy. Checked the web
UI's "Protocols" page first (NFS/SMB/Object toggles, CES IP fields) and
confirmed it's pure mockup with no backend wiring at all — these endpoints
are genuinely new, not a duplicate of existing functionality. Flags
confirmed against this toolkit version's own `-h` output, not guessed.
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


# ---- config protocols ---------------------------------------------------

def test_config_builds_minimal_command(ss, monkeypatch, _fake_toolkit_exists):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "configuring")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/protocols/config",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "toolkit": "/tmp/spectrumscale", "filesystem": "cesSharedRoot",
            "mountpoint": "/ibm/cesSharedRoot", "dry_run": False,
        },
    )
    resp.get_data()
    assert captured["cmd"] == [
        "sudo", "-n", "/tmp/spectrumscale", "config", "protocols",
        "-f", "cesSharedRoot", "-m", "/ibm/cesSharedRoot",
    ]


def test_config_builds_full_command_with_interface_and_export_ips(ss, monkeypatch, _fake_toolkit_exists):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "configuring")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/protocols/config",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "toolkit": "/tmp/spectrumscale", "filesystem": "cesSharedRoot",
            "mountpoint": "/ibm/cesSharedRoot", "interface": "eth1",
            "export_ip_pool": "10.249.128.45,10.249.128.43", "dry_run": False,
        },
    )
    resp.get_data()
    assert captured["cmd"] == [
        "sudo", "-n", "/tmp/spectrumscale", "config", "protocols",
        "-f", "cesSharedRoot", "-m", "/ibm/cesSharedRoot",
        "-i", "eth1", "-e", "10.249.128.45,10.249.128.43",
    ]


def test_config_rejects_invalid_filesystem(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/protocols/config",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "toolkit": "/tmp/spectrumscale", "filesystem": "ces;rm -rf /",
            "mountpoint": "/ibm/cesSharedRoot", "dry_run": True,
        },
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "Invalid filesystem name" in body


def test_config_rejects_invalid_mountpoint(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/protocols/config",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "toolkit": "/tmp/spectrumscale", "filesystem": "cesSharedRoot",
            "mountpoint": "not-absolute", "dry_run": True,
        },
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "Invalid mountpoint" in body


def test_config_rejects_invalid_export_ip(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/protocols/config",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "toolkit": "/tmp/spectrumscale", "filesystem": "cesSharedRoot",
            "mountpoint": "/ibm/cesSharedRoot", "export_ip_pool": "999.999.999.999",
            "dry_run": True,
        },
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "Invalid export IP" in body


def test_config_dry_run_true_does_not_claim_operation(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/protocols/config",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "toolkit": "/tmp/spectrumscale", "filesystem": "cesSharedRoot",
            "mountpoint": "/ibm/cesSharedRoot", "dry_run": True,
        },
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


def test_config_returns_busy_when_operation_already_running(ss, _fake_toolkit_exists):
    ss._claim_operation("some-other-op", "web")
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/protocols/config",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={
            "toolkit": "/tmp/spectrumscale", "filesystem": "cesSharedRoot",
            "mountpoint": "/ibm/cesSharedRoot", "dry_run": False,
        },
    )
    body = resp.get_data(as_text=True)
    assert '"type": "busy"' in body
    assert "some-other-op" in body


# ---- enable ---------------------------------------------------------------

def test_enable_builds_command_for_multiple_protocols(ss, monkeypatch, _fake_toolkit_exists):
    captured = {}

    def fake_stream_process(cmd, **kwargs):
        captured["cmd"] = cmd
        yield ss.sse("normal", "enabling")
        return 0

    monkeypatch.setattr(ss, "stream_process", fake_stream_process)
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/protocols/enable",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "protocols": ["nfs", "smb"], "dry_run": False},
    )
    resp.get_data()
    assert captured["cmd"] == ["sudo", "-n", "/tmp/spectrumscale", "enable", "nfs", "smb"]


def test_enable_rejects_invalid_protocol(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/protocols/enable",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "protocols": ["ftp"], "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "Invalid protocol" in body


def test_enable_rejects_empty_protocol_list(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/protocols/enable",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "protocols": [], "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "error"' in body
    assert "At least one protocol is required" in body


def test_enable_dry_run_true_does_not_claim_operation(ss, _fake_toolkit_exists):
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/protocols/enable",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "protocols": ["nfs"], "dry_run": True},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "dryrun"' in body
    assert ss._current_operation is None


def test_enable_returns_busy_when_operation_already_running(ss, _fake_toolkit_exists):
    ss._claim_operation("some-other-op", "web")
    client = ss.app.test_client()
    resp = client.post(
        "/api/stream/protocols/enable",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        json={"toolkit": "/tmp/spectrumscale", "protocols": ["nfs"], "dry_run": False},
    )
    body = resp.get_data(as_text=True)
    assert '"type": "busy"' in body
    assert "some-other-op" in body
