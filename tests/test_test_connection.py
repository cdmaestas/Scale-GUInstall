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
