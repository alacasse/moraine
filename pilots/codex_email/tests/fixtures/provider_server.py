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
from copy import deepcopy


def mailbox():
    # Owned by the provider. The access launcher passes IDs only to Moraine.
    return {mid: {"provider_message_id": mid, "title": title, "text": text,
                  "from_address": "contractor@example.test", "reply_address": "contractor@example.test",
                  "message_id": f"<{mid}@example.test>", "thread_id": "works"}
            for mid, title, text in [
                ("upstream-1", "Travaux : rendez-vous", "La visite pour les travaux est prévue mardi à 10 h."),
                ("upstream-2", "Travaux : préparation", "Merci de dégager le garage avant la visite. Budget fictif : 240 euros."),
                ("upstream-private", "Message exclu", "TEMOIN-HORS-PERIMETRE : information privée fictive.")]}


class ProviderServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, directory, token="synthetic-provider-token", port=0):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.token = token
        self.mode = "normal"
        self.messages = mailbox()
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
        if self.path == "/messages":
            return self.fetch_messages()
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

    def fetch_messages(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                raise ValueError()
            value = json.loads(self.rfile.read(size))
            if type(value) is not dict or set(value) != {"message_ids"}:
                raise ValueError()
            ids = value["message_ids"]
            if type(ids) is not list or not 1 <= len(ids) <= 5 or any(type(mid) is not str for mid in ids):
                raise ValueError()
            with self.server.guard:
                mode, self.server.mode = self.server.mode, "normal"
                messages = [deepcopy(self.server.messages[mid]) for mid in ids]
                hashes = {m["provider_message_id"]: hashlib.sha256(json.dumps(
                    m, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                    allow_nan=False).encode()).hexdigest() for m in messages}
                self.server.record("reads", {"message_ids": ids, "source_digests": hashes, "mode": mode})
            if mode == "slow_fetch":
                time.sleep(2)
            if mode == "disconnect_fetch":
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                self.close_connection = True
                return
            if mode == "invalid_fetch":
                messages[0]["text"] = {"untrusted": "invalid text"}
            if mode == "extra_fetch":
                messages.append(deepcopy(self.server.messages["upstream-private"]))
            if mode == "duplicate_fetch":
                messages[-1] = deepcopy(messages[0])
            if mode == "missing_fetch":
                messages.pop()
            if mode == "oversized_fetch":
                messages[0]["text"] = "x" * 262145
            self.reply(200, {"messages": messages})
        except (ValueError, TypeError, KeyError):
            self.reply(400, {"error": "invalid_selection"})
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    parser = argparse.ArgumentParser(description="Synthetic provider only; no real mail")
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--initial-mode", default="normal",
                        choices=["normal", "reject_before", "accept_then_disconnect", "malformed_success",
                                 "slow_fetch", "disconnect_fetch", "invalid_fetch", "extra_fetch",
                                 "duplicate_fetch", "missing_fetch", "oversized_fetch"])
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
