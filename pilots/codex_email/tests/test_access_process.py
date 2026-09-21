"""Real MCP, human CLI, broker/OPA and provider processes. Human is simulated here."""
import asyncio
import json
import sqlite3
import subprocess
import sys

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from examples.access_demo import ROOT, child_process, commands, prepare, ready
from moraine_email.human_cli import call


def test_access_processes_restart_and_independent_provider_evidence(tmp_path):
    directory = tmp_path / "runtime"
    config = prepare(directory)
    token = (directory / "agent-token").read_text()
    provider_command, broker_command = commands(directory)
    human_socket = directory / "human.sock"

    async def tools(actions):
        async with httpx.AsyncClient(headers={"Authorization": "Bearer " + token}, trust_env=False) as http, \
                streamable_http_client(config["endpoint"], http_client=http) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                replies = []
                for name, arguments, error in actions:
                    result = await session.call_tool(name, arguments)
                    assert result.isError is error, result
                    replies.append(result.structuredContent if not error else result.content[0].text)
                return replies

    with child_process(provider_command, directory / "provider.log") as upstream:
        ready(upstream, f'http://127.0.0.1:{config["provider_port"]}/messages')
        with child_process(broker_command, directory / "broker.log") as broker:
            ready(broker, config["endpoint"], human_socket)
            results = asyncio.run(tools([
                ("get_access", {"resource_set_ref": "travaux-demo"}, False),
                ("request_access", {"resource_set_ref": "travaux-demo", "idempotency_key": "process-access", "approved": True}, True),
                ("request_access", {"resource_set_ref": "travaux-demo", "idempotency_key": "process-access"}, False)]))
            assert results[0]["decision"] == "absent"
            assert results[1] == "invalid_tool_arguments"
            pending = results[2]
            assert pending["decision"] == "pending" and "grant_id" not in pending
            assert not (directory / "provider/reads.jsonl").exists()
            with sqlite3.connect(directory / "state/broker.sqlite3") as db:
                assert db.execute("SELECT decision FROM access_requests").fetchall() == [("pending",)]
                assert db.execute("SELECT count(*) FROM resources").fetchone()[0] == 0

        with child_process(broker_command, directory / "broker.log") as broker:
            ready(broker, config["endpoint"], human_socket)
            recovered = asyncio.run(tools([("get_access", {"resource_set_ref": "travaux-demo"}, False)]))[0]
            assert recovered == pending
            # Exercise rendering + explicit CLI choice, with an operator simulated by this test.
            cli = subprocess.run([sys.executable, "-m", "moraine_email.human_cli", "--socket", str(human_socket),
                                  "review-access", pending["request_id"]], input="approve\n",
                                 capture_output=True, text=True, cwd=ROOT, timeout=15)
            assert cli.returncode == 0 and '"retrieval": "ready"' in cli.stdout
            assert '"kind": "context_read"' in cli.stdout and "Future messages are excluded" in cli.stdout
            active = asyncio.run(tools([("get_access", {"resource_set_ref": "travaux-demo"}, False)]))[0]

        with child_process(broker_command, directory / "broker.log") as broker:
            ready(broker, config["endpoint"], human_socket)
            retrieved = asyncio.run(tools([("get_access", {"resource_set_ref": "travaux-demo"}, False)]))[0]
            assert retrieved == active
            gid = retrieved["grant_id"]
            metadata = asyncio.run(tools([("list_context", {"grant_id": gid}, False)]))[0]["resources"]
            assert len(metadata) == 2
            results = asyncio.run(tools([
                ("read_context", {"grant_id": gid, "resource_ref": r["resource_ref"], "version": r["version"]}, False)
                for r in metadata]))
            assert any("mardi à 10 h" in r["text"] for r in results)
            assert any("240 euros" in r["text"] for r in results)
            reads = [json.loads(line) for line in (directory / "provider/reads.jsonl").read_text().splitlines()]
            assert len(reads) == 1 and reads[0]["message_ids"] == ["upstream-1", "upstream-2"]
            assert all(r["source_digest"] == reads[0]["source_digests"][r["provider_message_id"]] for r in metadata)
            assert "TEMOIN-HORS-PERIMETRE" not in json.dumps(results)
            call(human_socket, {"operation": "revoke_grant", "grant_id": gid})
            denied = asyncio.run(tools([
                ("get_access", {"resource_set_ref": "travaux-demo"}, False),
                ("list_context", {"grant_id": gid}, True),
                ("read_context", {"grant_id": gid, "resource_ref": metadata[0]["resource_ref"], "version": 1}, True)]))
            assert denied[0]["access"] == "revoked"
            assert denied[1:] == ["scope_denied", "scope_denied"]
    for path in directory.glob("*.log"):
        assert token not in path.read_text()
        assert (directory / "provider-token").read_text() not in path.read_text()
