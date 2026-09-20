"""Synthetic downstream provider. Never use its fixture authentication in production."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class Provider(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int, state_dir: Path, token: str):
        self.token = token
        state_dir.mkdir(parents=True, exist_ok=True)
        self.database = state_dir / "provider.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS effects (
                    execution_id TEXT PRIMARY KEY, action TEXT NOT NULL,
                    effect_id TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS reads (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, document_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, version INTEGER NOT NULL,
                    content TEXT NOT NULL, classification TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS control (id INTEGER PRIMARY KEY, mode TEXT NOT NULL);
                INSERT OR IGNORE INTO control VALUES (1, 'normal');
                INSERT OR IGNORE INTO documents VALUES
                    ('public-note', 1, 'Public fixture note', 'public'),
                    ('tax-return', 1, 'PRIVATE SYNTHETIC TAX DATA', 'private');
            """)
        super().__init__(("127.0.0.1", port), Handler)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        return db


class Handler(BaseHTTPRequestHandler):
    server: Provider

    def log_message(self, *_: object) -> None:
        pass

    def reply(self, status: int, payload: object) -> None:
        data = canonical(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def authenticated(self) -> bool:
        supplied = self.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied, "Bearer " + self.server.token):
            self.reply(401, {"error": "invalid_provider_credential"})
            return False
        return True

    def do_GET(self) -> None:
        if self.path == "/health":
            self.reply(200, {"status": "ok", "kind": "synthetic-provider"})
            return
        if not self.authenticated():
            return
        status = 200
        with self.server.connect() as db:
            if self.path == "/effects":
                rows = db.execute("SELECT * FROM effects ORDER BY rowid").fetchall()
                payload = {"effects": [
                    {**dict(row), "action": json.loads(row["action"])} for row in rows
                ]}
            elif self.path == "/reads":
                payload = {"reads": [dict(row) for row in db.execute("SELECT * FROM reads")]}
            elif self.path.startswith("/documents/"):
                doc_id = self.path.removeprefix("/documents/")
                db.execute("INSERT INTO reads(document_id) VALUES (?)", (doc_id,))
                row = db.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
                status, payload = (200, dict(row)) if row else (404, {"error": "not_found"})
            else:
                status, payload = 404, {"error": "not_found"}
        self.reply(status, payload)

    def do_POST(self) -> None:
        if not self.authenticated():
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1024 * 1024:
                raise ValueError("bad body length")
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError("body must be object")
        except (ValueError, TypeError):
            self.reply(400, {"error": "invalid_json"})
            return
        if self.path == "/control":
            mode = body.get("mode", "normal")
            if not isinstance(mode, str) or mode not in {"normal", "reject_before", "accept_then_disconnect"}:
                self.reply(400, {"error": "invalid_mode"})
                return
            doc = body.get("document")
            if "document" in body and (
                not isinstance(doc, dict) or doc.get("id") != "public-note"
                or type(doc.get("version")) is not int
                or not isinstance(doc.get("content"), str)
            ):
                self.reply(400, {"error": "invalid_document"})
                return
            with self.server.connect() as db:
                db.execute("UPDATE control SET mode=? WHERE id=1", (mode,))
                if doc is not None:
                    db.execute("UPDATE documents SET version=?, content=? WHERE id=?",
                               (doc["version"], doc["content"], doc["id"]))
            self.reply(200, {"status": "configured"})
            return
        if self.path != "/effects":
            self.reply(404, {"error": "not_found"})
            return
        execution_id, action = body.get("execution_id"), body.get("action")
        if not isinstance(execution_id, str) or not execution_id or not isinstance(action, dict):
            self.reply(400, {"error": "invalid_effect"})
            return
        serialized = canonical(action)
        effect_id = "effect-" + hashlib.sha256(execution_id.encode()).hexdigest()[:20]
        with self.server.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT * FROM effects WHERE execution_id=?", (execution_id,)).fetchone()
            if previous:
                if previous["action"] != serialized:
                    self.reply(409, {"error": "execution_id_rebound"})
                    return
                self.reply(200, {"effect_id": previous["effect_id"], "execution_id": execution_id})
                return
            mode = db.execute("SELECT mode FROM control WHERE id=1").fetchone()[0]
            db.execute("UPDATE control SET mode='normal' WHERE id=1")
            if mode != "reject_before":
                db.execute("INSERT INTO effects VALUES (?, ?, ?)", (execution_id, serialized, effect_id))
        if mode == "reject_before":
            self.reply(503, {"error": "synthetic_provider_rejection"})
        elif mode == "accept_then_disconnect":
            self.close_connection = True
        else:
            self.reply(201, {"effect_id": effect_id, "execution_id": execution_id})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--provider-token", required=True)
    args = parser.parse_args()
    server = Provider(args.port, args.state_dir, args.provider_token)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
