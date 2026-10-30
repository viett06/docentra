import shutil
import socket
import ssl
import threading
from argparse import ArgumentTypeError
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import HTTPSHandler, ProxyHandler, build_opener

import pytest

from scripts.mobile import bootstrap_handler, lan_host, prepare


@pytest.fixture(scope="module")
def mobile_config(tmp_path_factory):
    if not shutil.which("openssl"):
        pytest.skip("OpenSSL CLI is needed for local HTTPS")
    return prepare(tmp_path_factory.mktemp("mobile"), "127.0.0.1", 8443, 8081)


@pytest.fixture
def tls_server(mobile_config):
    server = ThreadingHTTPServer(("127.0.0.1", 0), bootstrap_handler(mobile_config["public"]))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(mobile_config["cert"], mobile_config["key"])
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_https_requires_correct_ca_and_matching_address(mobile_config, tls_server):
    trusted = ssl.create_default_context(cafile=str(mobile_config["ca"]))
    with socket.create_connection(("127.0.0.1", tls_server), timeout=3) as raw:
        with trusted.wrap_socket(raw, server_hostname="127.0.0.1") as connection:
            assert ("IP Address", "127.0.0.1") in connection.getpeercert()["subjectAltName"]
    for context, hostname in [(ssl.create_default_context(), "127.0.0.1"), (trusted, "192.168.20.99")]:
        with socket.create_connection(("127.0.0.1", tls_server), timeout=3) as raw:
            with pytest.raises(ssl.SSLCertVerificationError):
                context.wrap_socket(raw, server_hostname=hostname)


def test_setup_server_shares_only_public_guide_ca_and_qr(mobile_config, tls_server):
    context = ssl.create_default_context(cafile=str(mobile_config["ca"]))
    client = build_opener(ProxyHandler({}), HTTPSHandler(context=context))
    base = f"https://127.0.0.1:{tls_server}"
    with client.open(base + "/docentra-ca.crt", timeout=3) as response:
        assert response.read() == mobile_config["ca"].read_bytes()
        assert "attachment" in response.headers["Content-Disposition"]
    with client.open(base + "/", timeout=3) as response:
        page = response.read().decode()
        assert mobile_config["app_url"].replace("&", "&amp;") in page
        assert mobile_config["fingerprint"] in page
    with client.open(base + "/connect.svg", timeout=3) as response:
        assert b"<svg" in response.read()
    for path in ["/private/ca.key", "/server.key", "/../private/ca.key", "/%2e%2e/private/ca.key", "/api/v1/employees"]:
        with pytest.raises(HTTPError) as denied:
            client.open(base + path, timeout=3)
        assert denied.value.code == 404


def test_wifi_address_change_preserves_installed_ca(tmp_path):
    original = prepare(tmp_path, "192.168.1.10", 8443, 8081)
    certificate = original["ca"].read_bytes()
    updated = prepare(tmp_path, "192.168.1.11", 8443, 8081)
    assert updated["ca"].read_bytes() == certificate
    assert updated["fingerprint"] == original["fingerprint"]
    assert updated["key"].stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "private/ca.key").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("address", ["8.8.8.8", "0.0.0.0", "example.com", "192.168.1.1;ls"])
def test_mobile_launcher_rejects_public_or_non_ip_addresses(address):
    with pytest.raises(ArgumentTypeError):
        lan_host(address)
