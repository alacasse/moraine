import json
import threading
import time

import anyio

import pytest
from starlette.testclient import TestClient

from moraine_email.mcp_server import MAX_BODY, create_app

TOKEN = "test-agent-secret-" + "x" * 40
HEADERS = {"Authorization": "Bearer " + TOKEN, "Accept": "application/json, text/event-stream"}


class RecordingBroker:
    def __init__(self):
        self.calls = []
        self.lock = threading.RLock()

    def list_context(self, agent, grant_id):
        self.calls.append((agent, grant_id))
        return {"resources": [{"resource_ref": "m1"}]}

    def propose_reply(self, agent, body):
        self.calls.append((agent, body))
        return {"request_id": "proposed", "state": "pending"}

    def get_request(self, agent, request_id):
        raise RuntimeError("DO-NOT-LEAK-this-internal-value")


@pytest.fixture
def client():
    broker = RecordingBroker()
    with TestClient(create_app(broker, token=TOKEN), base_url="http://127.0.0.1:8765") as client:
        client.broker = broker
        yield client


def rpc(client, method, params=None):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        payload["params"] = params
    return client.post("/mcp", headers=HEADERS, json=payload)


def test_real_sdk_initialize_discovery_and_dispatch(client):
    response = rpc(client, "initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                                          "clientInfo": {"name": "test", "version": "1"}})
    assert response.status_code == 200
    assert "protocolVersion" in response.json()["result"]
    tools = rpc(client, "tools/list").json()["result"]["tools"]
    assert {tool["name"] for tool in tools} == {"list_context", "read_context", "propose_reply", "get_request"}
    assert all(tool["inputSchema"]["additionalProperties"] is False for tool in tools)
    response = rpc(client, "tools/call", {"name": "list_context", "arguments": {"grant_id": "g1"}})
    assert response.json()["result"]["structuredContent"] == {"resources": [{"resource_ref": "m1"}]}
    assert client.broker.calls == [("agent:pilot", "g1")]


@pytest.mark.parametrize("arguments", [{"grant_id": "g1", "agent": "human:owner"},
                                       {"grant_id": "g1", "approved": True},
                                       {"grant_id": 1}, {}])
def test_authority_fields_and_invalid_arguments_rejected(client, arguments):
    response = rpc(client, "tools/call", {"name": "list_context", "arguments": arguments})
    assert response.json()["result"]["isError"] is True
    assert client.broker.calls == []


def test_safe_error_and_no_human_tools_or_routes(client):
    response = rpc(client, "tools/call", {"name": "get_request", "arguments": {"request_id": "q1"}})
    assert "DO-NOT-LEAK" not in response.text
    assert response.json()["result"]["isError"] is True
    response = rpc(client, "tools/call", {"name": "approve", "arguments": {}})
    assert response.json()["result"]["isError"] is True
    assert client.post("/human/review", headers=HEADERS, json={}).status_code == 404


def test_auth_origin_host_and_bounds(client):
    assert client.post("/mcp", json={}).status_code == 401
    assert client.post("/mcp", headers={**HEADERS, "Origin": "https://evil.test"}, json={}).status_code == 403
    assert client.post("/mcp", headers={**HEADERS, "Host": "evil.test"}, json={}).status_code == 403
    assert client.post("/mcp", headers=HEADERS, content=b"x" * (MAX_BODY + 1)).status_code == 413
    assert client.post("/mcp", headers=HEADERS, content=b'{"method":"a","method":"b"}').status_code == 400
    assert client.post("/mcp", headers=HEADERS, content=b"[{}]").status_code == 400


def test_end_to_end_real_broker_opa_provider_and_human_socket(broker, grant_body, oracle, tmp_path):
    import os
    import threading
    from moraine_email.human_cli import call
    from moraine_email.human_server import HumanServer

    path = tmp_path / "integration.sock"
    human = HumanServer(path, broker, allowed_uid=os.getuid())
    worker = threading.Thread(target=human.serve_forever)
    worker.start()
    try:
        grant = call(path, {"operation": "create_grant", "body": grant_body})
        with TestClient(create_app(broker, token=TOKEN), base_url="http://127.0.0.1:8765") as client:
            result = rpc(client, "tools/call", {"name": "list_context", "arguments": {"grant_id": grant["grant_id"]}})
            assert result.json()["result"]["isError"] is False
            proposal = {"grant_id": grant["grant_id"], "idempotency_key": "transport-e2e",
                        "reply_to_ref": "message-1", "body_text": "Oui, mardi convient."}
            request = rpc(client, "tools/call", {"name": "propose_reply", "arguments": proposal}).json()["result"]["structuredContent"]
            assert request["state"] == "pending"
            view = call(path, {"operation": "review", "request_id": request["request_id"]})
            result = call(path, {"operation": "decide_review", "request_id": request["request_id"],
                                 "action_digest": view["action_digest"], "nonce": view["nonce"], "decision": "approve"})
            assert result["state"] == "accepted"
            receipt = rpc(client, "tools/call", {"name": "get_request", "arguments": {"request_id": request["request_id"]}})
            assert receipt.json()["result"]["structuredContent"]["state"] == "accepted"
            replay = rpc(client, "tools/call", {"name": "propose_reply", "arguments": proposal})
            assert replay.json()["result"]["structuredContent"]["request_id"] == request["request_id"]
            assert len(oracle.records("attempts")) == 1
            assert len(oracle.records("effects")) == 1
    finally:
        human.shutdown()
        worker.join()
        human.server_close()


def test_token_expiry_denies_further_calls():
    app = create_app(RecordingBroker(), token=TOKEN)
    assert not hasattr(app, "token")
    app.expires_at = 0
    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        assert rpc(client, "tools/list").status_code == 401


def test_token_expiry_while_body_arrives():
    broker = RecordingBroker()
    app = create_app(broker, token=TOKEN, auth_lifetime_seconds=0.01)
    sent = []
    received = []
    scope = {"type": "http", "path": "/mcp", "headers": [
        (b"authorization", ("Bearer " + TOKEN).encode()), (b"host", b"127.0.0.1:8765")]}

    async def receive():
        received.append(True)
        await anyio.sleep(0.03)
        return {"type": "http.request", "body": b'{"jsonrpc":"2.0","method":"tools/list","id":1}'}

    async def send(event):
        sent.append(event)

    async def run():
        app.expires_at = time.monotonic() + 0.01
        await app(scope, receive, send)

    anyio.run(run)
    assert received == [True]  # Authentication passed before the delayed read.
    assert sent[0]["status"] == 401
    assert broker.calls == []


def test_token_expiry_while_waiting_for_worker(client, monkeypatch):
    original = anyio.to_thread.run_sync
    # Expiry happens at the real asynchronous handoff, before the queued worker
    # is allowed to execute. MCP parsing and the HTTP ingress still run normally.
    async def after_queue(function, *args, **kwargs):
        client.app.expires_at = 0
        return await original(function, *args, **kwargs)

    monkeypatch.setattr(anyio.to_thread, "run_sync", after_queue)
    result = rpc(client, "tools/call", {"name": "list_context", "arguments": {"grant_id": "g1"}})
    assert result.json()["result"]["isError"] is True
    assert result.json()["result"]["content"][0]["text"] == "unauthorized"
    assert client.broker.calls == []


def test_token_expiry_while_waiting_for_broker_lock(client):
    started = threading.Event()
    real_lock = threading.RLock()

    class ObservedLock:
        def __enter__(self):
            started.set()
            real_lock.acquire()

        def __exit__(self, *_):
            real_lock.release()

    client.broker.lock = ObservedLock()
    responses = []
    with real_lock:
        request = threading.Thread(target=lambda: responses.append(rpc(
            client, "tools/call", {"name": "list_context", "arguments": {"grant_id": "g1"}})))
        request.start()
        assert started.wait(3)
        client.app.expires_at = 0
    request.join(5)
    assert not request.is_alive()
    assert responses[0].json()["result"]["content"][0]["text"] == "unauthorized"
    assert client.broker.calls == []


@pytest.mark.parametrize("body", ["\x00" * 16384, "é" * 8192], ids=["controls", "unicode"])
def test_valid_reply_at_utf8_limit_with_json_escaping(client, body):
    proposal = {"grant_id": "g1", "idempotency_key": "expanded-json", "reply_to_ref": "m1", "body_text": body}
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "propose_reply", "arguments": proposal}}
    wire = json.dumps(payload, ensure_ascii=True).encode()
    result = client.post("/mcp", headers={**HEADERS, "Content-Type": "application/json"}, content=wire)
    assert result.status_code == 200
    assert result.json()["result"]["isError"] is False
    assert client.broker.calls == [("agent:pilot", proposal)]
    payload["params"]["arguments"]["body_text"] += "x"
    result = client.post("/mcp", headers=HEADERS, json=payload)
    assert result.json()["result"]["isError"] is True
    assert len(client.broker.calls) == 1
