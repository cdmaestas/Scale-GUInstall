"""
The CORS origin check used to be a prefix match (startswith("http://localhost")),
so a hostile page at http://localhost.evil.com got Access-Control-Allow-Origin and
could read the public HTML — which embeds the auth token — and then call any
mutating endpoint. Nothing validated the Host header either, leaving DNS
rebinding open. Both now require an exact, parsed loopback hostname.
"""
import pytest


def _get(ss, path="/", **headers):
    return ss.app.test_client().get(path, headers=headers)


@pytest.mark.parametrize("origin", [
    "http://localhost",
    "http://localhost:5001",
    "http://127.0.0.1:5001",
    "http://[::1]:5001",
    "http://LOCALHOST:5001",
])
def test_loopback_origins_are_allowed(ss, origin):
    assert _get(ss, Origin=origin).headers.get("Access-Control-Allow-Origin") == origin


@pytest.mark.parametrize("origin", [
    "http://localhost.evil.com",
    "http://127.0.0.1.evil.com",
    "http://localhost@evil.com",
    "http://evil.com",
    "http://localhost.evil.com:5001",
    "https://localhost",
    "null",
    "",
])
def test_lookalike_and_foreign_origins_are_not_allowed(ss, origin):
    assert "Access-Control-Allow-Origin" not in _get(ss, Origin=origin).headers


@pytest.mark.parametrize("host", ["localhost:5001", "127.0.0.1:5001", "[::1]:5001", "localhost"])
def test_loopback_hosts_are_served(ss, host):
    assert _get(ss, Host=host).status_code == 200


@pytest.mark.parametrize("host", ["evil.example", "localhost.evil.com", "127.0.0.1.evil.com", "evil.com:5001"])
def test_foreign_host_headers_are_refused_even_with_a_valid_token(ss, host):
    page = _get(ss, "/", Host=host)
    assert page.status_code == 421
    api = _get(ss, "/api/ping", Host=host, **{"X-Scale-Token": ss._AUTH_TOKEN})
    assert api.status_code == 421
    assert "Unrecognized Host" in api.get_json()["error"]


def test_preflight_requests_with_a_foreign_host_are_refused(ss):
    resp = ss.app.test_client().open("/api/ping", method="OPTIONS", headers={"Host": "evil.example"})
    assert resp.status_code == 421


def test_allowed_hosts_can_be_extended_explicitly(ss, monkeypatch):
    monkeypatch.setattr(ss, "_LOCAL_HOSTNAMES", ss._LOCAL_HOSTNAMES | {"bastion.internal"})
    assert _get(ss, Host="bastion.internal:5001").status_code == 200
    assert _get(ss, Host="evil.example").status_code == 421
