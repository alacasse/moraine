from __future__ import annotations

import threading

import httpx
import pytest

from server import Server


@pytest.fixture
def server(executor):
    server = Server(0, executor, {"agent:alice": "alice-token", "agent:bob": "bob-token", "human:alice": "human-token"})
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


@pytest.mark.parametrize("body", ["[]", "null", '{"a": 1, "a": 2}', '{"a": NaN}', "{broken"])
def test_malformed_protocol_json_returns_400(server, body):
    response = httpx.post(server + "/requests", content=body,
                          headers={"Authorization": "Bearer alice-token"}, trust_env=False)
    assert response.status_code == 400 and response.json()["error"] == "invalid_json"


def test_missing_capability_and_unknown_authority_fields_refused(server, executor, grant_data, order):
    grant = executor.create_grant("human:alice", grant_data)
    base = {"grant_id": grant["grant_id"], "idempotency_key": "key", "action": order}
    for body in (base, {**base, "capability": grant["capability"], "approved": True},
                 {**base, "capability": grant["capability"], "action": {**order, "owner": "alice"}}):
        response = httpx.post(server + "/requests", json=body,
                              headers={"Authorization": "Bearer alice-token"}, trust_env=False)
        assert response.status_code == 400


def test_malformed_token_http_fails_closed(server, executor, grant_data, order):
    grant = executor.create_grant("human:alice", grant_data)
    body = {**grant, "capability": "forged", "idempotency_key": "bad-token", "action": order}
    response = httpx.post(server + "/requests", json=body,
                          headers={"Authorization": "Bearer alice-token"}, trust_env=False)
    assert response.json()["state"] == "denied"
    assert response.json()["reason"] == "invalid_capability"
