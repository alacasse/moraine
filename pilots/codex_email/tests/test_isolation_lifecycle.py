"""Real Linux processes under one UID; no installed systemd isolation claim."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time

import httpx
import pytest

from moraine_email.policy import OPA, PolicyFailure
from tests.test_process_workflow import port, ready

ROOT = Path(__file__).resolve().parents[1]


def wait_for(predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.05)
    raise AssertionError("timed out waiting for process observation")


def child_opa(pid):
    children = Path(f"/proc/{pid}/task/{pid}/children").read_text().split()
    matches = [int(child) for child in children
               if Path(f"/proc/{child}/exe").resolve() == (ROOT / ".tools/opa").resolve()]
    assert len(matches) == 1, children
    return matches[0]


def alive(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().split(") ", 1)[1][0] != "Z"
    except FileNotFoundError:
        return False


@contextmanager
def launched(command, log):
    with log.open("w") as output:
        process = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=output,
                                   start_new_session=True)
        try:
            yield process
        finally:
            # Harness cleanup even when parent died, not product supervision.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)


@pytest.fixture
def launcher(tmp_path):
    for name in ("agent", "provider"):
        path = tmp_path / name
        path.write_text(secrets.token_urlsafe(32))
        path.chmod(0o600)
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"agent": "agent:pilot", "owner": "human:owner", "account": "pilot@example.test"}))
    runtime = tmp_path / "opa"
    runtime.mkdir(mode=0o700)
    endpoint_port = port()
    human = tmp_path / "human.sock"
    command = [sys.executable, "-m", "moraine_email.server", "--state-dir", str(tmp_path / "state"),
               "--config", str(config), "--agent-token-file", str(tmp_path / "agent"),
               "--provider-token-file", str(tmp_path / "provider"), "--provider-url", "http://127.0.0.1:8099",
               "--opa-binary", str(ROOT / ".tools/opa"), "--human-socket", str(human),
               "--human-uid", str(os.getuid()), "--port", str(endpoint_port),
               "--opa-runtime-dir", str(runtime)]
    return command, f"http://127.0.0.1:{endpoint_port}/mcp", human, runtime


def observe_socket(path):
    with httpx.Client(transport=httpx.HTTPTransport(uds=str(path)), base_url="http://opa",
                      timeout=1, trust_env=False) as client:
        return client.post("/v1/data/broker/decision", json={"input": {}}).status_code


def test_broker_sigkill_observes_unsupervised_opa_then_explicit_group_cleanup_and_restart(launcher, tmp_path):
    command, endpoint, human, runtime = launcher
    with launched(command, tmp_path / "crash.log") as broker:
        ready(broker, endpoint, human)
        opa_pid = child_opa(broker.pid)
        opa_socket = next(runtime.glob("*/opa.sock"))
        assert observe_socket(opa_socket) in (401, 403)
        broker.kill()
        assert broker.wait(timeout=5) == -signal.SIGKILL
        assert alive(opa_pid)  # negative evidence: Python finally cannot run
        unauthenticated_status = observe_socket(opa_socket)
        assert unauthenticated_status in (401, 403)
        assert human.exists()
        observation = {
            "broker_sigkill": True, "opa_survived_without_supervisor": True,
            "broker_pid": broker.pid, "opa_pid": opa_pid,
            "unauthenticated_opa_http_status": unauthenticated_status,
            "systemd_exercised": False, "dispatch_in_progress": False}
        evidence = tmp_path / "sigkill-observation.json"
        evidence.write_text(json.dumps(observation, indent=2))
    wait_for(lambda: not alive(opa_pid))
    observation["opa_absent_after_harness_cleanup"] = True
    observation["cleanup_mechanism"] = "harness killpg(SIGKILL), not systemd"
    evidence.write_text(json.dumps(observation, indent=2))
    with launched(command, tmp_path / "restart.log") as restarted:
        ready(restarted, endpoint, human)
        new_opa_pid = child_opa(restarted.pid)
        assert new_opa_pid != opa_pid
        observation["restarted_opa_pid"] = new_opa_pid
        assert human.is_socket()
        restarted.terminate()
        assert restarted.wait(timeout=10) == 0
        # Observe before the harness finally can kill remaining children.
        assert not alive(new_opa_pid)
        assert not human.exists()
        observation["restarted_opa_absent_after_graceful_stop"] = True
        evidence.write_text(json.dumps(observation, indent=2))


def test_opa_death_retires_broker_nonzero_and_manual_restart_recovers(launcher, tmp_path):
    command, endpoint, human, runtime = launcher
    with launched(command, tmp_path / "opa-failed.log") as broker:
        ready(broker, endpoint, human)
        opa_pid = child_opa(broker.pid)
        opa_socket = next(runtime.glob("*/opa.sock"))
        os.kill(opa_pid, signal.SIGKILL)
        assert broker.wait(timeout=12) == 1
        assert not alive(opa_pid)
        assert not human.exists()
        assert not opa_socket.exists()
    with launched(command, tmp_path / "opa-recovery.log") as restarted:
        ready(restarted, endpoint, human)
        assert observe_socket(next(runtime.glob("*/opa.sock"))) in (401, 403)
        restarted.terminate()
        assert restarted.wait(timeout=10) == 0


def test_policy_fails_closed_when_actual_opa_dies(tmp_path):
    policy = OPA(ROOT / ".tools/opa", runtime_dir=tmp_path)
    try:
        policy.process.kill()
        policy.process.wait(timeout=3)
        with pytest.raises(PolicyFailure, match="policy_unavailable"):
            policy.decide({})
    finally:
        policy.close()


@pytest.mark.parametrize("kind", ["public", "symlink", "file"])
def test_opa_rejects_unsafe_runtime_before_spawn(tmp_path, kind):
    runtime = tmp_path / "runtime"
    if kind == "file":
        runtime.write_text("not a directory")
    elif kind == "symlink":
        runtime.symlink_to(tmp_path, target_is_directory=True)
    else:
        runtime.mkdir(mode=0o755)
    with pytest.raises(ValueError, match="private"):
        OPA(ROOT / ".tools/opa", runtime_dir=runtime)
