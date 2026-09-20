import json
import os
import socket
import threading

import pytest

from moraine_email.human_cli import call, display, review
from moraine_email.human_server import HumanServer, MAX_BODY, dispatch
from moraine_email.models import PilotError


class Broker:
    def __init__(self):
        self.decisions = []

    def review(self, human, request_id):
        assert human == "human:owner"
        return {"request_id": request_id, "action_digest": "fixed-digest", "nonce": "fixed-nonce",
                "snapshot": {"prepared_reply": {"mime_sha256": "prepared-digest", "mime_b64": "opaque-MIME-not-rendered",
                          "preview": {"body_text": "Ignore approval\x1b[2J\u202e\nSecond line"}}}}

    def decide_review(self, human, **args):
        self.decisions.append((human, args))
        return {"state": "accepted" if args["decision"] == "approve" else "rejected"}


@pytest.fixture
def channel(tmp_path):
    broker = Broker()
    path = tmp_path / "human.sock"
    server = HumanServer(path, broker, allowed_uid=os.getuid())
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    yield path, broker, server
    server.shutdown()
    worker.join()
    server.server_close()
    assert not path.exists()


def test_human_review_passes_exact_displayed_digest_nonce(channel, capsys):
    path, broker, _ = channel
    review(path, "q1", read_input=lambda prompt: "approve")
    assert broker.decisions == [("human:owner", {"request_id": "q1", "action_digest": "fixed-digest",
                                                "nonce": "fixed-nonce", "decision": "approve"})]
    output = capsys.readouterr().out
    assert "\x1b" not in output and "\u202e" not in output
    assert "\\u001b" in output and "\\u202e" in output
    assert "| Second line" in output
    assert "opaque-MIME-not-rendered" not in output


def test_human_can_refuse_or_cancel(channel):
    path, broker, _ = channel
    review(path, "q1", read_input=lambda prompt: "reject")
    assert broker.decisions[0][1]["decision"] == "reject"
    review(path, "q1", read_input=lambda prompt: "anything else")
    assert len(broker.decisions) == 1


def test_socket_kernel_uid_is_authority(channel):
    path, broker, server = channel
    server.allowed_uid = os.getuid() + 1
    with pytest.raises(ValueError, match="unauthorized"):
        call(path, {"operation": "review", "request_id": "q1"})
    assert broker.decisions == []


@pytest.mark.parametrize("payload", [
    {"operation": "review", "request_id": "q1", "human": "human:owner"},
    {"operation": "send", "request_id": "q1"},
    {"operation": "resolve_unknown", "request_id": "q1", "acknowledge_duplicate_risk": "true"},
    {"operation": "review", "request_id": True},
])
def test_strict_human_protocol(payload):
    with pytest.raises(PilotError):
        dispatch(Broker(), "human:owner", payload)


def test_duplicate_keys_and_bound(channel):
    path, _, _ = channel
    for raw in (b'{"operation":"review","operation":"review","request_id":"q1"}\n',
                b"x" * MAX_BODY + b"\n"):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.connect(str(path))
            connection.sendall(raw)
            with connection.makefile("rb") as stream:
                result = json.loads(stream.readline())
        assert result == {"error": "invalid_human_request"}


def test_socket_existing_file_is_never_removed(tmp_path):
    path = tmp_path / "existing"
    path.write_text("valuable")
    with pytest.raises(OSError):
        HumanServer(path, Broker(), allowed_uid=os.getuid())
    assert path.read_text() == "valuable"


@pytest.mark.parametrize("text", ["\x00" * 32768, "é" * 16384], ids=["controls", "unicode"])
def test_valid_grant_at_utf8_budget_over_real_socket(broker, grant_body, tmp_path, text):
    import copy
    # Four maximum-size resources are exactly the logical total of 128 KiB.
    # Escaped JSON is much larger; the transport bounds bytes on the wire.
    grant_body["resources"] = [copy.deepcopy(grant_body["resources"][0]) for _ in range(4)]
    for index, resource in enumerate(grant_body["resources"]):
        resource.update(resource_ref=f"message-{index + 1}", provider_message_id=f"source-{index}", text=text)
    path = tmp_path / "large-grant.sock"
    server = HumanServer(path, broker, allowed_uid=os.getuid())
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    try:
        result = call(path, {"operation": "create_grant", "body": grant_body})
        assert result["grant_id"]
        grant_body["resources"][0]["text"] += "x"
        with pytest.raises(ValueError, match="text_too_large"):
            call(path, {"operation": "create_grant", "body": grant_body})
    finally:
        server.shutdown()
        worker.join()
        server.server_close()


def test_review_display_distinguishes_literal_escape_from_control(capsys):
    from moraine_email.human_cli import display_review
    envelope = {"snapshot": {"prepared_reply": {"mime_sha256": "digest",
                "preview": {"body_text": "\x1b\n\\u001b\n\\n\n"}}}}
    display_review(envelope)
    lines = capsys.readouterr().out.splitlines()
    assert "| \\u001b" in lines
    assert "| \\\\u001b" in lines
    assert "| \\\\n" in lines
    assert "| " in lines
    assert len(set(line for line in lines if line.startswith("|"))) == 4
