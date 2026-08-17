"""
_config_read_locked() must tell "no config saved yet" (normal — the file
doesn't exist) apart from "a config file exists but couldn't be read"
(corruption) rather than treating both as an empty config with no trace
of what happened. Redirects _CONFIG_PATH to a scratch file per test
rather than touching /var/lib/scale-guinstall.
"""
def test_config_read_missing_file_is_not_corrupted(ss, tmp_path):
    ss._CONFIG_PATH = str(tmp_path / "does-not-exist.json")
    with ss._config_lock:
        revision, data, corrupted = ss._config_read_locked()
    assert (revision, data, corrupted) == (0, None, False)


def test_config_read_valid_file(ss, tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"revision": 3, "data": {"clusterName": "test"}}')
    ss._CONFIG_PATH = str(path)
    with ss._config_lock:
        revision, data, corrupted = ss._config_read_locked()
    assert (revision, data, corrupted) == (3, {"clusterName": "test"}, False)


def test_config_read_corrupt_json_is_flagged(ss, tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{not valid json')
    ss._CONFIG_PATH = str(path)
    with ss._config_lock:
        revision, data, corrupted = ss._config_read_locked()
    assert revision == 0
    assert data is None
    assert corrupted is True


def test_config_endpoint_get_surfaces_corruption_warning(ss, tmp_path):
    path = tmp_path / "config.json"
    path.write_text("not json at all")
    ss._CONFIG_PATH = str(path)
    client = ss.app.test_client()
    resp = client.get("/api/config", headers={"X-Scale-Token": ss._AUTH_TOKEN})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["revision"] == 0
    assert body["data"] is None
    assert "warning" in body


def test_config_endpoint_get_no_warning_when_missing(ss, tmp_path):
    ss._CONFIG_PATH = str(tmp_path / "does-not-exist.json")
    client = ss.app.test_client()
    resp = client.get("/api/config", headers={"X-Scale-Token": ss._AUTH_TOKEN})
    assert resp.status_code == 200
    assert "warning" not in resp.get_json()
