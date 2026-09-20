"""Opt-in read-only probe run separately under each real installation identity.

No UID switching, mutation, secret output or business operations.
"""
import argparse
import json
import os
from pathlib import Path
import socket


def inaccessible(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except PermissionError:
        return True
    else:
        os.close(fd)
        return False


def peer_result(path):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(3)
        try:
            connection.connect(str(path))
        except PermissionError:
            return "connect_denied"
        connection.sendall(b"{}\n")  # cannot dispatch a business operation
        with connection.makefile("rb") as stream:
            return json.loads(stream.readline(4096)).get("error")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", required=True, choices=["agent", "human", "group-peer", "service"])
    parser.add_argument("--expected-uid", required=True, type=int)
    parser.add_argument("--human-gid", required=True, type=int)
    parser.add_argument("--service-uid", required=True, type=int)
    parser.add_argument("--human-uid", required=True, type=int)
    parser.add_argument("--broker-pid", required=True, type=int)
    parser.add_argument("--opa-pid", required=True, type=int)
    parser.add_argument("--confirm-installed-probe", action="store_true")
    args = parser.parse_args()
    if not args.confirm_installed_probe:
        parser.error("explicit --confirm-installed-probe required")
    required_count = 2 if args.role in {"human", "service"} else 3
    if len({args.service_uid, args.human_uid, args.expected_uid}) != required_count:
        parser.error("roles must use distinct real UIDs")
    expected = {"agent": "connect_denied", "human": "invalid_human_request",
                "group-peer": "unauthorized", "service": "unauthorized"}[args.role]
    groups = set(os.getgroups()) | {os.getegid()}
    checks = {"expected_uid": os.geteuid() == args.expected_uid,
              "correct_group": (args.human_gid in groups) == (args.role != "agent")}
    if args.role == "human":
        checks["human_identity"] = os.geteuid() == args.human_uid
    elif args.role == "service":
        checks["service_identity"] = os.geteuid() == args.service_uid
    if not all(checks.values()):
        print(json.dumps({"checks": checks}))
        return 1
    checks["socket"] = peer_result(Path("/run/moraine-pilot/human.sock")) == expected
    checks["immutable_install"] = True
    for path in [Path("/opt/moraine-pilot"), Path("/etc/moraine-pilot/config.json")]:
        if not path.exists():
            raise FileNotFoundError(path)
        for item in [path, *path.rglob("*")]:
            if os.access(item, os.W_OK):
                checks["immutable_install"] = False
    if args.role != "service":
        for path in ["/var/lib/moraine-pilot", "/run/moraine-pilot/opa",
                     "/etc/moraine-pilot/secrets/provider-token",
                     f"/proc/{args.broker_pid}/environ", f"/proc/{args.opa_pid}/environ"]:
            checks[path] = inaccessible(path)
    print(json.dumps({"uid": os.geteuid(), "groups": sorted(groups), "role": args.role,
                      "checks": checks, "passed": all(checks.values())}, sort_keys=True))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
