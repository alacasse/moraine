"""Exercise the lab's public transports, independent effects, and failure reporting."""
from contextlib import contextmanager
import http.client
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading

import httpx
import pytest

from lab.runtime import Laboratory, LabError, Run, ROOT
from lab.scenarios import SCENARIOS, run_suite
from lab.server import Console, Handler


@contextmanager
def laboratory():
    # Unix socket paths must fit sockaddr_un even with long pytest test names.
    with tempfile.TemporaryDirectory(prefix="ml-") as root:
        lab = Laboratory(Path(root) / "lab")
        try:
            yield lab
        finally:
            lab.close()


def test_real_campaign_and_independent_evidence():
    expected = {
        "approval": ("accepted", 1, 1), "human_rejection": ("rejected", 0, 0),
        "revocation": ("denied", 0, 0), "expiration": ("denied", 0, 0),
        "replay": ("accepted", 1, 1), "restart": ("accepted", 1, 1),
        "provider_rejection": ("failed", 1, 0), "unknown_after_effect": ("unknown", 1, 1),
        "outside_scope": (None, 0, 0)}
    with laboratory() as lab:
        result = run_suite(lab)
        assert result["status"] == "passed", result
        assert [row["scenario"] for row in result["results"]] == list(SCENARIOS)
        for row in result["results"]:
            assert row["passed"]
            actual_state = row["request"]["state"] if row["request"] else None
            assert (actual_state, row["attempts"], row["effects"]) == expected[row["scenario"]]
            report = json.loads(Path(row["evidence"]).read_text())
            assert report["closed"] and not report["processes"]
            assert all(check["passed"] for check in report["checks"])
            if row["effects"]:
                assert {"received_bytes_equal_reviewed_bytes", "received_envelope_and_content"} <= {
                    check["name"] for check in report["checks"]}
            serialized = json.dumps(report)
            assert '"nonce"' not in serialized
            for secret_path in Path(row["evidence"]).parent.glob("*-token"):
                assert secret_path.read_text() not in serialized
            for event in report["events"]:
                if event["kind"] == "process.stopped":
                    with pytest.raises(ProcessLookupError):
                        os.kill(event["data"]["pid"], 0)


def test_http_operator_boundary_and_stale_page():
    with laboratory() as lab:
        run = lab.new()
        console = Console(lab)
        thread = threading.Thread(target=console.serve_forever)
        thread.start()
        try:
            with httpx.Client(base_url=console.origin, trust_env=False) as client:
                auth = {"Authorization": "Bearer " + console.token}
                payload = {"action": "propose", "run_id": run.id, "body": "Texte"}
                assert client.get("/").status_code == 200
                assert console.token not in client.get("/app.js").text
                assert client.get("/api/state").status_code == 401
                assert client.post("/api/action", json=payload).status_code == 401
                assert client.post("/api/action", json=payload, headers={**auth, "Origin": "https://foreign.invalid"}).status_code == 403
                assert client.post("/api/action", json=payload, headers={**auth, "Host": "foreign.invalid"}).status_code == 403
                assert client.get("/../connection.json", headers=auth).status_code == 404
                assert client.get("/%2e%2e/connection.json", headers=auth).status_code == 404
                assert client.get("/api/state?token=x", headers=auth).status_code == 400
                assert client.post("/api/action", content='{"action":"new","action":"propose","run_id":null}', headers={**auth, "Content-Type":"application/json"}).status_code == 400
                assert client.post("/api/action", content="x" * 32769, headers={**auth, "Content-Type":"application/json"}).status_code == 400
                connection = http.client.HTTPConnection("127.0.0.1", console.server_port)
                connection.putrequest("GET", "/api/state")
                connection.putheader("Authorization", "Bearer " + console.token)
                connection.putheader("Authorization", "Bearer " + console.token)
                connection.endheaders()
                assert connection.getresponse().status == 400
                connection.close()
                assert run.records("attempts") == [] and run.request is None
                assert client.post("/api/action", json={"action":"new", "run_id":run.id}, headers=auth).status_code == 200
                assert client.post("/api/action", json=payload, headers=auth).status_code == 409
                assert lab.current.request is None and lab.current.records("attempts") == []
                assert Path(lab.directory / "connection.json").stat().st_mode & 0o777 == 0o600
                assert console.token not in client.get("/api/state", headers=auth).text
        finally:
            console.shutdown()
            thread.join(timeout=5)
            console.close()


def test_failed_start_preserves_diagnostics_and_reaps_children(monkeypatch):
    original_start = Run.start

    def fail_broker(self, name, command):
        if name == "broker":
            command = [sys.executable, "-c", "raise RuntimeError('intentional broker startup failure')"]
        original_start(self, name, command)

    with laboratory() as lab:
        with monkeypatch.context() as patch:
            patch.setattr(Run, "start", fail_broker)
            with pytest.raises(LabError, match="broker_exited_"):
                lab.new()
        report_path = next(lab.directory.glob("run-*/report.json"))
        report = json.loads(report_path.read_text())
        assert report["closed"] and "broker_exited_" in report["error"]
        assert "intentional broker startup failure" in report_path.with_name("broker.log").read_text()
        for event in report["events"]:
            if event["kind"] == "process.started":
                with pytest.raises(ProcessLookupError):
                    os.kill(event["data"]["pid"], 0)
        assert lab.new().read()["text"]


def test_request_with_delayed_body_cannot_restart_closed_console(monkeypatch):
    accepted = threading.Event()
    original_boundary = Handler.boundary

    def boundary(self, **kwargs):
        result = original_boundary(self, **kwargs)
        accepted.set()
        return result

    monkeypatch.setattr(Handler, "boundary", boundary)
    with laboratory() as lab:
        run = lab.new()
        console = Console(lab)
        thread = threading.Thread(target=console.serve_forever)
        thread.start()
        connection = socket.create_connection(("127.0.0.1", console.server_port), timeout=5)
        try:
            payload = json.dumps({"action": "new", "run_id": run.id}).encode()
            connection.sendall((f"POST /api/action HTTP/1.1\r\nHost: 127.0.0.1:{console.server_port}\r\n"
                f"Authorization: Bearer {console.token}\r\nContent-Type: application/json\r\n"
                f"Content-Length: {len(payload)}\r\n\r\n").encode())
            assert accepted.wait(timeout=3)
            # shutdown waits for the accept loop; the handler remains blocked on
            # this client's body while close retires the owned subprocesses.
            console.shutdown()
            thread.join(timeout=5)
            console.close()
            connection.sendall(payload)
            response = http.client.HTTPResponse(connection)
            response.begin()
            assert response.status == 409
            assert json.loads(response.read())["error"] == "console_closing"
            assert lab.current is run and run.closed and not run.children
            assert len(list(lab.directory.glob("run-*"))) == 1
        finally:
            connection.close()
            console.shutdown()
            thread.join(timeout=5)
            console.close()


def test_runtime_rejects_repository_and_reuse_before_writing():
    destination = ROOT / "forbidden-lab-runtime"
    with pytest.raises(LabError, match="outside_repository"):
        Laboratory(destination)
    assert not destination.exists()
    with tempfile.TemporaryDirectory(prefix="ml-") as existing:
        with pytest.raises(FileExistsError):
            Laboratory(existing)


def test_unreadable_effects_are_failure_not_an_empty_inbox():
    with laboratory() as lab:
        run = lab.new()
        (run.directory / "provider" / "effects.jsonl").write_text("broken-json\n")
        with pytest.raises(json.JSONDecodeError):
            run.snapshot()
        with pytest.raises(json.JSONDecodeError):
            run.close()
        assert not run.children
        report = json.loads((run.directory / "report.json").read_text())
        assert report["error"].startswith("evidence_unreadable:")
        assert report["attempts"] is None and report["effects"] is None
