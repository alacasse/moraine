"""Loopback-only simulated pilot launcher; secrets are supplied by protected files."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import signal
import threading

import uvicorn

from .adapters.simulated import SimulatedProvider
from .broker import Broker
from .human_server import HumanServer, strict_json
from .mcp_server import create_app
from .policy import OPA, PolicyFailure
from .models import PilotError


def read_secret(path: Path) -> str:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
            raise ValueError("secret file must be a private regular file owned by the service UID")
        raw = source.read(4097)
    if len(raw) > 4096:
        raise ValueError("secret file too large")
    value = raw.decode("ascii").strip()
    if len(value) < 32 or any(c.isspace() for c in value):
        raise ValueError("secret must contain at least 32 ASCII characters without whitespace")
    return value


def run_http(app, policy, port):
    """An exited policy child retires this broker; systemd owns group restart.

    Requests already in progress still use the broker's fail-closed policy path.
    No attempt is made to restart OPA in place or replay work.
    """
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port,
                                         access_log=False, log_level="warning",
                                         timeout_graceful_shutdown=10))
    stop = threading.Event()
    failed = threading.Event()

    def watch():
        while not stop.wait(0.1):
            if policy.process.poll() is not None:
                failed.set()
                server.should_exit = True
                return

    watcher = threading.Thread(target=watch, name="opa-watch", daemon=True)
    watcher.start()
    try:
        server.run()
    finally:
        stop.set()
        watcher.join(timeout=3)
    if failed.is_set() or policy.process.poll() is not None:
        raise PolicyFailure()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path, help="JSON with agent, owner and account identities")
    parser.add_argument("--agent-token-file", required=True, type=Path)
    parser.add_argument("--provider-token-file", required=True, type=Path)
    parser.add_argument("--provider-url", required=True)
    parser.add_argument("--opa-binary", required=True, type=Path)
    parser.add_argument("--human-socket", required=True, type=Path)
    parser.add_argument("--human-uid", required=True, type=int)
    parser.add_argument("--human-socket-gid", type=int, help="Connection group; peer UID remains authoritative")
    parser.add_argument("--opa-runtime-dir", type=Path, help="Existing private service runtime directory")
    parser.add_argument("--resource-sets", type=Path, help="Local synthetic selection catalogue: public names to closed message ID lists")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    policy = provider = broker = human = worker = None

    def terminate(signum, frame):
        # Uvicorn restores and re-raises SIGTERM after graceful HTTP shutdown.
        # Convert that final signal into normal Python unwinding so the human
        # channel, SQLite, provider and OPA are closed by the outer finally.
        raise SystemExit(0)

    previous_sigterm = signal.signal(signal.SIGTERM, terminate)
    try:
        if not 1024 <= args.port <= 65535:
            raise ValueError("port out of range")
        with args.config.open("rb") as source:
            raw = source.read(4097)
        if len(raw) > 4096:
            raise ValueError("configuration too large")
        config = strict_json(raw)
        if not isinstance(config, dict) or set(config) != {"agent", "owner", "account"}:
            raise ValueError("configuration must contain exactly agent, owner, account")
        if any(not isinstance(value, str) or not value or len(value) > 128 for value in config.values()):
            raise ValueError("invalid configured identity")
        if config["agent"] == config["owner"]:
            raise ValueError("agent and owner identities must differ")
        token = read_secret(args.agent_token_file)
        provider_token = read_secret(args.provider_token_file)
        if token == provider_token:
            raise ValueError("agent and provider credentials must differ")
        args.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = args.state_dir.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
            raise ValueError("state directory must be private and owned by the service UID")
        policy = OPA(args.opa_binary, runtime_dir=args.opa_runtime_dir)
        provider = SimulatedProvider(args.provider_url, provider_token)
        resource_sets = None
        if args.resource_sets:
            with args.resource_sets.open("rb") as source:
                raw = source.read(8193)
            if len(raw) > 8192:
                raise ValueError("resource catalogue too large")
            resource_sets = strict_json(raw)
        broker = Broker(args.state_dir, policy, provider, resource_sets=resource_sets, **config)
        human = HumanServer(args.human_socket, broker, allowed_uid=args.human_uid, owner=config["owner"],
                            socket_gid=args.human_socket_gid)
        worker = threading.Thread(target=human.serve_forever, name="human-channel", daemon=True)
        worker.start()
        app = create_app(broker, token=token, agent=config["agent"], port=args.port)
        del token, provider_token
        run_http(app, policy, args.port)
    except (OSError, ValueError, PolicyFailure, PilotError):
        parser.exit(1, "Pilot startup refused; check protected configuration, paths and local dependencies.\n")
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        if human is not None:
            if worker is not None and worker.is_alive():
                human.shutdown()
                worker.join(timeout=10)
            human.server_close()
        if broker is not None:
            broker.close()
        if provider is not None:
            provider.close()
        if policy is not None:
            policy.close()
        signal.signal(signal.SIGTERM, previous_sigterm)


if __name__ == "__main__":
    main()
