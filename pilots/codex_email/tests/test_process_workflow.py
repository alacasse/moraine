"""Real subprocesses and official MCP client: no ASGI transport substitution."""
import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from moraine_email.human_cli import call

ROOT = Path(__file__).resolve().parents[1]


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def process(command, logfile):
    with logfile.open("w") as output:
        child = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=output, start_new_session=True)
        try:
            yield child
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=3)


def ready(child, url, human_socket=None):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        assert child.poll() is None, "subprocess exited before ready"
        try:
            response = httpx.post(url, json={}, timeout=.2, trust_env=False)
            if response.status_code == 401 and (human_socket is None or human_socket.exists()):
                return
        except httpx.HTTPError:
            pass
        time.sleep(.05)
    raise AssertionError("subprocess readiness timed out")


def test_official_client_process_restart_and_observed_effect(tmp_path, grant_body):
    agent_token, provider_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    agent_file, provider_file = tmp_path / "agent-token", tmp_path / "provider-token"
    for path, value in [(agent_file, agent_token), (provider_file, provider_token)]:
        path.write_text(value)
        path.chmod(0o600)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"agent": "agent:pilot", "owner": "human:owner", "account": "pilot@example.test"}))
    provider_port, mcp_port = port(), port()
    upstream = f"http://127.0.0.1:{provider_port}"
    endpoint = f"http://127.0.0.1:{mcp_port}/mcp"
    human_socket = tmp_path / "human.sock"
    oracle_dir = tmp_path / "oracle"
    provider_command = [sys.executable, "-m", "tests.fixtures.provider_server", "--directory", str(oracle_dir),
                        "--token-file", str(provider_file), "--port", str(provider_port)]
    command = [sys.executable, "-m", "moraine_email.server", "--state-dir", str(tmp_path / "state"),
               "--config", str(config), "--agent-token-file", str(agent_file),
               "--provider-token-file", str(provider_file), "--provider-url", upstream,
               "--opa-binary", str(ROOT / ".tools/opa"), "--human-socket", str(human_socket),
               "--human-uid", str(os.getuid()), "--port", str(mcp_port)]
    transcript = []

    async def tools(actions):
        async with httpx.AsyncClient(headers={"Authorization": "Bearer " + agent_token}, trust_env=False) as http, \
                streamable_http_client(endpoint, http_client=http) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                names = {tool.name for tool in (await session.list_tools()).tools}
                assert names == {"list_context", "read_context", "propose_reply", "get_request"}
                replies = []
                for name, arguments, expected_error in actions:
                    response = await session.call_tool(name, arguments)
                    assert response.isError is expected_error
                    replies.append(response.structuredContent)
                    transcript.append({"tool": name, "is_error": response.isError,
                                       "result": response.structuredContent})
                return replies

    with process(provider_command, tmp_path / "provider.log") as upstream_process:
        ready(upstream_process, upstream + "/send")
        with process(command, tmp_path / "broker-first.log") as broker_process:
            ready(broker_process, endpoint, human_socket)
            grant = call(human_socket, {"operation": "create_grant", "body": grant_body})
            proposal = {"grant_id": grant["grant_id"], "idempotency_key": "process-e2e",
                        "reply_to_ref": "message-1", "body_text": "Mardi à 10 h convient. Merci !"}
            results = asyncio.run(tools([
                ("read_context", {"grant_id": grant["grant_id"], "resource_ref": "outside", "version": 1}, True),
                ("read_context", {"grant_id": grant["grant_id"], "resource_ref": "message-1", "version": 1}, False),
                ("propose_reply", proposal, False)]))
            request = results[-1]
            assert request["state"] == "pending"
        # No tool call/session held open while the service restarts or human reviews.
        assert not human_socket.exists()
        with process(command, tmp_path / "broker-restarted.log") as broker_process:
            ready(broker_process, endpoint, human_socket)
            rid = request["request_id"]
            view = call(human_socket, {"operation": "review", "request_id": rid})
            sent = call(human_socket, {"operation": "decide_review", "request_id": rid,
                                      "action_digest": view["action_digest"], "nonce": view["nonce"], "decision": "approve"})
            assert sent["state"] == "accepted"
            assert sent["result"]["delivery_status"] == "unverified"
            replay, receipt = asyncio.run(tools([("propose_reply", proposal, False),
                                                ("get_request", {"request_id": rid}, False)]))
            assert replay["state"] == receipt["state"] == "accepted"
            call(human_socket, {"operation": "revoke_grant", "grant_id": grant["grant_id"]})
            redacted = asyncio.run(tools([("get_request", {"request_id": rid}, False)]))[0]
            assert set(redacted) == {"request_id", "state", "reason"}
            assert redacted["state"] == "accepted"
            effects = [json.loads(line) for line in (oracle_dir / "effects.jsonl").read_text().splitlines()]
            assert len(effects) == 1
            assert effects[0]["mime_b64"] == view["snapshot"]["prepared_reply"]["mime_b64"]
            assert len((oracle_dir / "attempts.jsonl").read_text().splitlines()) == 1
    (tmp_path / "transcript.json").write_text(json.dumps(transcript, ensure_ascii=False, indent=2))
    for path in tmp_path.glob("*.log"):
        assert agent_token not in path.read_text() and provider_token not in path.read_text()
