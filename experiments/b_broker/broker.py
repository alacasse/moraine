"""Experimental credential-holding broker: strict HTTP, SQLite lifecycle, real Rego."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import sqlite3
import threading
import time
from urllib.parse import quote, urlsplit
import uuid
import httpx
from opa import OPA, PolicyFailure

MAX_INT = 2**53 - 1


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class BadRequest(Exception):
    pass


def exact(value, fields):
    if type(value) is not dict or set(value) != set(fields.split()):
        raise BadRequest()


def string(value, limit=1000, empty=False):
    if type(value) is not str or len(value) > limit or (not empty and not value):
        raise BadRequest()
    # JSON lone surrogates cannot be represented in the canonical UTF-8 snapshot.
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError as error:
        raise BadRequest() from error


def integer(value, minimum=1):
    if type(value) is not int or not minimum <= value <= MAX_INT:
        raise BadRequest()


def strings(value, limit=100):
    if type(value) is not list or len(value) > limit:
        raise BadRequest()
    for item in value:
        string(item)


def validate_grant(body):
    exact(body, "agent account expires_at recipients document_ids merchants currency auto_limit_minor hard_limit_minor")
    for field in ("agent", "account", "currency"):
        string(body[field])
    for field in ("recipients", "document_ids", "merchants"):
        strings(body[field])
    integer(body["expires_at"])
    integer(body["auto_limit_minor"], 0)
    integer(body["hard_limit_minor"])
    if (body["expires_at"] <= time.time() or body["auto_limit_minor"] > body["hard_limit_minor"]
            or body["agent"] != "agent:alice" or body["account"] != "alice"):
        raise BadRequest()


def validate_action(action):
    if type(action) is not dict or type(action.get("type")) is not str:
        raise BadRequest()
    kind = action["type"]
    if kind == "email.send":
        exact(action, "type account to cc bcc subject body attachments")
        for field in ("to", "cc", "bcc"):
            strings(action[field])
        if sum(len(action[field]) for field in ("to", "cc", "bcc")) > 100:
            raise BadRequest()
        string(action["subject"], 16000, True)
        string(action["body"], 200000, True)
        if type(action["attachments"]) is not list or len(action["attachments"]) > 20:
            raise BadRequest()
        for attachment in action["attachments"]:
            exact(attachment, "id version")
            string(attachment["id"])
            integer(attachment["version"])
    elif kind == "order.create":
        exact(action, "type account merchant sku quantity amount_minor currency shipping_address_id recurring")
        for field in ("merchant", "sku", "currency", "shipping_address_id"):
            string(action[field])
        integer(action["quantity"])
        integer(action["amount_minor"])
        if type(action["recurring"]) is not bool:
            raise BadRequest()
    elif kind == "document.read":
        exact(action, "type account document_id")
        string(action["document_id"])
    else:
        raise BadRequest()
    string(action["account"])


def json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BadRequest()
        result[key] = value
    return result


def no_constant(_):
    raise BadRequest()


class ProviderFailure(Exception):
    def __init__(self, reason):
        self.reason = reason


class Broker:
    def __init__(self, args):
        self.lock = threading.RLock()
        self.directory = Path(args.state_dir)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.filelock = (self.directory / "broker.lock").open("a+")
        fcntl.flock(self.filelock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.tokens = [(args.agent_token, "agent:alice"), (args.other_agent_token, "agent:bob"),
                       (args.human_token, "human:alice")]
        tokens = [token for token, _ in self.tokens] + [args.provider_token]
        if any(not token or not token.isascii() for token in tokens) or len(set(tokens)) != len(tokens):
            raise ValueError("Fixture credentials must be nonempty, ASCII and distinct")
        origin = urlsplit(args.provider_url)
        if (origin.scheme != "http" or origin.hostname not in {"127.0.0.1", "localhost", "::1"}
                or origin.username or origin.password or origin.query or origin.fragment
                or origin.path not in ("", "/")):
            raise ValueError("Provider must be a loopback HTTP origin")
        self.db = sqlite3.connect(self.directory / "broker.sqlite3", timeout=5,
                                  check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA busy_timeout=5000")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            raise ValueError("Unsupported storage version")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS grants (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, scope TEXT NOT NULL,
                created_at REAL NOT NULL, revoked_at REAL
            );
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY, agent TEXT NOT NULL, account TEXT NOT NULL,
                grant_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                input_digest TEXT NOT NULL, action TEXT NOT NULL,
                snapshot TEXT, action_digest TEXT, policy_revision TEXT NOT NULL,
                created_at REAL NOT NULL, review_expires_at REAL,
                phase TEXT NOT NULL, state TEXT NOT NULL, reason TEXT NOT NULL, result TEXT,
                UNIQUE(agent, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS approvals (
                request_id TEXT PRIMARY KEY REFERENCES requests(id), human TEXT NOT NULL,
                action_digest TEXT NOT NULL, accepted_at REAL NOT NULL, expires_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE REFERENCES requests(id),
                payload_digest TEXT NOT NULL, intent_at REAL NOT NULL,
                state TEXT NOT NULL, result TEXT
            );
            PRAGMA user_version=1;
        """)
        with self.transaction():
            self.db.execute("UPDATE requests SET phase='terminal',state='failed',reason='preparation_interrupted' WHERE phase='preparing'")
            self.db.execute("UPDATE requests SET phase='terminal',state='unknown',reason='execution_interrupted' WHERE phase='executing'")
            self.db.execute("UPDATE executions SET state='unknown' WHERE state='executing'")
        self.provider = httpx.Client(base_url=args.provider_url.rstrip("/"), trust_env=False,
                                     timeout=5, follow_redirects=False,
                                     transport=httpx.HTTPTransport(retries=0),
                                     headers={"Authorization": "Bearer " + args.provider_token})
        policy = os.environ.get("B_BROKER_TEST_POLICY")
        self.opa = OPA(Path(policy) if policy else None)
        try:
            self.opa.wait_ready()
        except Exception:
            self.opa.close()
            self.provider.close()
            self.db.close()
            self.filelock.close()
            raise

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def close(self):
        self.opa.close()
        self.provider.close()
        self.db.close()
        self.filelock.close()

    def actor(self, header):
        for token, actor in self.tokens:
            if hmac.compare_digest(header.encode(), ("Bearer " + token).encode()):
                return actor
        return None

    def row(self, rid):
        return self.db.execute("SELECT * FROM requests WHERE id=?", (rid,)).fetchone()

    def grant(self, gid):
        row = self.db.execute("SELECT * FROM grants WHERE id=?", (gid,)).fetchone()
        if not row:
            return None
        return {**json.loads(row["scope"]), "id": gid, "owner": row["owner"],
                "revoked": row["revoked_at"] is not None}

    def visible(self, row, actor):
        return row is not None and (row["agent"] == actor or actor == "human:alice" and row["account"] == "alice")

    def public(self, row):
        result = {"request_id": row["id"], "state": row["state"], "reason": row["reason"]}
        if row["snapshot"]:
            result["action_digest"] = row["action_digest"]
            result["snapshot"] = json.loads(row["snapshot"])
            result["review_expires_at"] = row["review_expires_at"]
        if row["result"]:
            result["result"] = json.loads(row["result"])
        return result

    def finish(self, rid, state, reason, result=None):
        with self.transaction():
            self.db.execute("UPDATE requests SET phase=?,state=?,reason=?,result=? WHERE id=?",
                            ("pending" if state == "pending" else "terminal", state, reason,
                             canonical(result) if result is not None else None, rid))
            self.db.execute("UPDATE executions SET state=?,result=? WHERE request_id=?",
                            (state, canonical(result) if result is not None else None, rid))
        return 200, self.public(self.row(rid))

    def facts(self, row, phase, action, snapshot=None, approval=None):
        return {"phase": phase, "now": time.time(),
                "subject": {"principal": row["agent"], "account": row["account"]},
                "grant": self.grant(row["grant_id"]), "action": action,
                "snapshot": ({**snapshot, "action_digest": row["action_digest"]} if snapshot else None),
                "policy_revision": self.opa.revision, "approval": approval}

    def decide(self, row, phase, action, snapshot=None, approval=None):
        return self.opa.decide(self.facts(row, phase, action, snapshot, approval))["decision"]

    def document(self, did):
        try:
            response = self.provider.get("/documents/" + quote(did, safe=""))
            if response.status_code != 200:
                raise ProviderFailure("provider_rejected")
            result = response.json()
            if (not isinstance(result, dict) or set(result) != {"id", "version", "content", "classification"}
                    or result["id"] != did or type(result["version"]) is not int
                    or result["version"] < 1 or type(result["content"]) is not str
                    or type(result["classification"]) is not str):
                raise ProviderFailure("provider_invalid_document")
            return result
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderFailure("provider_unavailable") from error

    def create_grant(self, body):
        validate_grant(body)
        gid = str(uuid.uuid4())
        with self.transaction():
            self.db.execute("INSERT INTO grants VALUES (?, 'human:alice', ?, ?, NULL)",
                            (gid, canonical(body), time.time()))
        return 201, {"grant_id": gid}

    def revoke(self, gid, body):
        exact(body, "")
        if not self.grant(gid):
            return 404, {"error": "not_found"}
        with self.transaction():
            self.db.execute("UPDATE grants SET revoked_at=COALESCE(revoked_at,?) WHERE id=?", (time.time(), gid))
            self.db.execute("UPDATE requests SET phase='terminal', state='denied', reason='grant_revoked' WHERE grant_id=? AND phase='pending'", (gid,))
        return 200, {"grant_id": gid, "state": "revoked"}

    def submit(self, actor, body):
        exact(body, "grant_id idempotency_key action")
        string(body["grant_id"])
        string(body["idempotency_key"], 128)
        validate_action(body["action"])
        input_hash = digest({"grant_id": body["grant_id"], "action": body["action"]})
        previous = self.db.execute("SELECT * FROM requests WHERE agent=? AND idempotency_key=?",
                                   (actor, body["idempotency_key"])).fetchone()
        if previous:
            if previous["input_digest"] != input_hash:
                return 409, {"error": "idempotency_conflict"}
            return 200, self.public(previous)
        rid = str(uuid.uuid4())
        with self.transaction():
            self.db.execute("""INSERT INTO requests
                (id,agent,account,grant_id,idempotency_key,input_digest,action,policy_revision,created_at,phase,state,reason)
                VALUES (?,?,?,?,?,?,?,?,?,'preparing','failed','preparation_interrupted')""",
                (rid, actor, actor.split(":", 1)[1], body["grant_id"], body["idempotency_key"],
                 input_hash, canonical(body["action"]), self.opa.revision, time.time()))
        row = self.row(rid)
        action = json.loads(row["action"])
        try:
            decision = self.decide(row, "preflight", action)
            if decision == "deny":
                return self.finish(rid, "denied", "scope_denied")
            if action["type"] == "email.send":
                prepared = []
                for attachment in action["attachments"]:
                    if self.decide(row, "preflight", action) == "deny":
                        return self.finish(rid, "denied", "scope_denied")
                    if time.time() >= self.grant(row["grant_id"])["expires_at"]:
                        return self.finish(rid, "denied", "grant_expired")
                    document = self.document(attachment["id"])
                    if document["version"] != attachment["version"]:
                        return self.finish(rid, "denied", "attachment_version_mismatch")
                    prepared.append({key: document[key] for key in ("id", "version", "content")})
                action["attachments"] = prepared
            prepared_at = time.time()
            grant = self.grant(row["grant_id"])
            snapshot = {"version": 1, "request_id": rid, "principal": actor, "account": row["account"],
                        "grant_id": row["grant_id"], "prepared_action": action,
                        "policy_revision": self.opa.revision, "prepared_at": prepared_at,
                        "review_expires_at": min(grant["expires_at"], prepared_at + 300)}
            with self.transaction():
                self.db.execute("UPDATE requests SET snapshot=?,action_digest=?,review_expires_at=? WHERE id=?",
                                (canonical(snapshot), digest(snapshot), snapshot["review_expires_at"], rid))
            if decision == "review":
                # No pending snapshot survives an expiry during attachment preparation.
                if time.time() >= snapshot["review_expires_at"]:
                    return self.finish(rid, "denied", "review_expired")
                return self.finish(rid, "pending", "requires_approval")
            return self.execute(self.row(rid))
        except PolicyFailure as error:
            return self.finish(rid, "failed", error.reason)
        except ProviderFailure as error:
            return self.finish(rid, "failed", error.reason)

    def approve(self, rid, body):
        exact(body, "action_digest")
        string(body["action_digest"], 64)
        row = self.row(rid)
        if not self.visible(row, "human:alice"):
            return 404, {"error": "not_found"}
        if row["state"] != "pending":
            return 409, self.public(row)
        if not hmac.compare_digest(body["action_digest"].encode(), row["action_digest"].encode()):
            return 409, {"error": "digest_mismatch"}
        if row["policy_revision"] != self.opa.revision:
            return self.finish(rid, "denied", "policy_changed")
        now = time.time()
        approval = {"human": "human:alice", "action_digest": row["action_digest"],
                    "accepted_at": now, "expires_at": min(now + 60, row["review_expires_at"])}
        try:
            return self.execute(row, approval)
        except PolicyFailure as error:
            return self.finish(rid, "failed", error.reason)

    def pause_test(self, phase):
        # Trusted process-launch configuration only, never reachable through HTTP.
        if os.environ.get("B_BROKER_TEST_PAUSE") == phase:
            (self.directory / "test-paused").write_text(phase)
            os.kill(os.getpid(), signal.SIGSTOP)

    def execute(self, row, approval=None):
        rid = row["id"]
        snapshot = json.loads(row["snapshot"])
        if digest(snapshot) != row["action_digest"]:
            return self.finish(rid, "failed", "snapshot_corrupt")
        action = snapshot["prepared_action"]
        if self.decide(row, "execute", action, snapshot, approval) != "allow":
            return self.finish(rid, "denied", "scope_denied")
        # Fresh local time guard after the remote policy check, immediately before claim.
        now = time.time()
        if now >= snapshot["review_expires_at"] or (approval and now >= approval["expires_at"]):
            return self.finish(rid, "denied", "review_expired")
        execution_id = str(uuid.uuid4())
        with self.transaction():
            if approval:
                self.db.execute("INSERT INTO approvals VALUES (?, ?, ?, ?, ?)",
                                (rid, approval["human"], approval["action_digest"],
                                 approval["accepted_at"], approval["expires_at"]))
            self.db.execute("INSERT INTO executions VALUES (?, ?, ?, ?, 'executing', NULL)",
                            (execution_id, rid, digest(action), now))
            self.db.execute("UPDATE requests SET phase='executing',state='unknown',reason='execution_interrupted' WHERE id=?", (rid,))
        self.pause_test("after_intent")
        # A durable claim may have waited for SQLite, fsync, or process scheduling.
        # Recheck time after that wait, at the last local boundary before provider IO.
        # This cannot guarantee when a remote provider will accept an in-flight call.
        grant = self.grant(row["grant_id"])
        now = time.time()
        if (now >= grant["expires_at"] or now >= snapshot["review_expires_at"]
                or approval and (now >= approval["expires_at"]
                                 or now >= approval["accepted_at"] + 60)):
            return self.finish(rid, "denied", "authorization_expired")
        try:
            if action["type"] == "document.read":
                result = self.document(action["document_id"])
            else:
                response = self.provider.post("/effects", json={"execution_id": execution_id, "action": action})
                if response.status_code == 503:
                    # Definite rejection is a property of THIS synthetic provider.
                    return self.finish(rid, "failed", "provider_rejected")
                if response.status_code not in (200, 201):
                    return self.finish(rid, "unknown", "provider_outcome_unknown")
                result = response.json()
                if (not isinstance(result, dict) or result.get("execution_id") != execution_id
                        or type(result.get("effect_id")) is not str or not result["effect_id"]):
                    return self.finish(rid, "unknown", "provider_outcome_unknown")
                result = {"execution_id": execution_id, "effect_id": result["effect_id"]}
            self.pause_test("after_effect")
            return self.finish(rid, "executed", "completed", result)
        except (httpx.HTTPError, ValueError, ProviderFailure):
            return self.finish(rid, "unknown", "provider_outcome_unknown")
        except sqlite3.Error:
            # Durable intent remains executing; restart recovers it as unknown.
            return 200, {"request_id": rid, "state": "unknown", "reason": "local_outcome_unknown"}

    def route(self, method, path, actor, body):
        parts = path.strip("/").split("/")
        if method == "POST" and (path == "/grants" or len(parts) == 3 and parts[0] == "grants" and parts[2] == "revoke"):
            if actor != "human:alice":
                return 403, {"error": "human_required"}
            return self.create_grant(body) if path == "/grants" else self.revoke(parts[1], body)
        if method == "POST" and path == "/requests":
            if not actor.startswith("agent:"):
                return 403, {"error": "agent_required"}
            return self.submit(actor, body)
        if method == "GET" and len(parts) == 2 and parts[0] == "requests":
            row = self.row(parts[1])
            return (200, self.public(row)) if self.visible(row, actor) else (404, {"error": "not_found"})
        if method == "POST" and len(parts) == 3 and parts[0] == "requests" and parts[2] == "approve":
            if actor != "human:alice":
                return 403, {"error": "human_required"}
            return self.approve(parts[1], body)
        return 404, {"error": "not_found"}


class Server(ThreadingHTTPServer):
    daemon_threads = False

    def __init__(self, port, broker):
        self.broker = broker
        super().__init__(("127.0.0.1", port), Handler)


class Handler(BaseHTTPRequestHandler):
    server: Server

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_):
        pass

    def reply(self, status, body):
        encoded = canonical(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        try:
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def handle_request(self):
        broker = self.server.broker
        if self.command == "GET" and self.path == "/health":
            healthy = broker.opa.healthy()
            self.reply(200 if healthy else 503, {"status": "ok" if healthy else "unavailable"})
            return
        headers = self.headers.get_all("Authorization", [])
        actor = broker.actor(headers[0]) if len(headers) == 1 else None
        if actor is None:
            self.reply(401, {"error": "invalid_credential"})
            return
        try:
            body = None
            if self.command == "POST":
                lengths = self.headers.get_all("Content-Length", [])
                if len(lengths) != 1 or self.headers.get("Transfer-Encoding") is not None:
                    raise BadRequest()
                if not lengths[0].isascii() or not lengths[0].isdigit():
                    raise BadRequest()
                size = int(lengths[0])
                if not 0 < size <= 256 * 1024:
                    raise BadRequest()
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise BadRequest()
                body = json.loads(raw.decode("utf-8"), object_pairs_hook=json_object, parse_constant=no_constant)
                if type(body) is not dict:
                    raise BadRequest()
            with broker.lock:
                status, result = broker.route(self.command, self.path, actor, body)
        except (BadRequest, ValueError, UnicodeError, RecursionError):
            status, result = 400, {"error": "invalid_request"}
        except sqlite3.Error:
            status, result = 503, {"error": "storage_unavailable"}
        self.reply(status, result)

    do_GET = handle_request
    do_POST = handle_request


def main():
    parser = argparse.ArgumentParser()
    for field in ("provider-url", "provider-token", "agent-token", "other-agent-token", "human-token"):
        parser.add_argument("--" + field, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    args = parser.parse_args()
    broker = Broker(args)
    server = None
    try:
        server = Server(args.port, broker)
        def stop(_signal, _frame):
            threading.Thread(target=server.shutdown, daemon=True).start()
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        server.serve_forever(poll_interval=0.1)
    finally:
        if server is not None:
            server.server_close()
        broker.close()


if __name__ == "__main__":
    try:
        main()
    except (PolicyFailure, BlockingIOError, ValueError) as error:
        raise SystemExit(f"Broker startup failed: {type(error).__name__}")
