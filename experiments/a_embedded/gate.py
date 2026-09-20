"""Embedded delegated execution. Authentication is the trusted host's responsibility."""
from __future__ import annotations

import asyncio
import fcntl
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3
import time
import uuid

from models import Approval, Grant, Principal, Submission
from policy import Policy
from provider import ProviderClient, ProviderRejected, ProviderUnknown


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Refusal(Exception):
    def __init__(self, reason: str, status=403):
        self.reason, self.status = reason, status
        super().__init__(reason)


class ExecutionGate:
    """One process owns one state directory; one event loop owns this instance.

    The lock intentionally spans bounded downstream I/O: approval/revocation
    linearize before or after dispatch. They cannot recall a sent operation.
    """

    REVIEW_MAX_AGE = 300

    def __init__(self, state_dir: Path, provider: ProviderClient, *, policy: Policy | None = None):
        self.policy = policy or Policy()
        self.provider = provider
        state_dir = Path(state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)
        self._ownership = (state_dir / "gate.lock").open("a")
        try:
            fcntl.flock(self._ownership, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._ownership.close()
            raise RuntimeError("state directory already has a live gate") from None
        self.db = sqlite3.connect(state_dir / "gate.sqlite3")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS grants (id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY, actor TEXT NOT NULL, idem TEXT NOT NULL,
                submitted TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(actor, idem)
            );
            CREATE TABLE IF NOT EXISTS transitions (
                sequence INTEGER PRIMARY KEY, request_id TEXT NOT NULL,
                state TEXT NOT NULL, reason TEXT NOT NULL, at INTEGER NOT NULL
            );
        """)
        self.lock = asyncio.Lock()
        for row in self.db.execute("SELECT data FROM requests").fetchall():
            request = json.loads(row["data"])
            if request["state"] == "executing":
                self._transition(request, "unknown", "interrupted_dispatch")
            elif request["state"] == "preparing":
                self._transition(request, "failed", "interrupted_preparation")

    @staticmethod
    def _human(actor: Principal):
        if actor.kind != "human" or actor.id != "human:alice" or actor.account != "alice":
            raise Refusal("human_required")

    @staticmethod
    def _agent(actor: Principal):
        if actor.kind != "agent":
            raise Refusal("agent_required")

    def _grant(self, grant_id: str):
        row = self.db.execute("SELECT data FROM grants WHERE id=?", (grant_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def _request(self, request_id: str):
        row = self.db.execute("SELECT data FROM requests WHERE id=?", (request_id,)).fetchone()
        if not row:
            raise Refusal("not_found", 404)
        return json.loads(row["data"])

    def _transition(self, request, state, reason):
        request.update(state=state, reason=reason)
        with self.db:
            self.db.execute("UPDATE requests SET data=? WHERE id=?", (canonical(request), request["request_id"]))
            self.db.execute("INSERT INTO transitions(request_id,state,reason,at) VALUES(?,?,?,?)",
                            (request["request_id"], state, reason, int(time.time())))

    @staticmethod
    def _outcome(request):
        result = {key: request[key] for key in ("request_id", "state", "reason")}
        if result["state"] in {"preparing", "executing"}:
            # A cancelled host coroutine or a post-dispatch SQLite failure can
            # leave an internal phase visible before process recovery runs.
            result.update(state="unknown", reason="operation_interrupted")
        if request["state"] == "pending":
            result["action_digest"] = request["action_digest"]
        if request["state"] == "executed":
            result["result"] = request["result"]
        return result

    async def create_grant(self, actor: Principal, spec: dict) -> dict:
        self._human(actor)
        grant = Grant.model_validate(spec).model_dump()
        if grant["account"] != actor.account or grant["agent"] != "agent:alice":
            raise Refusal("grant_scope_forbidden")
        async with self.lock:
            if grant["expires_at"] <= int(time.time()):
                raise Refusal("grant_expired", 400)
            grant.update(revoked=False, creator=actor.id)
            identifier = str(uuid.uuid4())
            with self.db:
                self.db.execute("INSERT INTO grants VALUES(?,?)", (identifier, canonical(grant)))
            return {"grant_id": identifier}

    async def revoke(self, actor: Principal, grant_id: str):
        self._human(actor)
        async with self.lock:
            grant = self._grant(grant_id)
            if not grant or grant["creator"] != actor.id or grant["account"] != actor.account:
                raise Refusal("not_found", 404)
            grant["revoked"] = True
            with self.db:
                self.db.execute("UPDATE grants SET data=? WHERE id=?", (canonical(grant), grant_id))
            return {"status": "revoked"}

    async def submit(self, actor: Principal, grant_id: str, key: str, action: dict):
        self._agent(actor)
        proposal = Submission.model_validate({"grant_id": grant_id, "idempotency_key": key, "action": action})
        proposed = proposal.model_dump()
        submitted = canonical(proposed)
        action = proposed["action"]
        async with self.lock:
            previous = self.db.execute("SELECT submitted,data FROM requests WHERE actor=? AND idem=?",
                                       (actor.id, key)).fetchone()
            if previous:
                if previous["submitted"] != submitted:
                    raise Refusal("idempotency_conflict", 409)
                return self._outcome(json.loads(previous["data"]))
            request = {
                "request_id": str(uuid.uuid4()), "actor": actor.id, "grant_id": grant_id,
                "account": action["account"], "state": "preparing", "reason": "preparing",
                "created_at": int(time.time()), "policy_hash": self.policy.backend.policy_hash,
                "execution_id": str(uuid.uuid4()),
            }
            with self.db:
                self.db.execute("INSERT INTO requests VALUES(?,?,?,?,?)",
                                (request["request_id"], actor.id, key, submitted, canonical(request)))
            grant = self._grant(grant_id)
            if (not grant or actor.account != grant["account"]
                    or not await self.policy.allows(actor.id, action, grant, int(time.time()))):
                self._transition(request, "denied", "not_authorized")
                return self._outcome(request)
            prepared = json.loads(canonical(action))
            try:
                if action["type"] == "email.send":
                    for attachment in prepared["attachments"]:
                        # Scope is already authorized under the lifecycle lock;
                        # time can still advance during a preceding provider read.
                        if int(time.time()) >= grant["expires_at"]:
                            self._transition(request, "denied", "grant_expired")
                            return self._outcome(request)
                        document = await self.provider.document(attachment["id"])
                        if document["version"] != attachment["version"]:
                            self._transition(request, "denied", "attachment_version_mismatch")
                            return self._outcome(request)
                        attachment["content"] = document["content"]
            except ProviderRejected:
                self._transition(request, "failed", "preparation_failed")
                return self._outcome(request)
            envelope = {"version": 1, "actor": actor.id, "account": action["account"],
                        "grant_id": grant_id, "action": prepared}
            request.update(snapshot=envelope, action_digest=hashlib.sha256(canonical(envelope).encode()).hexdigest(),
                           review_deadline=min(request["created_at"] + self.REVIEW_MAX_AGE, grant["expires_at"]))
            # Preparation may have crossed expiry. Reevaluate before review or dispatch.
            if not await self.policy.allows(actor.id, prepared, grant, int(time.time())):
                self._transition(request, "denied", "not_authorized")
            elif (action["type"] == "email.send" or
                  action["type"] == "order.create" and action["amount_minor"] > grant["auto_limit_minor"]):
                self._transition(request, "pending", "human_review_required")
            else:
                await self._execute(request, grant)
            return self._outcome(request)

    async def inspect(self, actor: Principal, request_id: str):
        async with self.lock:
            request = self._request(request_id)
            if actor.kind == "human":
                self._human(actor)
                authorized = request["account"] == actor.account
            else:
                authorized = actor.id == request["actor"] and actor.account == request["account"]
            if not authorized:
                raise Refusal("not_found", 404)
            result = self._outcome(request)
            if "snapshot" in request:
                result["snapshot"] = request["snapshot"]
                result["action_digest"] = request["action_digest"]
                result["review_deadline"] = request["review_deadline"]
            return result

    async def approve(self, actor: Principal, request_id: str, digest: str):
        self._human(actor)
        Approval.model_validate({"action_digest": digest})
        async with self.lock:
            request = self._request(request_id)
            if request["account"] != actor.account:
                raise Refusal("not_found", 404)
            if request["state"] != "pending":
                raise Refusal("request_not_pending", 409)
            if not hmac.compare_digest(digest, request["action_digest"]):
                raise Refusal("digest_mismatch", 409)
            if int(time.time()) >= request["review_deadline"]:
                self._transition(request, "denied", "review_expired")
                return self._outcome(request)
            grant = self._grant(request["grant_id"])
            if not grant:
                self._transition(request, "denied", "not_authorized")
            else:
                await self._execute(request, grant)
            return self._outcome(request)

    async def _execute(self, request, grant):
        action = request["snapshot"]["action"]
        reviewing = request["state"] == "pending"
        if not await self.policy.allows(request["actor"], action, grant, int(time.time())):
            self._transition(request, "denied", "not_authorized")
            return
        # Close the final clock gap after the asynchronous Cedar call.
        if int(time.time()) >= grant["expires_at"]:
            self._transition(request, "denied", "grant_expired")
            return
        if reviewing and int(time.time()) >= request["review_deadline"]:
            self._transition(request, "denied", "review_expired")
            return
        self._transition(request, "executing", "dispatch_started")
        # SQLite lock waits/fsync may cross a deadline after the earlier check.
        # This gates local dispatch, not the time of remote provider acceptance.
        if int(time.time()) >= grant["expires_at"]:
            self._transition(request, "denied", "grant_expired")
            return
        if reviewing and int(time.time()) >= request["review_deadline"]:
            self._transition(request, "denied", "review_expired")
            return
        try:
            if action["type"] == "document.read":
                result = await self.provider.document(action["document_id"])
            else:
                result = await self.provider.execute(request["execution_id"], action)
        except ProviderUnknown:
            self._transition(request, "unknown", "provider_outcome_unknown")
        except ProviderRejected:
            self._transition(request, "failed", "provider_rejected")
        else:
            request["result"] = result
            self._transition(request, "executed", "completed")

    async def aclose(self):
        await self.policy.aclose()
        await self.provider.aclose()
        self.db.close()
        self._ownership.close()
