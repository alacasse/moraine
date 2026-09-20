"""Opt-in disruptive probe for a FUTURE disposable simulated installation.

Requires administrator and explicit flag. SIGKILL broker then OPA, await systemd.
No email request. Never run on a live pilot. Evidence: PID/starttime/cgroup/socket.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time

UNIT = "moraine-email.service"


def properties():
    output = subprocess.check_output(["systemctl", "show", UNIT, "--property=MainPID,ControlGroup,ActiveState,KillMode,Restart"], text=True)
    return dict(line.split("=", 1) for line in output.splitlines())


def identity(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().split(") ", 1)[1].split()
        return None if fields[0] == "Z" else (pid, fields[19])
    except FileNotFoundError:
        return None


def snapshot():
    props = properties()
    pid = int(props["MainPID"])
    if not pid or props["ActiveState"] != "active":
        raise RuntimeError("service is not active")
    group = Path("/sys/fs/cgroup") / props["ControlGroup"].lstrip("/")
    members = [int(p) for p in (group / "cgroup.procs").read_text().split()]
    opa = [p for p in members if Path(f"/proc/{p}/exe").resolve() == Path("/opt/moraine-pilot/.tools/opa")]
    if len(opa) != 1 or pid not in members:
        raise RuntimeError("expected one broker and OPA in the unit cgroup")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(1)
        connection.connect("/run/moraine-pilot/human.sock")
    return {"broker": identity(pid), "opa": identity(opa[0]),
            "members": [identity(p) for p in members], "properties": props}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-kill-and-restart-simulated-installation", action="store_true")
    args = parser.parse_args()
    if not args.allow_kill_and_restart_simulated_installation or os.geteuid() != 0:
        parser.error("explicit flag and administrator execution required")
    before = snapshot()
    if before["properties"]["KillMode"] != "control-group" or before["properties"]["Restart"] != "on-failure":
        raise SystemExit("unexpected installed supervision policy")
    records = []
    for target in ("broker", "opa"):
        old = snapshot()
        if not old[target] or identity(old[target][0]) != old[target]:
            raise SystemExit("process identity changed before signal")
        fd = os.pidfd_open(old[target][0])
        try:
            if identity(old[target][0]) != old[target]:
                raise SystemExit("process identity changed before signal")
            signal.pidfd_send_signal(fd, signal.SIGKILL)
        finally:
            os.close(fd)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                new = snapshot()
                gone = all(item is None or identity(item[0]) != item for item in old["members"])
                if gone and new["broker"] != old["broker"] and new["opa"] != old["opa"]:
                    records.append({"killed": target, "old": old, "new": new, "old_members_gone": True})
                    break
            except (OSError, RuntimeError):
                pass
            time.sleep(.2)
        else:
            raise SystemExit("restart/group cleanup failed; inspect unit before any real use")
    print(json.dumps({"unit": UNIT, "observations": records}, sort_keys=True))


if __name__ == "__main__":
    main()
