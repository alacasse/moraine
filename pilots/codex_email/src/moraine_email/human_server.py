"""Small, bounded local human channel authenticated by Linux peer credentials."""
from __future__ import annotations

import errno
import fcntl
import json
import os
from pathlib import Path
import socket
import socketserver
import stat
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
    "list_access_requests": set(),
    "review_access": {"request_id"},
    "decide_access": {"request_id", "scope_digest", "nonce", "decision"},
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
    if operation in {"decide_review", "decide_access"} and args["decision"] not in {"approve", "reject"}:
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

    def __init__(self, path: Path, broker, *, allowed_uid: int,
                 owner: str = "human:owner", socket_gid: int | None = None):
        if not hasattr(socket, "SO_PEERCRED") or allowed_uid < 0:
            raise ValueError("Linux peer credentials and a valid human UID are required")
        if socket_gid is not None and (
            type(socket_gid) is not int or socket_gid not in {os.getegid(), *os.getgroups()}
        ):
            raise ValueError("socket GID must belong to the service")
        self.broker = broker
        self.owner = owner
        self.allowed_uid = allowed_uid
        self.path = Path(os.path.abspath(path))
        self._lock_fd = None
        self._bound_inode = None
        self._validate_parent()
        super().__init__(str(self.path), _Handler, bind_and_activate=False)
        try:
            self._acquire_lock()
            self._recover_stale_socket()
            self.server_bind()
            if socket_gid is not None:
                # Connection permission only; SO_PEERCRED still authorizes the human.
                # The unprivileged service retains ownership, never chowns to the human.
                os.chown(self.path, -1, socket_gid)
            os.chmod(self.path, 0o660 if socket_gid is not None else 0o600)
            self.server_activate()
        except BaseException:
            self.socket.close()
            try:
                self._unlink_owned()
            finally:
                self._release_lock()
            raise

    def _validate_parent(self):
        parent = self.path.parent
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise PermissionError("socket parent must be a service-owned, non-shared directory")
        # Ancestors are administratively trusted, but may not expose the path to
        # replacement via shared writes or symlinks. Sticky /tmp is supported.
        for ancestor in parent.parents:
            info = ancestor.lstat()
            if not stat.S_ISDIR(info.st_mode) or (
                info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX
            ):
                raise PermissionError("unsafe socket path ancestor")

    def _acquire_lock(self):
        lock_path = self.path.with_name(self.path.name + ".lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
                raise PermissionError("socket lock must be a private service-owned regular file")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(fd)
            raise
        self._lock_fd = fd

    def _release_lock(self):
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None
        # Never unlink: another process may already be holding this lock inode.

    @staticmethod
    def _identity(info):
        return info.st_dev, info.st_ino

    def _recover_stale_socket(self):
        try:
            info = self.path.lstat()
        except FileNotFoundError:
            return
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid():
            raise PermissionError("existing endpoint is not a service-owned socket")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            try:
                probe.connect(str(self.path))
            except OSError as exc:
                if exc.errno != errno.ECONNREFUSED:
                    raise
            else:
                raise OSError(errno.EADDRINUSE, "human socket already active", str(self.path))
        # Cooperating services hold the stable lock; do not remove a replacement
        # even if a trusted same-UID process changed the endpoint during the probe.
        if self._identity(self.path.lstat()) != self._identity(info):
            raise OSError(errno.EADDRINUSE, "human socket changed during recovery", str(self.path))
        self.path.unlink()

    def server_bind(self):
        super().server_bind()
        self._bound_inode = self._identity(self.path.lstat())

    def _unlink_owned(self):
        if self._bound_inode is None:
            return
        try:
            if self._identity(self.path.lstat()) == self._bound_inode:
                self.path.unlink()
        except FileNotFoundError:
            pass

    def server_close(self):
        try:
            super().server_close()
            self._unlink_owned()
        finally:
            self._release_lock()
