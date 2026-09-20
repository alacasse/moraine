"""Small, bounded local human channel authenticated by Linux peer credentials."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import socketserver
import struct
import time

from .models import PilotError

MAX_BODY = 1024 * 1024


def strict_json(raw: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("non-finite number")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


OPERATIONS = {
    "create_grant": {"body"},
    "revoke_grant": {"grant_id"},
    "get_request": {"request_id"},
    "review": {"request_id"},
    "decide_review": {"request_id", "action_digest", "nonce", "decision"},
    "resolve_unknown": {"request_id", "acknowledge_duplicate_risk"},
}


def dispatch(broker, owner: str, payload):
    if not isinstance(payload, dict):
        raise PilotError("invalid_human_request")
    operation = payload.get("operation")
    if not isinstance(operation, str) or operation not in OPERATIONS:
        raise PilotError("invalid_human_request")
    if set(payload) != OPERATIONS[operation] | {"operation"}:
        raise PilotError("invalid_human_request")
    args = {key: payload[key] for key in OPERATIONS[operation]}
    for key, value in args.items():
        if key == "body":
            if not isinstance(value, dict):
                raise PilotError("invalid_human_request")
        elif key == "acknowledge_duplicate_risk":
            if type(value) is not bool:
                raise PilotError("invalid_human_request")
        elif not isinstance(value, str) or not value or len(value) > 128:
            raise PilotError("invalid_human_request")
    if operation == "decide_review" and args["decision"] not in {"approve", "reject"}:
        raise PilotError("invalid_human_request")
    return getattr(broker, operation)(owner, **args)


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(5)
        server = self.server
        try:
            _, uid, _ = struct.unpack("3i", self.connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != server.allowed_uid:
                self.respond({"error": "unauthorized"})
                return
            deadline = time.monotonic() + 5
            raw = bytearray()
            while b"\n" not in raw and len(raw) <= MAX_BODY:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise socket.timeout()
                self.connection.settimeout(remaining)
                chunk = self.connection.recv(min(16384, MAX_BODY + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
            if len(raw) > MAX_BODY or not raw.endswith(b"\n") or raw.count(b"\n") != 1:
                self.respond({"error": "invalid_human_request"})
                return
            result = dispatch(server.broker, server.owner, strict_json(raw))
            self.respond({"result": result})
        except PilotError as exc:
            self.respond({"error": exc.reason})
        except (ValueError, TypeError, UnicodeError, socket.timeout):
            self.respond({"error": "invalid_human_request"})
        except Exception:
            self.respond({"error": "internal_error"})

    def respond(self, result):
        try:
            self.wfile.write(json.dumps(result, ensure_ascii=True, allow_nan=False).encode() + b"\n")
        except (OSError, ValueError):
            pass


class HumanServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = False
    block_on_close = True

    def __init__(self, path: Path, broker, *, allowed_uid: int, owner: str = "human:owner"):
        if not hasattr(socket, "SO_PEERCRED") or allowed_uid < 0:
            raise ValueError("Linux peer credentials and a valid human UID are required")
        self.broker = broker
        self.owner = owner
        self.allowed_uid = allowed_uid
        self.path = Path(path)
        # Do not remove an existing endpoint: it might belong to a live service.
        super().__init__(str(self.path), _Handler, bind_and_activate=False)
        try:
            self.server_bind()
            os.chmod(self.path, 0o600)
            if allowed_uid != os.geteuid():
                os.chown(self.path, allowed_uid, -1)
            self.server_activate()
        except BaseException:
            self.socket.close()
            # Only unlink the inode created by this instance.
            if hasattr(self, "_bound_inode"):
                self._unlink_owned()
            raise

    def server_bind(self):
        super().server_bind()
        self._bound_inode = self.path.lstat().st_ino

    def _unlink_owned(self):
        try:
            if self.path.lstat().st_ino == self._bound_inode:
                self.path.unlink()
        except FileNotFoundError:
            pass

    def server_close(self):
        super().server_close()
        if hasattr(self, "_bound_inode"):
            self._unlink_owned()
