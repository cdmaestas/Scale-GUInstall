"""
stream_node_identity()'s `days` cert-validity field used to silently
fall back to a default on invalid input instead of reporting it, unlike
every other field the same route validates. Confirms it's now an
explicit, reported error like its siblings.
"""


def _post(ss, body):
    client = ss.app.test_client()
    return client.post("/api/stream/node-identity", json=body,
                        headers={"X-Scale-Token": ss._AUTH_TOKEN})


def test_invalid_days_reported_as_error(ss):
    resp = _post(ss, {"cluster_name": "mycluster", "nodes": ["node1"], "days": "not-a-number"})
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Invalid days" in body
    assert "not-a-number" in body


def test_missing_days_defaults_without_error(ss):
    # Absence is fine (falls back to the documented default of 10000) —
    # only a present-but-unparseable value should be reported. Paired
    # with an unrelated invalid field (org_name) so the route still
    # stops at validation instead of going on to real mkdir/openssl
    # subprocess calls.
    resp = _post(ss, {"cluster_name": "mycluster", "nodes": ["node1"], "org_name": "bad org!"})
    body = resp.get_data(as_text=True)
    assert "Invalid org name" in body
    assert "Invalid days" not in body
