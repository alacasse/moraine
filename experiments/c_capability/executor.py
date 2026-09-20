"""Protected lifecycle: online revocation, exact approvals, replay and dispatch."""
from __future__ import annotations

import fcntl
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from urllib.parse import quote, urlsplit
import uuid

import httpx

from actions import Refusal, canonical, digest, grant_input, shape, submission_input
import capabilities

REVIEW_MAX_AGE = 300


class ProviderFailure(Exception):
    def __init__(self, ambiguous: bool):
        self.ambiguous = ambiguous


class Executor:
    """All methods serialize against one lifecycle lock and a single state owner."""

    def __init__(self, state_dir: Path, provider_url: str, provider_token: str):
        parsed = urlsplit(provider_url)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}):
            raise ValueError("fixture provider must be a loopback HTTP origin")
        state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock_file = (state_dir / "executor.lock").open("a+")
        try:
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock_file.close()
            raise RuntimeError("state directory already has an executor") from None
        self.lock = threading.RLock()
        self.pair = capabilities.keypair(state_dir)
        self.database = state_dir / "executor.sqlite3"
        self.client = httpx.Client(base_url=provider_url.rstrip("/"),
                                   headers={"Authorization": "Bearer " + provider_token},
                                   timeout=3.0, follow_redirects=False, trust_env=False)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS grants (
                    id TEXT PRIMARY KEY, root_revocation_id TEXT NOT NULL UNIQUE,
                    data TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY, actor TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                    submission_hash TEXT NOT NULL, data TEXT NOT NULL,
                    UNIQUE(actor, idempotency_key)
                );
            """)
            rows = db.execute("SELECT id, data FROM requests").fetchall()
            for row in rows:
                record = json.loads(row["data"])
                if record["state"] == "dispatching":
                    record.update(state="unknown", reason="interrupted_dispatch")
                    db.execute("UPDATE requests SET data=? WHERE id=?", (canonical(record), row["id"]))
        os.chmod(self.database, 0o600)
        # Fail startup if the installed library cannot execute our real policy.
        smoke_grant = {"agent": "agent:alice", "account": "alice", "expires_at": int(time.time()) + 60,
                       "recipients": [], "document_ids": ["health"], "merchants": [],
                       "currency": "CAD", "auto_limit_minor": 0, "hard_limit_minor": 1}
        token = capabilities.issue(self.pair, "health", smoke_grant)
        capabilities.authorize(token, grant_id="health", actor="agent:alice",
                               action={"type": "document.read", "account": "alice", "document_id": "health"})

    def close(self) -> None:
        self.client.close()
        self.lock_file.close()

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def human(actor: str) -> None:
        if actor != "human:alice":
            raise Refusal("human_required", 403)

    def create_grant(self, actor: str, body: dict) -> dict:
        self.human(actor)
        grant = grant_input(body)
        with self.lock:
            grant_id = "grant-" + uuid.uuid4().hex
            token = capabilities.issue(self.pair, grant_id, grant)
            with self.connect() as db:
                db.execute("INSERT INTO grants(id, root_revocation_id, data) VALUES (?, ?, ?)",
                           (grant_id, token.revocation_ids[0], canonical(grant)))
            return {"grant_id": grant_id, "capability": token.to_base64()}

    def revoke(self, actor: str, grant_id: str, body: dict) -> dict:
        self.human(actor)
        shape(body, set())
        with self.lock, self.connect() as db:
            row = db.execute("SELECT data FROM grants WHERE id=?", (grant_id,)).fetchone()
            if row is None or json.loads(row["data"])["account"] != "alice":
                raise Refusal("not_found", 404)
            db.execute("UPDATE grants SET revoked=1 WHERE id=?", (grant_id,))
        return {"status": "revoked"}

    def authorize(self, actor: str, submission: dict) -> str:
        if actor not in {"agent:alice", "agent:bob"}:
            raise Refusal("agent_required", 403)
        token = capabilities.verify(submission["capability"], self.pair.public_key)
        with self.connect() as db:
            row = db.execute("SELECT * FROM grants WHERE id=?", (submission["grant_id"],)).fetchone()
        if row is None or row["root_revocation_id"] != token.revocation_ids[0]:
            raise Refusal("grant_binding", 403)
        grant = json.loads(row["data"])
        if grant["agent"] != actor or grant["account"] != submission["action"]["account"]:
            raise Refusal("grant_binding", 403)
        if row["revoked"]:
            raise Refusal("grant_revoked", 403)
        # Expiry and domain rights come from scoped signed Datalog, not the copied grant JSON.
        return capabilities.authorize(token, grant_id=submission["grant_id"], actor=actor,
                                      action=submission["action"])

    def provider_document(self, doc_id: str) -> dict:
        try:
            response = self.client.get("/documents/" + quote(doc_id, safe=""))
            if response.status_code != 200:
                raise ProviderFailure(False)
            value = response.json()
            if (not isinstance(value, dict) or value.get("id") != doc_id
                    or type(value.get("version")) is not int or value["version"] < 1
                    or not isinstance(value.get("content"), str)
                    or not isinstance(value.get("classification"), str)):
                raise ProviderFailure(False)
            return value
        except (httpx.HTTPError, ValueError):
            raise ProviderFailure(False) from None

    def prepare(self, actor: str, submission: dict) -> dict:
        action = submission["action"]
        prepared = json.loads(canonical(action))
        if action["type"] == "email.send":
            attachments = []
            for attachment in action["attachments"]:
                # Earlier authorized reads can consume the remaining validity window.
                # Check again before every protected read, not merely after preparation.
                self.authorize(actor, submission)
                document = self.provider_document(attachment["id"])
                if document["version"] != attachment["version"]:
                    raise Refusal("attachment_version_mismatch", 403)
                attachments.append({"id": document["id"], "version": document["version"],
                                    "content": document["content"]})
            prepared["attachments"] = attachments
        return prepared

    def save(self, record: dict) -> None:
        with self.connect() as db:
            db.execute("INSERT INTO requests VALUES (?, ?, ?, ?, ?) "
                       "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                       (record["request_id"], record["actor"], record["idempotency_key"],
                        record["submission_hash"], canonical(record)))

    @staticmethod
    def visible(record: dict) -> dict:
        state = "unknown" if record["state"] == "dispatching" else record["state"]
        response = {"request_id": record["request_id"], "state": state, "reason": record["reason"]}
        if "action_digest" in record:
            response["action_digest"] = record["action_digest"]
        if record["state"] == "pending":
            response["snapshot"] = record["prepared"]
            response["review_deadline"] = record["review_deadline"]
        if "result" in record:
            response["result"] = record["result"]
        return response

    def submit(self, actor: str, body: dict) -> dict:
        if actor not in {"agent:alice", "agent:bob"}:
            raise Refusal("agent_required", 403)
        submission = submission_input(body)
        submission_hash = digest(submission)
        with self.lock:
            with self.connect() as db:
                previous = db.execute("SELECT * FROM requests WHERE actor=? AND idempotency_key=?",
                                      (actor, submission["idempotency_key"])).fetchone()
            if previous:
                if previous["submission_hash"] != submission_hash:
                    raise Refusal("idempotency_conflict", 409)
                return self.visible(json.loads(previous["data"]))
            now = time.time()
            record = {"request_id": "request-" + uuid.uuid4().hex, "actor": actor,
                      "idempotency_key": submission["idempotency_key"], "submission_hash": submission_hash,
                      "submission": submission, "input_digest": digest(submission["action"]),
                      "execution_id": "execution-" + uuid.uuid4().hex, "submitted_at": now,
                      "review_deadline": now + REVIEW_MAX_AGE, "state": "denied", "reason": "denied"}
            try:
                decision = self.authorize(actor, submission)
                record["prepared"] = self.prepare(actor, submission)
                record["action_digest"] = digest(record["prepared"])
                decision = self.authorize(actor, submission)
                if decision == "review":
                    record.update(state="pending", reason="human_approval_required")
                    self.save(record)
                else:
                    self.dispatch(record)
            except Refusal as error:
                record.update(state="denied", reason=error.reason)
                self.save(record)
            except ProviderFailure:
                record.update(state="failed", reason="provider_prepare_failed")
                self.save(record)
            return self.visible(record)

    def load_request(self, actor: str, request_id: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT data FROM requests WHERE id=?", (request_id,)).fetchone()
        if row is None:
            raise Refusal("not_found", 404)
        record = json.loads(row["data"])
        if actor not in {record["actor"], "human:alice"}:
            raise Refusal("not_found", 404)
        return record

    def get(self, actor: str, request_id: str) -> dict:
        with self.lock:
            return self.visible(self.load_request(actor, request_id))

    def approve(self, actor: str, request_id: str, body: dict) -> dict:
        self.human(actor)
        shape(body, {"action_digest"})
        if not isinstance(body["action_digest"], str):
            raise Refusal("invalid_digest")
        with self.lock:
            record = self.load_request(actor, request_id)
            if record["state"] != "pending":
                raise Refusal("not_pending", 409)
            if body["action_digest"] != record["action_digest"]:
                raise Refusal("digest_mismatch", 409)
            try:
                if time.time() >= record["review_deadline"]:
                    raise Refusal("review_expired", 403)
                self.authorize(record["actor"], record["submission"])
            except Refusal as error:
                record.update(state="denied", reason=error.reason)
                self.save(record)
                return self.visible(record)
            # Human and snapshot digest are recorded durably before the reserved dispatch.
            record["approval"] = {"actor": actor, "digest": body["action_digest"], "time": time.time()}
            self.dispatch(record)
            return self.visible(record)

    def dispatch(self, record: dict) -> None:
        record.update(state="dispatching", reason="dispatch_reserved")
        self.save(record)
        try:
            # The reservation commit can block beyond expiry. Reauthorize after
            # it completes, with no intervening persistence before provider IO.
            decision = self.authorize(record["actor"], record["submission"])
            if decision == "review" and "approval" not in record:
                raise Refusal("human_approval_required", 403)
            if "approval" in record and time.time() >= record["review_deadline"]:
                raise Refusal("review_expired", 403)
            if record["prepared"]["type"] == "document.read":
                result = self.provider_document(record["prepared"]["document_id"])
            else:
                try:
                    response = self.client.post("/effects", json={"execution_id": record["execution_id"],
                                                                  "action": record["prepared"]})
                except httpx.HTTPError:
                    raise ProviderFailure(True) from None
                if not 200 <= response.status_code < 300:
                    # The benchmark provider explicitly guarantees no effect on its 503/4xx paths.
                    raise ProviderFailure(False)
                try:
                    result = response.json()
                except ValueError:
                    raise ProviderFailure(True) from None
                if (not isinstance(result, dict) or not isinstance(result.get("effect_id"), str)
                        or result.get("execution_id") != record["execution_id"]):
                    raise ProviderFailure(True)
            record.update(state="executed", reason="provider_confirmed", result=result)
        except Refusal as error:
            # No provider IO has started, so the durable reservation can become
            # a terminal denial. A crash before this save remains unknown.
            record.update(state="denied", reason=error.reason)
        except ProviderFailure as error:
            record.update(state="unknown" if error.ambiguous else "failed",
                          reason="provider_outcome_unknown" if error.ambiguous else "provider_rejected")
        self.save(record)
