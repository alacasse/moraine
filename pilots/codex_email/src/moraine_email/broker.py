"""Durable single-owner email broker; no transport can supply trusted identities."""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
import uuid

from .mime import prepare_reply
from .models import PilotError, canonical, digest, validate_grant, validate_proposal
from .policy import PolicyFailure


class Broker:
    def __init__(self, state_dir: Path, policy, provider, *, owner="human:owner",
                 agent="agent:pilot", account="pilot@example.test"):
        self.owner, self.agent, self.account = owner, agent, account
        self.policy, self.provider = policy, provider
        self.lock = threading.RLock()
        self.suspended = False
        self.last_time = time.time()
        self.directory = Path(state_dir)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        self.filelock = (self.directory / "broker.lock").open("a+")
        try:
            fcntl.flock(self.filelock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.filelock.close()
            raise
        self.db = sqlite3.connect(self.directory / "broker.sqlite3", timeout=5,
                                  check_same_thread=False, isolation_level=None)
        os.chmod(self.directory / "broker.sqlite3", 0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA foreign_keys=ON")
        if self.db.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
            self.close()
            raise PilotError("storage_version")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS grants (
                id TEXT PRIMARY KEY, scope TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS resources (
                grant_id TEXT NOT NULL REFERENCES grants(id), ref TEXT NOT NULL,
                metadata TEXT NOT NULL, text TEXT NOT NULL,
                PRIMARY KEY(grant_id,ref)
            );
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY, agent TEXT NOT NULL, grant_id TEXT NOT NULL REFERENCES grants(id),
                account TEXT NOT NULL, source_id TEXT NOT NULL, idem TEXT NOT NULL,
                input_digest TEXT NOT NULL, state TEXT NOT NULL, reason TEXT NOT NULL,
                action_digest TEXT NOT NULL, policy_revision TEXT NOT NULL, review_expires_at REAL NOT NULL,
                snapshot TEXT NOT NULL, nonce_hash TEXT, result TEXT,
                UNIQUE(agent,idem)
            );
            CREATE TABLE IF NOT EXISTS decisions (
                request_id TEXT PRIMARY KEY REFERENCES requests(id), human TEXT NOT NULL,
                action_digest TEXT NOT NULL, decision TEXT NOT NULL, accepted_at REAL NOT NULL,
                expires_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS resolutions (
                request_id TEXT PRIMARY KEY REFERENCES requests(id), human TEXT NOT NULL,
                acknowledged_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE REFERENCES requests(id),
                account TEXT NOT NULL, source_id TEXT NOT NULL, state TEXT NOT NULL,
                resolved_at REAL, result TEXT
            );
            CREATE INDEX IF NOT EXISTS unresolved_source ON executions(account,source_id,state);
            PRAGMA user_version=1;
        """)
        with self.transaction():
            self.db.execute("UPDATE requests SET state='unknown',reason='execution_interrupted' WHERE state='processing'")
            self.db.execute("UPDATE executions SET state='unknown' WHERE state='intent'")
        for suffix in ("-wal", "-shm"):
            path = self.directory / ("broker.sqlite3" + suffix)
            if path.exists():
                os.chmod(path, 0o600)

    def close(self):
        self.db.close()
        self.filelock.close()

    @contextmanager
    def transaction(self):
        try:
            self.db.execute("BEGIN IMMEDIATE")
            yield
            self.db.execute("COMMIT")
        except BaseException as exc:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            if isinstance(exc, sqlite3.Error):
                self.suspended = True
            raise

    def now(self):
        now = time.time()
        if now < self.last_time:
            self.suspended = True
        self.last_time = max(now, self.last_time)
        return now

    def human(self, actor):
        if actor != self.owner:
            raise PilotError("forbidden", status=403)

    def grant(self, grant_id):
        row = self.db.execute("SELECT scope,revoked FROM grants WHERE id=?", (grant_id,)).fetchone()
        if row is None:
            raise PilotError("scope_denied", status=403)
        return {**json.loads(row["scope"]), "id": grant_id, "revoked": bool(row["revoked"])}

    def active(self, grant, actor):
        now = self.now()
        return (not self.suspended and actor == self.agent == grant["agent"]
                and grant["owner"] == self.owner and grant["account_id"] == self.account
                and not grant["revoked"] and now < grant["expires_at"])

    def require_active(self, grant, actor):
        if not self.active(grant, actor):
            raise PilotError("scope_denied", status=403)

    def facts(self, grant, operation, **extra):
        return {"subject": self.agent, "trusted": {"owner": self.owner, "agent": self.agent,
                "account": self.account}, "grant": grant, "now": self.now(),
                "operation": operation, "policy_revision": self.policy.revision, **extra}

    def authorize(self, grant, actor, operation, expected="allow", **extra):
        self.require_active(grant, actor)
        try:
            decision = self.policy.decide(self.facts(grant, operation, **extra))
        except PolicyFailure as exc:
            raise PilotError(exc.reason, status=503) from exc
        # OPA itself may wait: never release content or dispatch after that wait expires.
        self.require_active(grant, actor)
        if decision["decision"] != expected:
            raise PilotError("scope_denied", status=403)

    def create_grant(self, human, body):
        with self.lock:
            self.human(human)
            value = validate_grant(body)
            if value["agent"] != self.agent or value["account_id"] != self.account:
                raise PilotError("scope_denied", status=403)
            resources = value.pop("resources")
            value.update(owner=self.owner, resource_refs=[r["resource_ref"] for r in resources])
            gid = str(uuid.uuid4())
            with self.transaction():
                if value["expires_at"] <= self.now():
                    raise PilotError("grant_expired")
                self.db.execute("INSERT INTO grants(id,scope) VALUES(?,?)", (gid, canonical(value)))
                for resource in resources:
                    metadata = {k: v for k, v in resource.items() if k != "text"}
                    metadata["digest"] = digest(resource)
                    self.db.execute("INSERT INTO resources VALUES(?,?,?,?)",
                                    (gid, resource["resource_ref"], canonical(metadata), resource["text"]))
            return {"grant_id": gid, "expires_at": value["expires_at"]}

    def revoke_grant(self, human, grant_id):
        with self.lock:
            self.human(human)
            self.grant(grant_id)
            with self.transaction():
                self.db.execute("UPDATE grants SET revoked=1 WHERE id=?", (grant_id,))
                self.db.execute("UPDATE requests SET state='denied',reason='grant_revoked',nonce_hash=NULL WHERE grant_id=? AND state='pending'", (grant_id,))
            return {"grant_id": grant_id, "state": "revoked"}

    def list_context(self, agent, grant_id):
        with self.lock:
            grant = self.grant(grant_id)
            self.authorize(grant, agent, "list")
            resources = [json.loads(r[0]) for r in self.db.execute(
                "SELECT metadata FROM resources WHERE grant_id=? ORDER BY ref", (grant_id,))]
            self.require_active(grant, agent)
            return {"grant_id": grant_id, "resources": resources}

    def read_context(self, agent, grant_id, resource_ref, version):
        with self.lock:
            grant = self.grant(grant_id)
            if type(version) is not int:
                raise PilotError("scope_denied", status=403)
            self.authorize(grant, agent, "read", resource_ref=resource_ref)
            row = self.db.execute("SELECT metadata FROM resources WHERE grant_id=? AND ref=?",
                                  (grant_id, resource_ref)).fetchone()
            metadata = json.loads(row[0]) if row else None
            if metadata is None or metadata["version"] != version:
                raise PilotError("scope_denied", status=403)
            self.require_active(grant, agent)
            text = self.db.execute("SELECT text FROM resources WHERE grant_id=? AND ref=?",
                                   (grant_id, resource_ref)).fetchone()[0]
            self.require_active(grant, agent)
            return {"resource_ref": resource_ref, "version": version,
                    "digest": metadata["digest"], "text": text}

    def blocked(self, account, source_id, exclude=None):
        return self.db.execute("""SELECT 1 FROM executions WHERE account=? AND source_id=?
            AND state IN ('intent','unknown') AND resolved_at IS NULL
            AND (? IS NULL OR request_id != ?) LIMIT 1""",
            (account, source_id, exclude, exclude)).fetchone() is not None

    def request(self, request_id, actor):
        # Deliberately avoid reading snapshot before scope is known.
        row = self.db.execute("""SELECT id,agent,grant_id,account,source_id,idem,input_digest,
            state,reason,action_digest,policy_revision,review_expires_at FROM requests WHERE id=?""", (request_id,)).fetchone()
        if row is None or not (actor == self.owner or actor == self.agent == row["agent"]):
            raise PilotError("not_found", status=404)
        if row["state"] == "pending":
            grant = self.grant(row["grant_id"])
            reason = ("grant_revoked" if grant["revoked"] else
                      "grant_expired" if self.now() >= grant["expires_at"] else
                      "review_expired" if self.now() >= row["review_expires_at"] else None)
            if reason:
                with self.transaction():
                    self.db.execute("UPDATE requests SET state='denied',reason=?,nonce_hash=NULL WHERE id=? AND state='pending'", (reason, request_id))
                return self.request(request_id, actor)
        return row

    def snapshot(self, request_id):
        return json.loads(self.db.execute("SELECT snapshot FROM requests WHERE id=?", (request_id,)).fetchone()[0])

    def projection(self, row, actor):
        receipt = {"request_id": row["id"], "state": row["state"], "reason": row["reason"]}
        if row["state"] == "processing":
            return {"request_id": row["id"], "state": "unknown", "reason": "unresolved_dispatch_intent"}
        if actor != self.owner and row["policy_revision"] != self.policy.revision:
            return receipt
        grant = self.grant(row["grant_id"])
        if actor != self.owner:
            try:
                self.authorize(grant, actor, "list")
            except PilotError:
                return receipt
        if actor == self.owner:
            receipt["snapshot"] = self.snapshot(row["id"])
        if row["state"] == "pending":
            if self.now() >= row["review_expires_at"]:
                return receipt
            snapshot = receipt.get("snapshot") or self.snapshot(row["id"])
            receipt.update(action_digest=row["action_digest"],
                           review_expires_at=row["review_expires_at"],
                           preview=snapshot["prepared_reply"]["preview"])
        result = self.db.execute("SELECT result FROM requests WHERE id=?", (row["id"],)).fetchone()[0]
        if result is not None:
            receipt["result"] = json.loads(result)
        if actor != self.owner and not self.active(grant, actor):
            return {k: receipt[k] for k in ("request_id", "state", "reason")}
        return receipt

    def get_request(self, actor, request_id):
        with self.lock:
            return self.projection(self.request(request_id, actor), actor)

    def propose_reply(self, agent, body):
        with self.lock:
            body = validate_proposal(body)
            if agent != self.agent:
                raise PilotError("forbidden", status=403)
            input_digest = digest(body)
            previous = self.db.execute("SELECT id,input_digest FROM requests WHERE agent=? AND idem=?",
                                       (agent, body["idempotency_key"])).fetchone()
            if previous:
                if previous["input_digest"] != input_digest:
                    raise PilotError("idempotency_conflict", status=409)
                return self.projection(self.request(previous["id"], agent), agent)
            grant = self.grant(body["grant_id"])
            self.require_active(grant, agent)
            if body["reply_to_ref"] != grant["reply_to_ref"]:
                raise PilotError("scope_denied", status=403)
            resources = [json.loads(r[0]) for r in self.db.execute(
                "SELECT metadata FROM resources WHERE grant_id=? ORDER BY ref", (grant["id"],))]
            source = next(r for r in resources if r["resource_ref"] == grant["reply_to_ref"])
            scope = {"reply_to_ref": source["resource_ref"], "recipient": grant["recipient"],
                     "blocked": self.blocked(self.account, source["provider_message_id"]), "phase": "preflight"}
            if scope["blocked"]:
                raise PilotError("source_unresolved", status=409)
            self.authorize(grant, agent, "reply", expected="review", **scope)
            request_id = str(uuid.uuid4())
            prepared = prepare_reply(account=self.account, recipient=grant["recipient"], source=source,
                                     body_text=body["body_text"], request_id=request_id)
            now = self.now()
            snapshot = {"schema_version": 1, "request_id": request_id, "principal": agent,
                        "account_id": self.account, "grant_id": grant["id"],
                        "source_key": {"account_id": self.account, "provider_message_id": source["provider_message_id"]},
                        "context": [{k: r[k] for k in ("resource_ref", "version", "digest")} for r in resources],
                        "prepared_reply": prepared, "policy_revision": self.policy.revision,
                        "prepared_at": now, "review_expires_at": min(now + 300, grant["expires_at"])}
            with self.transaction():
                self.require_active(grant, agent)
                self.db.execute("""INSERT INTO requests(id,agent,grant_id,account,source_id,idem,input_digest,
                    state,reason,action_digest,policy_revision,review_expires_at,snapshot) VALUES(?,?,?,?,?,?,?,'pending',
                    'requires_approval',?,?,?,?)""", (request_id, agent, grant["id"], self.account,
                    source["provider_message_id"], body["idempotency_key"], input_digest,
                    digest(snapshot), self.policy.revision, snapshot["review_expires_at"], canonical(snapshot)))
            return self.projection(self.request(request_id, agent), agent)

    def review(self, human, request_id):
        with self.lock:
            self.human(human)
            row = self.request(request_id, human)
            grant = self.grant(row["grant_id"])
            self.require_active(grant, self.agent)
            if row["state"] != "pending" or self.now() >= row["review_expires_at"]:
                raise PilotError("not_reviewable", status=409)
            nonce = secrets.token_urlsafe(32)
            with self.transaction():
                self.require_active(grant, self.agent)
                if self.now() >= row["review_expires_at"]:
                    raise PilotError("review_expired", status=409)
                self.db.execute("UPDATE requests SET nonce_hash=? WHERE id=?", (digest(nonce), request_id))
            return {"request_id": request_id, "action_digest": row["action_digest"], "nonce": nonce,
                    "review_expires_at": row["review_expires_at"], "snapshot": self.snapshot(request_id)}

    def decide_review(self, human, request_id, action_digest, nonce, decision):
        with self.lock:
            self.human(human)
            if decision not in ("approve", "reject") or not isinstance(nonce, str) or not isinstance(action_digest, str):
                raise PilotError("invalid_decision")
            row = self.request(request_id, human)
            if row["state"] != "pending":
                return self.projection(row, human)
            grant = self.grant(row["grant_id"])
            snapshot = self.snapshot(request_id)
            execution_id = str(uuid.uuid4())
            now = self.now()
            approval = {"human": human, "action_digest": action_digest, "accepted_at": now,
                        "expires_at": min(now + 60, row["review_expires_at"], grant["expires_at"])}
            if decision == "approve":
                self.execute_guard(row, grant, snapshot, approval)
            with self.transaction():
                # BEGIN can wait on another SQLite connection: all deadlines are checked here.
                self.require_active(grant, self.agent)
                if self.now() >= row["review_expires_at"]:
                    raise PilotError("review_expired", status=409)
                nonce_hash = self.db.execute("SELECT nonce_hash FROM requests WHERE id=?", (request_id,)).fetchone()[0]
                if (not nonce_hash or not hmac.compare_digest(nonce_hash, digest(nonce))
                        or not hmac.compare_digest(row["action_digest"], action_digest)
                        or digest(snapshot) != action_digest):
                    raise PilotError("invalid_review", status=409)
                self.db.execute("UPDATE requests SET nonce_hash=NULL WHERE id=?", (request_id,))
                self.db.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?)", (request_id, human,
                                action_digest, decision, approval["accepted_at"], approval["expires_at"]))
                if decision == "reject":
                    self.db.execute("UPDATE requests SET state='rejected',reason='human_rejected' WHERE id=?", (request_id,))
                else:
                    if (self.now() >= approval["expires_at"] or self.blocked(self.account, row["source_id"])
                            or self.policy.revision != snapshot["policy_revision"]):
                        raise PilotError("dispatch_denied", status=403)
                    self.db.execute("INSERT INTO executions(id,request_id,account,source_id,state) VALUES(?,?,?,?,'intent')",
                                    (execution_id, request_id, self.account, row["source_id"]))
                    self.db.execute("UPDATE requests SET state='processing',reason='dispatch_intent' WHERE id=?", (request_id,))
            if decision == "reject":
                return self.projection(self.request(request_id, human), human)
            try:
                # Intent COMMIT can wait too. Recheck immediately before the one provider IO.
                self.execute_guard(row, grant, snapshot, approval, exclude=request_id)
            except PilotError as exc:
                self.finish(request_id, execution_id, "denied", exc.reason, {})
                return self.projection(self.request(request_id, human), human)
            try:
                outcome = self.provider.send_prepared(deepcopy(snapshot["prepared_reply"]), execution_id)
                if (not isinstance(outcome, dict) or outcome.get("state") not in {"accepted", "failed", "unknown"}
                        or not isinstance(outcome.get("reason"), str) or not isinstance(outcome.get("result"), dict)):
                    outcome = {"state": "unknown", "reason": "provider_invalid_result", "result": {}}
            except Exception:
                outcome = {"state": "unknown", "reason": "provider_outcome_unknown", "result": {}}
            try:
                self.finish(request_id, execution_id, outcome["state"], outcome["reason"], outcome["result"])
            except PilotError:
                return {"request_id": request_id, "state": "unknown", "reason": "result_not_persisted"}
            return self.projection(self.request(request_id, human), human)

    def execute_guard(self, row, grant, snapshot, approval, exclude=None):
        if self.blocked(row["account"], row["source_id"], exclude):
            raise PilotError("source_unresolved", status=409)
        self.authorize(grant, self.agent, "reply", phase="execute", blocked=False,
                       reply_to_ref=grant["reply_to_ref"], recipient=grant["recipient"],
                       snapshot=snapshot, approval=approval, action_digest=row["action_digest"])
        now = self.now()
        if (now >= approval["expires_at"] or now >= row["review_expires_at"]
                or now < approval["accepted_at"] or self.policy.revision != snapshot["policy_revision"]):
            raise PilotError("consent_expired", status=403)

    def finish(self, request_id, execution_id, state, reason, result):
        try:
            with self.transaction():
                self.db.execute("UPDATE requests SET state=?,reason=?,result=? WHERE id=?",
                                (state, reason, canonical(result), request_id))
                self.db.execute("UPDATE executions SET state=?,result=? WHERE id=?",
                                (state, canonical(result), execution_id))
        except sqlite3.Error as exc:
            # Keep the committed intent; restart will classify unknown and retain its source barrier.
            self.suspended = True
            raise PilotError("storage_unavailable", status=503) from exc

    def resolve_unknown(self, human, request_id, acknowledge_duplicate_risk):
        with self.lock:
            self.human(human)
            if acknowledge_duplicate_risk is not True:
                raise PilotError("duplicate_risk_acknowledgement_required")
            row = self.request(request_id, human)
            if row["state"] != "unknown":
                raise PilotError("not_unknown", status=409)
            with self.transaction():
                self.db.execute("INSERT OR IGNORE INTO resolutions VALUES(?,?,?)", (request_id, human, self.now()))
                self.db.execute("UPDATE executions SET resolved_at=COALESCE(resolved_at,?) WHERE request_id=? AND state='unknown'",
                                (self.now(), request_id))
            return {"request_id": request_id, "state": "unknown", "reason": row["reason"], "barrier_resolved": True}
