"""Independent oracle: log every attempt and effect, deliberately no deduplication."""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import threading
import time
import uuid


class ProviderServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, directory, token="synthetic-provider-token", port=0):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.token = token
        self.mode = "normal"
        self.guard = threading.Lock()
        super().__init__(("127.0.0.1", port), Handler)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_port}"

    def record(self, kind, value):
        with (self.directory / f"{kind}.jsonl").open("a") as f:
            f.write(json.dumps({"at": time.time(), **value}, ensure_ascii=True) + "\n")
            f.flush()

    def records(self, kind):
        path = self.directory / f"{kind}.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(3)

    def reply(self, status, value):
        raw = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + self.server.token):
            self.reply(401, {"error": "unauthorized"})
            return
        if self.path != "/send":
            self.reply(404, {"error": "not_found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 262144:
                raise ValueError()
            value = json.loads(self.rfile.read(size))
            if set(value) != {"execution_id", "mime_b64"} or not isinstance(value["execution_id"], str):
                raise ValueError()
            raw = base64.b64decode(value["mime_b64"], validate=True)
        except (ValueError, TypeError):
            self.reply(400, {"error": "invalid_request"})
            return
        with self.server.guard:
            mode, self.server.mode = self.server.mode, "normal"
            record = {**value, "sha256": hashlib.sha256(raw).hexdigest()}
            self.server.record("attempts", record)
            if mode == "reject_before":
                self.reply(422, {"error": "synthetic_rejected_before_effect"})
                return
            receipt = {"execution_id": value["execution_id"], "message_id": str(uuid.uuid4())}
            self.server.record("effects", {**record, **receipt})
        if mode == "accept_then_disconnect":
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            self.close_connection = True
            return
        if mode == "malformed_success":
            self.reply(200, {"not_a_receipt": True})
            return
        self.reply(200, receipt)


def main():
    parser = argparse.ArgumentParser(description="Synthetic provider only; no real mail")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--initial-mode", default="normal",
                        choices=["normal", "reject_before", "accept_then_disconnect", "malformed_success"])
    args = parser.parse_args()
    server = ProviderServer(args.directory, args.token_file.read_text().strip(), args.port)
    server.mode = args.initial_mode
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
