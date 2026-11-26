"""
/api/stream/phase's `skip_ssh` param: `--skip ssh` is on unless a caller
turns it off, and is never appended to phases that don't accept it.
"""
import pytest


@pytest.fixture(autouse=True)
def _fake_toolkit_exists(monkeypatch, ss):
    monkeypatch.setattr(ss, "_sudo_isfile", lambda path: True)


def _preview(ss, phase, **extra):
    resp = ss.app.test_client().get(
        "/api/stream/phase",
        headers={"X-Scale-Token": ss._AUTH_TOKEN},
        query_string={"toolkit": "/tmp/spectrumscale", "phase": phase, "dry_run": "true", **extra},
    )
    return resp.get_data(as_text=True)


@pytest.mark.parametrize("phase", ["precheck-install", "install", "postcheck-deploy",
                                   "upgrade-precheck", "upgrade-run", "upgrade-postcheck"])
def test_skip_ssh_is_the_default(ss, phase):
    assert "--skip ssh" in _preview(ss, phase)


def test_skip_ssh_can_be_turned_off(ss):
    body = _preview(ss, "install", skip_ssh="false")
    assert "spectrumscale install" in body
    assert "--skip ssh" not in body


@pytest.mark.parametrize("phase", ["upgrade-showversions", "enable-daemon", "nodeid-define"])
def test_default_does_not_reach_unsupported_phases(ss, phase):
    body = _preview(ss, phase)
    assert "spectrumscale" in body
    assert "--skip ssh" not in body
