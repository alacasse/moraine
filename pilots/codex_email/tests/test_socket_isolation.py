"""Real Linux checks under one UID: these are not proof of inter-UID isolation.

SO_PEERCRED rejection uses the real UID against another configured UID.
Explicitly injected error branches are not OS isolation tests.
"""
import errno
import os
import socket
import stat
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from moraine_email.human_cli import call
from moraine_email.human_server import HumanServer


class Broker:
    def __init__(self):
        self.calls = []

    def get_request(self, owner, request_id):
        self.calls.append((owner, request_id))
        return {"request_id": request_id}


def create(path, **kwargs):
    return HumanServer(path, Broker(), allowed_uid=kwargs.pop("allowed_uid", os.geteuid()), **kwargs)


@pytest.mark.parametrize("group", [False, True], ids=["private", "connection-group"])
def test_service_owns_socket_with_configured_mode_and_group(tmp_path, monkeypatch, group):
    path = tmp_path / "human.sock"
    ownership_calls = []
    chown = os.chown

    def record(path, uid, gid):
        ownership_calls.append((uid, gid))
        chown(path, uid, gid)

    monkeypatch.setattr(os, "chown", record)
    server = create(path, allowed_uid=os.geteuid() + 1,
                    socket_gid=os.getegid() if group else None)
    try:
        info = path.stat()
        assert info.st_uid == os.geteuid()
        assert stat.S_IMODE(info.st_mode) == (0o660 if group else 0o600)
        if group:
            assert info.st_gid == os.getegid()
        assert ownership_calls == ([(-1, os.getegid())] if group else [])
    finally:
        server.server_close()


def test_connection_group_does_not_authorize_another_human_uid(tmp_path):
    path = tmp_path / "human.sock"
    server = create(path, allowed_uid=os.geteuid() + 1, socket_gid=os.getegid())
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    try:
        with pytest.raises(ValueError, match="unauthorized"):
            call(path, {"operation": "get_request", "request_id": "q1"})
        assert server.broker.calls == []
    finally:
        server.shutdown()
        worker.join()
        server.server_close()


def test_unavailable_group_rejected_before_socket_creation(tmp_path):
    unavailable = max({os.getegid(), *os.getgroups()}) + 1
    path = tmp_path / "human.sock"
    with pytest.raises(ValueError, match="GID"):
        create(path, socket_gid=unavailable)
    assert not path.exists()
    assert not path.with_suffix(".sock.lock").exists()


@pytest.mark.parametrize("mode", [0o770, 0o707, 0o777])
def test_shared_writable_parent_rejected(tmp_path, mode):
    parent = tmp_path / "runtime"
    parent.mkdir(mode=mode)
    parent.chmod(mode)
    with pytest.raises(PermissionError, match="parent"):
        create(parent / "human.sock")


def test_symlink_parent_and_ancestor_rejected(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "inner").mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    for path in (link / "human.sock", link / "inner" / "human.sock"):
        with pytest.raises(PermissionError):
            create(path)
    assert not (real / "human.sock").exists()
    assert not (real / "inner" / "human.sock").exists()


def test_nonsticky_shared_ancestor_rejected(tmp_path):
    ancestor = tmp_path / "shared"
    ancestor.mkdir()
    ancestor.chmod(0o777)
    private = ancestor / "private"
    private.mkdir(mode=0o700)
    with pytest.raises(PermissionError, match="ancestor"):
        create(private / "human.sock")


@pytest.mark.parametrize("kind", ["symlink", "public", "hardlink"])
def test_unsafe_lock_is_preserved_and_rejected(tmp_path, kind):
    path = tmp_path / "human.sock"
    lock = tmp_path / "human.sock.lock"
    target = tmp_path / "valuable"
    target.write_text("preserve")
    if kind == "symlink":
        lock.symlink_to(target)
    elif kind == "hardlink":
        target.chmod(0o600)
        os.link(target, lock)
    else:
        lock.write_text("preserve")
        lock.chmod(0o644)
    before = lock.lstat()
    with pytest.raises(OSError):
        create(path)
    assert (lock.lstat().st_dev, lock.lstat().st_ino) == (before.st_dev, before.st_ino)
    assert target.read_text() == "preserve"
    assert not path.exists()


def test_lock_inode_persists_across_close_and_restart(tmp_path):
    path = tmp_path / "human.sock"
    first = create(path)
    lock = tmp_path / "human.sock.lock"
    info = lock.stat()
    assert stat.S_IMODE(info.st_mode) == 0o600
    assert info.st_uid == os.geteuid()
    first.server_close()
    assert not path.exists()
    second = create(path)
    try:
        assert (lock.stat().st_dev, lock.stat().st_ino) == (info.st_dev, info.st_ino)
    finally:
        second.server_close()


def test_concurrent_constructors_have_one_owner(tmp_path):
    path = tmp_path / "human.sock"
    barrier = threading.Barrier(2)

    def contender():
        barrier.wait(timeout=3)
        try:
            return create(path)
        except OSError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: contender(), range(2)))
    servers = [result for result in results if isinstance(result, HumanServer)]
    try:
        assert len(servers) == 1
        assert sum(isinstance(result, BlockingIOError) for result in results) == 1
        assert path.exists()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(str(path))
    finally:
        for server in servers:
            server.server_close()


def test_active_endpoint_without_lock_is_preserved(tmp_path):
    path = tmp_path / "human.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as existing:
        existing.bind(str(path))
        existing.listen()
        info = path.lstat()
        with pytest.raises(OSError) as exc:
            create(path)
        assert exc.value.errno == errno.EADDRINUSE
        assert (path.lstat().st_dev, path.lstat().st_ino) == (info.st_dev, info.st_ino)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(str(path))


def stale_socket(path):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as abandoned:
        abandoned.bind(str(path))


def test_stale_service_socket_recovered_and_serves_requests(tmp_path):
    path = tmp_path / "human.sock"
    stale_socket(path)
    server = create(path)
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    try:
        assert call(path, {"operation": "get_request", "request_id": "q1"}) == {"request_id": "q1"}
        assert server.broker.calls == [("human:owner", "q1")]
    finally:
        server.shutdown()
        worker.join()
        server.server_close()


@pytest.mark.parametrize("error", [PermissionError(errno.EACCES, "injected"),
                                   TimeoutError("injected"), OSError(errno.EAGAIN, "injected")])
def test_injected_ambiguous_probe_failure_never_unlinks(tmp_path, monkeypatch, error):
    path = tmp_path / "human.sock"
    stale_socket(path)
    info = path.lstat()

    def fail_connect(*args):
        raise error

    monkeypatch.setattr(socket.socket, "connect", fail_connect)
    with pytest.raises(OSError):
        create(path)
    assert (path.lstat().st_dev, path.lstat().st_ino) == (info.st_dev, info.st_ino)


def test_existing_symlink_endpoint_is_preserved(tmp_path):
    target = tmp_path / "valuable"
    target.write_text("preserve")
    path = tmp_path / "human.sock"
    path.symlink_to(target)
    with pytest.raises(PermissionError):
        create(path)
    assert path.is_symlink()
    assert target.read_text() == "preserve"


def test_close_preserves_replacement_inode(tmp_path):
    path = tmp_path / "human.sock"
    server = create(path)
    path.unlink()
    path.write_text("replacement")
    server.server_close()
    assert path.read_text() == "replacement"
