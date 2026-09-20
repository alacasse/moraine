import http.client
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import httpx
import pytest

HERE = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def command(folder, state, port, provider):
    return [sys.executable, str(folder / "host.py"), "--port", str(port), "--state-dir", str(state),
            "--provider-url", provider[0], "--provider-token", provider[1],
            "--agent-token", "-agent-fixture", "--other-agent-token", "other-fixture",
            "--human-token", "human-fixture"]


@pytest.fixture
def host_service(tmp_path, provider_service):
    port = free_port()
    logfile = (tmp_path / "host.log").open("w")
    process = subprocess.Popen(command(HERE, tmp_path / "host-state", port, provider_service), stdout=logfile, stderr=logfile)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise AssertionError((tmp_path / "host.log").read_text())
            try:
                if httpx.get(base + "/health", trust_env=False).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.03)
        else:
            raise AssertionError("host did not start")
        yield base, port
    finally:
        process.terminate()
        process.wait(timeout=3)
        logfile.close()


@pytest.mark.parametrize("body", [b'[]', b'{"agent":"agent:alice","agent":"human:alice"}', b'{"amount":NaN}', b'{broken', b'null'])
def test_malformed_json_is_rejected_without_crashing(host_service, body):
    response = httpx.post(host_service[0] + "/grants", content=body,
                          headers={"Authorization": "Bearer human-fixture"}, trust_env=False)
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_body"}


def test_duplicate_authorization_headers_are_refused(host_service):
    connection = http.client.HTTPConnection("127.0.0.1", host_service[1], timeout=2)
    try:
        connection.putrequest("GET", "/requests/fabricated")
        connection.putheader("Authorization", "Bearer -agent-fixture")
        connection.putheader("Authorization", "Bearer human-fixture")
        connection.endheaders()
        assert connection.getresponse().status == 401
    finally:
        connection.close()


def test_body_identity_and_policy_claims_are_rejected(host_service):
    body = {"grant_id": "fabricated", "idempotency_key": "one", "principal": "human:alice",
            "action": {"type": "document.read", "account": "alice", "document_id": "public-note"}}
    response = httpx.post(host_service[0] + "/requests", json=body,
                          headers={"Authorization": "Bearer -agent-fixture"}, trust_env=False)
    assert response.status_code == 400


def test_malformed_policy_fails_before_health_is_available(tmp_path, provider_service):
    folder = tmp_path / "broken-host"
    folder.mkdir()
    for name in ("host.py", "models.py", "policy.py", "gate.py", "provider.py", "schema.json"):
        shutil.copy2(HERE / name, folder / name)
    (folder / "policy.cedar").write_text("invalid Cedar syntax")
    port = free_port()
    result = subprocess.run(command(folder, tmp_path / "state", port, provider_service),
                            capture_output=True, text=True, timeout=5)
    assert result.returncode != 0
    assert "invalid embedded Cedar policy" in result.stderr
    with pytest.raises(httpx.ConnectError):
        httpx.get(f"http://127.0.0.1:{port}/health", trust_env=False)
