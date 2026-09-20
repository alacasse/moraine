"""Own real subprocesses, exercise public transports, retain independent evidence."""
from __future__ import annotations

import asyncio
import base64
from email import policy
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from moraine_email.human_cli import call

ROOT = Path(__file__).resolve().parents[1]
PROVIDER_MODES = {"normal", "reject_before", "accept_then_disconnect", "malformed_success"}


class LabError(Exception):
    pass


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def source_message():
    return {"resource_ref": "message-1", "provider_message_id": "local-incoming-1",
            "kind": "message", "version": 1, "title": "Réunion de mardi",
            "text": "Bonjour, peux-tu confirmer la réunion mardi à 10 h ? Nous serons trois. Merci, Camille.",
            "from_address": "camille@example.test", "reply_address": "camille@example.test",
            "message_id": "<meeting@example.test>", "thread_id": "meeting-1"}


class Run:
    def __init__(self, directory: Path, *, provider_mode="normal", ttl=600, actor="scripted"):
        if provider_mode not in PROVIDER_MODES or type(ttl) not in (int, float) or not 1 <= ttl <= 1800:
            raise LabError("invalid_run_options")
        if actor not in {"scripted", "assistant", "operator"}:
            raise LabError("invalid_actor")
        self.directory = Path(directory)
        self.directory.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.id = self.directory.name
        self.actor = actor
        self.provider_mode = provider_mode
        self.children = {}
        self.logfiles = {}
        self.events = []
        self.checks = []
        self.view = None
        self.proposal = None
        self.request = None
        self.grant = None
        self.context = None
        self.error = None
        self.closed = False
        self.message = source_message()
        self.witness = {**source_message(), "resource_ref": "message-private",
                        "provider_message_id": "local-private-2", "thread_id": "private-2",
                        "message_id": "<private@example.test>", "title": "Hors sélection",
                        "text": "TEMOIN-NON-DELEGUE-7d21 : le rendez-vous confidentiel est jeudi."}
        self.tokens = {name: secrets.token_urlsafe(32) for name in ("agent", "provider")}
        for name, token in self.tokens.items():
            path = self.directory / (name + "-token")
            path.write_text(token)
            path.chmod(0o600)
        write_json(self.directory / "config.json", {"agent": "agent:pilot", "owner": "human:owner",
                                                   "account": "pilot@example.test"})
        self.provider_port = free_port()
        self.broker_port = free_port()
        while self.broker_port == self.provider_port:
            self.broker_port = free_port()
        self.endpoint = f"http://127.0.0.1:{self.broker_port}/mcp"
        self.human_socket = self.directory / "human.sock"
        self.broker_command = [sys.executable, "-m", "moraine_email.server",
            "--state-dir", str(self.directory / "state"), "--config", str(self.directory / "config.json"),
            "--agent-token-file", str(self.directory / "agent-token"),
            "--provider-token-file", str(self.directory / "provider-token"),
            "--provider-url", f"http://127.0.0.1:{self.provider_port}",
            "--opa-binary", str(ROOT / ".tools/opa"), "--human-socket", str(self.human_socket),
            "--human-uid", str(os.getuid()), "--port", str(self.broker_port)]
        try:
            self.start("provider", [sys.executable, "-m", "tests.fixtures.provider_server",
                "--directory", str(self.directory / "provider"),
                "--token-file", str(self.directory / "provider-token"),
                "--port", str(self.provider_port), "--initial-mode", provider_mode])
            self.wait_ready("provider", f"http://127.0.0.1:{self.provider_port}/send")
            self.start("broker", self.broker_command)
            self.wait_ready("broker", self.endpoint, self.human_socket)
            self.human("create_grant", body={
                "agent": "agent:pilot", "account_id": "pilot@example.test", "expires_at": time.time() + 600,
                "recipient": self.witness["reply_address"], "reply_to_ref": "message-private",
                "resources": [self.witness]})
            self.grant = self.human("create_grant", body={
                "agent": "agent:pilot", "account_id": "pilot@example.test", "expires_at": time.time() + ttl,
                "recipient": self.message["reply_address"], "reply_to_ref": "message-1",
                "resources": [self.message]})
            self.event("run.ready", {"actor": actor, "provider_mode": provider_mode})
        except BaseException as exc:
            self.error = self.clean(str(exc))
            self.event("run.start_failed", {"error": self.error})
            self.close()
            raise

    def clean(self, value):
        if isinstance(value, dict):
            return {key: self.clean(item) for key, item in value.items() if key not in {"nonce", "token"}}
        if isinstance(value, list):
            return [self.clean(item) for item in value]
        if isinstance(value, str):
            for secret in self.tokens.values():
                value = value.replace(secret, "[redacted]")
        return value

    def event(self, kind, data):
        item = self.clean({"sequence": len(self.events) + 1, "at": time.time(), "kind": kind, "data": data})
        self.events.append(item)
        with (self.directory / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(item, ensure_ascii=False, allow_nan=False) + "\n")

    def start(self, name, command):
        log = (self.directory / (name + ".log")).open("a")
        try:
            process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=log, start_new_session=True,
                env={"PATH": os.defpath, "PYTHONPATH": str(ROOT / "src") + os.pathsep + str(ROOT),
                     "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8"})
        except BaseException:
            log.close()
            raise
        self.children[name] = process
        self.logfiles[name] = log
        self.event("process.started", {"name": name, "pid": process.pid, "command": command})

    def wait_ready(self, name, endpoint, unix_path=None):
        deadline = time.monotonic() + 12
        with httpx.Client(timeout=.3, trust_env=False) as client:
            while time.monotonic() < deadline:
                process = self.children[name]
                if process.poll() is not None:
                    raise LabError(f"{name}_exited_{process.returncode}: inspect {name}.log")
                try:
                    response = client.post(endpoint, json={})
                    if response.status_code == 401 and (unix_path is None or unix_path.is_socket()):
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(.04)
        raise LabError(f"{name}_readiness_timeout: inspect {name}.log")

    def stop(self, name):
        process = self.children.get(name)
        if process is None:
            return
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
        finally:
            # Also retire an orphan OPA in our own broker process group. This is
            # harness cleanup, never evidence of systemd supervision.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
            self.logfiles.pop(name).close()
            self.children.pop(name)
            self.event("process.stopped", {"name": name, "pid": process.pid, "returncode": process.returncode})

    def restart(self):
        self.stop("broker")
        self.start("broker", self.broker_command)
        self.wait_ready("broker", self.endpoint, self.human_socket)
        self.refresh()

    def human(self, operation, **arguments):
        try:
            result = call(self.human_socket, {"operation": operation, **arguments})
            self.event("human." + operation, {"result": result})
            return result
        except Exception as exc:
            self.event("human." + operation, {"error": str(exc)})
            raise

    async def _agent(self, name, arguments):
        async with asyncio.timeout(15):
            async with httpx.AsyncClient(headers={"Authorization": "Bearer " + self.tokens["agent"]},
                                         trust_env=False) as client:
                async with streamable_http_client(self.endpoint, http_client=client) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        response = await session.call_tool(name, arguments)
                        return {"is_error": bool(response.isError), "result": response.structuredContent,
                                "content": [item.text for item in response.content if hasattr(item, "text")]}

    def agent(self, name, arguments):
        response = asyncio.run(self._agent(name, arguments))
        self.event("mcp." + name, {"arguments": arguments, **response})
        return response

    def read(self):
        listing = self.agent("list_context", {"grant_id": self.grant["grant_id"]})
        result = self.agent("read_context", {"grant_id": self.grant["grant_id"],
                                             "resource_ref": "message-1", "version": 1})
        if listing["is_error"] or result["is_error"]:
            raise LabError("context_refused")
        self.context = result["result"]
        return self.context

    def propose(self, body, *, new_key=False):
        if not isinstance(body, str) or not body.strip() or len(body.encode("utf-8")) > 16384:
            raise LabError("invalid_reply")
        key = str(uuid.uuid4()) if new_key or self.proposal is None else self.proposal["idempotency_key"]
        proposal = {"grant_id": self.grant["grant_id"], "idempotency_key": key,
                    "reply_to_ref": "message-1", "body_text": body}
        response = self.agent("propose_reply", proposal)
        if not response["is_error"]:
            self.proposal = proposal
            self.request = response["result"]
        return response

    def refresh(self):
        if self.request is not None:
            response = self.agent("get_request", {"request_id": self.request["request_id"]})
            if response["is_error"]:
                raise LabError("request_status_refused")
            self.request = response["result"]
        return self.request

    def review(self):
        if self.request is None:
            raise LabError("no_proposal")
        self.view = self.human("review", request_id=self.request["request_id"])
        return self.clean(self.view)

    def decide(self, decision):
        if decision not in {"approve", "reject"} or self.view is None:
            raise LabError("review_required")
        self.request = self.human("decide_review", request_id=self.view["request_id"],
            action_digest=self.view["action_digest"], nonce=self.view["nonce"], decision=decision)
        return self.request

    def revoke(self):
        result = self.human("revoke_grant", grant_id=self.grant["grant_id"])
        self.refresh()
        return result

    def records(self, name):
        path = self.directory / "provider" / (name + ".jsonl")
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def assert_check(self, name, condition, **observed):
        item = {"name": name, "passed": bool(condition), "observed": observed}
        self.checks.append(item)
        self.event("assertion", item)
        if not condition:
            raise AssertionError(name + ": " + json.dumps(observed, ensure_ascii=False))

    def verify_delivery(self):
        attempts, effects = self.records("attempts"), self.records("effects")
        self.assert_check("exactly_one_attempt_and_effect", len(attempts) == len(effects) == 1,
                          attempts=len(attempts), effects=len(effects))
        if self.view is None:
            raise LabError("review_required")
        expected = base64.b64decode(self.view["snapshot"]["prepared_reply"]["mime_b64"], validate=True)
        delivered = base64.b64decode(effects[0]["mime_b64"], validate=True)
        self.assert_check("received_bytes_equal_reviewed_bytes", delivered == expected,
                          reviewed_sha256=hashlib.sha256(expected).hexdigest(),
                          delivered_sha256=hashlib.sha256(delivered).hexdigest())
        parsed = BytesParser(policy=policy.default).parsebytes(delivered)
        body = self.proposal["body_text"].replace("\r\n", "\n").replace("\r", "\n")
        if not body.endswith("\n"):
            body += "\n"
        self.assert_check("received_envelope_and_content", not parsed.is_multipart()
            and str(parsed["To"]) == self.message["reply_address"]
            and str(parsed["From"]) == "pilot@example.test"
            and str(parsed["Subject"]) == self.message["title"]
            and str(parsed["In-Reply-To"]) == self.message["message_id"]
            and str(parsed["References"]) == self.message["message_id"]
            and parsed["Cc"] is None and parsed["Bcc"] is None
            and parsed.get_content().replace("\r\n", "\n") == body)

    def snapshot(self):
        inbox = []
        for record in self.records("effects"):
            raw = base64.b64decode(record["mime_b64"], validate=True)
            mime = BytesParser(policy=policy.default).parsebytes(raw)
            inbox.append({"to": str(mime["To"]), "from": str(mime["From"]), "subject": str(mime["Subject"]),
                          "body": mime.get_content(), "sha256": hashlib.sha256(raw).hexdigest()})
        return self.clean({"run_id": self.id, "actor": self.actor, "provider_mode": self.provider_mode,
            "source_message": self.message, "context": self.context, "grant": self.grant,
            "unselected_message": self.witness,
            "request": self.request, "review": self.view, "received": inbox,
            "attempts": len(self.records("attempts")), "effects": len(inbox),
            "processes": {name: {"pid": proc.pid, "running": proc.poll() is None}
                          for name, proc in self.children.items()},
            "events": self.events, "checks": self.checks, "error": self.error,
            "closed": self.closed, "scope": "local_fixture_single_uid_no_systemd_no_ingestion"})

    def save(self):
        try:
            report = self.snapshot()
        except Exception as exc:
            write_json(self.directory / "report.json", self.clean({"run_id": self.id,
                "closed": self.closed, "error": "evidence_unreadable: " + str(exc),
                "events": self.events, "checks": self.checks, "attempts": None, "effects": None}))
            raise
        write_json(self.directory / "report.json", report)

    def close(self):
        if self.closed:
            return
        try:
            self.stop("broker")
        finally:
            self.stop("provider")
            self.closed = True
            self.save()


class Laboratory:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        if self.directory.is_relative_to(ROOT.parents[1]):
            raise LabError("runtime_directory_must_be_outside_repository")
        self.directory.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.lock = threading.RLock()
        self.current = None

    def new(self, *, actor="operator", provider_mode="normal", ttl=600):
        with self.lock:
            if self.current:
                self.current.close()
                self.current = None
            path = self.directory / ("run-" + uuid.uuid4().hex[:12])
            self.current = Run(path, actor=actor, provider_mode=provider_mode, ttl=ttl)
            self.current.save()
            return self.current

    def close(self):
        with self.lock:
            if self.current:
                self.current.close()
