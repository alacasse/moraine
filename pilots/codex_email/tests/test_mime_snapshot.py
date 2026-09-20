import base64
import copy
from email.parser import BytesParser
from email.policy import default
import hashlib
import socket
import threading
import time

import pytest

from moraine_email.mime import prepare_reply
from moraine_email.models import PilotError, safe_text, strict_json, validate_grant, validate_proposal
from moraine_email.adapters.simulated import SimulatedProvider


def prepare(grant_body, body="Oui, mardi à 10 h.\r\nMerci !"):
    grant = validate_grant(grant_body)
    return prepare_reply(account=grant["account_id"], recipient=grant["recipient"],
                         source=grant["resources"][0], body_text=body, request_id="request-1")


def test_exact_mime_and_preview_roundtrip(grant_body):
    prepared = prepare(grant_body)
    raw = base64.b64decode(prepared["mime_b64"])
    assert hashlib.sha256(raw).hexdigest() == prepared["mime_sha256"]
    message = BytesParser(policy=default).parsebytes(raw)
    assert str(message["To"]) == prepared["preview"]["to"][0]
    assert str(message["Subject"]) == prepared["preview"]["subject"]
    assert message.get_content().replace("\r\n", "\n") == prepared["preview"]["body_text"]
    assert message.get_content_type() == "text/plain"
    assert message["Cc"] is None and message["Bcc"] is None
    assert list(message.iter_attachments()) == []
    assert message["In-Reply-To"] == "<original@example.test>"


@pytest.mark.parametrize("field,value", [("recipient", "a@example.test\r\nBcc: b@example.test"),
                                          ("recipient", "a@example.test,b@example.test"),
                                          ("expires_at", True), ("approved", True)])
def test_rejects_ambiguous_or_authoritative_fields(grant_body, field, value):
    grant_body[field] = value
    with pytest.raises(PilotError):
        validate_grant(grant_body)


def test_selection_is_copied_and_addresses_preserve_local_case(grant_body):
    grant_body["recipient"] = "Case@EXAMPLE.TEST"
    grant_body["resources"][0]["reply_address"] = "Case@example.test"
    checked = validate_grant(grant_body)
    grant_body["resources"][0]["text"] = "mutated"
    assert checked["resources"][0]["text"] != "mutated"
    assert checked["recipient"] == "Case@example.test"


def test_no_proposal_attachments_and_no_surrogates():
    body = {"grant_id": "g", "idempotency_key": "key", "reply_to_ref": "r", "body_text": "hi"}
    for extra in ({"attachments": []}, {"approved": True}, {"body_text": "\ud800"}):
        with pytest.raises(PilotError):
            validate_proposal({**body, **extra})


def test_selection_limits_and_header_controls(grant_body):
    for key, value in [("title", "unsafe\x1b[2J"), ("text", "a" * 32769), ("version", True)]:
        altered = copy.deepcopy(grant_body)
        altered["resources"][0][key] = value
        with pytest.raises(PilotError):
            validate_grant(altered)


def test_terminal_and_json_are_inert():
    assert safe_text("hello\x1b[2J\u202e\nworld") == "hello\\u001b[2J\\u202e\nworld"
    assert safe_text("\x1b") != safe_text(r"\u001b")
    assert safe_text(r"\u001b") == r"\\u001b"
    for raw in ['{"approved":false,"approved":true}', '{"a":NaN}', '{"a":Infinity}']:
        with pytest.raises(PilotError):
            strict_json(raw)


def test_provider_logs_actual_bytes_without_deduplication(provider, oracle, grant_body):
    prepared = prepare(grant_body)
    one = provider.send_prepared(prepared, "same-execution")
    two = provider.send_prepared(prepared, "same-execution")
    assert one["state"] == two["state"] == "accepted"
    effects = oracle.records("effects")
    assert len(effects) == len(oracle.records("attempts")) == 2
    assert effects[0]["mime_b64"] == prepared["mime_b64"]
    assert effects[0]["message_id"] != effects[1]["message_id"]


@pytest.mark.parametrize("mode,state,effects", [("reject_before", "failed", 0),
                                               ("accept_then_disconnect", "unknown", 1),
                                               ("malformed_success", "unknown", 1)])
def test_provider_failure_semantics(provider, oracle, grant_body, mode, state, effects):
    oracle.mode = mode
    result = provider.send_prepared(prepare(grant_body), "execution-1")
    assert result["state"] == state
    assert len(oracle.records("attempts")) == 1
    assert len(oracle.records("effects")) == effects


def test_total_deadline_includes_trickling_response_headers(grant_body):
    attempts = []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(6)

        def trickle():
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(2)
                attempts.append(connection.recv(65536))
                try:
                    connection.sendall(b"HTTP/1.1 200 OK\r\n")
                    for _ in range(20):
                        connection.sendall(b"X-Trickle: header\r\n")
                        time.sleep(.3)
                except OSError:
                    pass

        thread = threading.Thread(target=trickle, daemon=True)
        thread.start()
        adapter = SimulatedProvider(f"http://127.0.0.1:{listener.getsockname()[1]}", "synthetic-token")
        start = time.monotonic()
        result = adapter.send_prepared(prepare(grant_body), "deadline-execution")
        elapsed = time.monotonic() - start
        thread.join(timeout=2)
    assert result["state"] == "unknown"
    assert 3.5 <= elapsed < 5.5
    assert len(attempts) == 1
