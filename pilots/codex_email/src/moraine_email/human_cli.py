"""Human-only interactive client. Message content is rendered as inert JSON text."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket

from .human_server import MAX_BODY, strict_json
from .models import safe_text


def call(path: Path, payload: dict) -> dict:
    raw = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode() + b"\n"
    if len(raw) > MAX_BODY:
        raise ValueError("request too large")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(15)
        connection.connect(str(path))
        connection.sendall(raw)
        with connection.makefile("rb") as stream:
            response = stream.readline(4 * MAX_BODY + 1)
    if len(response) > 4 * MAX_BODY or not response.endswith(b"\n"):
        raise ValueError("invalid server response")
    data = strict_json(response)
    if not isinstance(data, dict) or set(data) not in ({"result"}, {"error"}):
        raise ValueError("invalid server response")
    if "error" in data:
        raise ValueError("human operation refused: " + json.dumps(data["error"], ensure_ascii=True))
    return data["result"]


def display(value):
    # Escapes every non-ASCII/control character, including ANSI, bidi and newlines
    # embedded in untrusted fields. JSON structure remains readable.
    print(json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False))


def display_review(envelope):
    snapshot = envelope["snapshot"]
    prepared = snapshot["prepared_reply"]
    metadata = {key: value for key, value in envelope.items() if key != "snapshot"}
    metadata["snapshot"] = {key: value for key, value in snapshot.items() if key != "prepared_reply"}
    metadata["mime_sha256"] = prepared["mime_sha256"]
    metadata["preview"] = {key: value for key, value in prepared["preview"].items() if key != "body_text"}
    display(metadata)
    print("BEGIN exact reply body (each line prefixed with |):")
    for line in safe_text(prepared["preview"]["body_text"]).split("\n"):
        print("| " + line)
    print("END exact reply body")


def review(path: Path, request_id: str, *, read_input=input):
    snapshot = call(path, {"operation": "review", "request_id": request_id})
    display_review(snapshot)
    choice = read_input("Type approve or reject for this exact snapshot (anything else cancels): ").strip()
    if choice not in {"approve", "reject"}:
        print("Cancelled; no decision sent.")
        return
    display(call(path, {"operation": "decide_review", "request_id": request_id,
                        "action_digest": snapshot["action_digest"], "nonce": snapshot["nonce"],
                        "decision": choice}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("create-grant").add_argument("file", type=Path)
    commands.add_parser("revoke-grant").add_argument("grant_id")
    for command in ("get-request", "review", "resolve-unknown"):
        commands.add_parser(command).add_argument("request_id")
    args = parser.parse_args()
    try:
        if args.command == "review":
            review(args.socket, args.request_id)
            return
        if args.command == "create-grant":
            with args.file.open("rb") as source:
                raw = source.read(MAX_BODY + 1)
            if len(raw) > MAX_BODY:
                raise ValueError("grant file too large")
            payload = {"operation": "create_grant", "body": strict_json(raw)}
        elif args.command == "revoke-grant":
            payload = {"operation": "revoke_grant", "grant_id": args.grant_id}
        elif args.command == "resolve-unknown":
            display(call(args.socket, {"operation": "get_request", "request_id": args.request_id}))
            text = input("Resolution permits a future attempt that may duplicate a prior effect. Type acknowledge-duplicate-risk: ")
            if text != "acknowledge-duplicate-risk":
                print("Cancelled; unresolved barrier retained.")
                return
            payload = {"operation": "resolve_unknown", "request_id": args.request_id,
                       "acknowledge_duplicate_risk": True}
        else:
            payload = {"operation": "get_request", "request_id": args.request_id}
        display(call(args.socket, payload))
    except (OSError, ValueError, EOFError, KeyboardInterrupt):
        parser.exit(1, "Human operation failed or cancelled.\n")


if __name__ == "__main__":
    main()
