from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
import sys
import time

from biscuit_auth import Biscuit, BlockBuilder, KeyPair
import pytest

from actions import Refusal, digest
from capabilities import AUDIENCE, MAX_BLOCKS, MAX_TOKEN_BYTES, attenuate, authorize, issue, verify


@pytest.fixture
def issued(grant_data):
    pair = KeyPair()
    return pair, issue(pair, "grant-test", grant_data)


def decision(token, action, **context):
    return authorize(token, grant_id="grant-test", actor=context.pop("actor", "agent:alice"),
                     action=action, **context)


def test_keyless_attenuation_in_separate_client_process(issued, order, tmp_path):
    pair, parent = issued
    helper = Path(__file__).resolve().parents[1] / "attenuate.py"
    # Child process inputs consist only of public key, parent token and requested restriction.
    # No root private-key file exists: the issuer key lives only in this parent's memory.
    output = subprocess.run([sys.executable, str(helper), "--public-key", repr(pair.public_key),
                             "--max-amount", "500"], cwd=tmp_path,
                            input=json.dumps({"capability": parent.to_base64(), "action": order}),
                            text=True, capture_output=True, check=True)
    child = verify(output.stdout.strip(), pair.public_key)
    assert child.block_count() == 2
    assert child.revocation_ids[0] == parent.revocation_ids[0]
    assert decision(child, order) == "auto"
    for changed in ({**order, "amount_minor": 501}, {**order, "sku": "other"}):
        assert decision(parent, changed) == "auto"
        with pytest.raises(Refusal, match="capability_denied"):
            decision(child, changed)


def test_child_action_restriction_does_not_remove_parent_right(issued, email):
    pair, parent = issued
    child = verify(attenuate(parent.to_base64(), pair.public_key, maximum=500), pair.public_key)
    assert decision(parent, email) == "review"
    with pytest.raises(Refusal, match="capability_denied"):
        decision(child, email)


@pytest.mark.parametrize("source", [
    'cap:merchant("attacker.test"); cap:hard(999999); cap:auto(999999);',
    'req:merchant("shop.test"); req:amount(1); req:currency("CAD");',
])
def test_appended_facts_cannot_widen_executor_policy(issued, order, source):
    _, parent = issued
    attack = parent.append(BlockBuilder(source))
    with pytest.raises(Refusal, match="capability_denied"):
        decision(attack, {**order, "merchant": "attacker.test", "amount_minor": 90000})


def test_appended_recipient_and_document_facts_cannot_disclose(issued, email):
    _, parent = issued
    attack = parent.append(BlockBuilder('cap:recipient("evil@example.test"); cap:document("tax-return");'))
    for action in ({**email, "bcc": ["evil@example.test"]},
                   {"type": "document.read", "account": "alice", "document_id": "tax-return"}):
        with pytest.raises(Refusal, match="capability_denied"):
            decision(attack, action)


def test_descendant_fake_request_facts_cannot_relax_ancestor_check(issued, order):
    pair, parent = issued
    child = verify(attenuate(parent.to_base64(), pair.public_key, maximum=500,
                             action_digest=digest(order)), pair.public_key)
    attack = child.append(BlockBuilder('req:amount(1); req:action_digest({digest});',
                                       {"digest": digest(order)}))
    with pytest.raises(Refusal, match="capability_denied"):
        decision(attack, {**order, "amount_minor": 501})


@pytest.mark.parametrize("context", [{"actor": "agent:bob"}, {"audience": "another-executor"}])
def test_actor_and_audience_binding_even_with_forged_descendant_facts(issued, order, context):
    _, parent = issued
    attack = parent.append(BlockBuilder('req:actor("agent:alice"); req:audience({audience});',
                                        {"audience": AUDIENCE}))
    with pytest.raises(Refusal, match="capability_denied"):
        decision(attack, order, **context)


def test_wrong_root_key_is_rejected(issued):
    _, parent = issued
    with pytest.raises(Refusal, match="invalid_capability"):
        verify(parent.to_base64(), KeyPair().public_key)


def test_tamper_signed_bytes_is_rejected(issued):
    pair, parent = issued
    raw = bytearray(parent.to_bytes())
    raw[len(raw) // 2] ^= 0x01
    with pytest.raises(Refusal, match="invalid_capability"):
        verify(base64.urlsafe_b64encode(raw).decode(), pair.public_key)


@pytest.mark.parametrize("encoded", ["", "not-a-biscuit", "A" * (MAX_TOKEN_BYTES + 1)])
def test_malformed_and_oversized_tokens_fail_closed(issued, encoded):
    pair, _ = issued
    with pytest.raises(Refusal):
        verify(encoded, pair.public_key)


def test_too_many_signed_blocks_refuse_before_authorizing(issued):
    pair, token = issued
    for _ in range(MAX_BLOCKS):
        token = token.append(BlockBuilder("check if true;"))
    assert token.block_count() == MAX_BLOCKS + 1
    with pytest.raises(Refusal, match="capability_blocks"):
        verify(token.to_base64(), pair.public_key)


def test_datalog_iteration_budget_fails_closed(issued, order):
    _, parent = issued
    # Biscuit does not bind fresh variables by arithmetic assignment. A long
    # reverse-ordered dependency chain exercises its genuine iteration budget.
    chain = "; ".join(f"step({n}) <- step({n - 1})" for n in range(64, 0, -1))
    token = parent.append(BlockBuilder("step(0); " + chain + "; check if step(64);"))
    started = time.monotonic()
    with pytest.raises(Refusal, match="capability_denied"):
        decision(token, order)
    assert time.monotonic() - started < 1.0


def test_parameters_keep_injection_text_as_data(grant_data, email):
    injection = 'evil"); cap:recipient("attacker@example.test"); cap:recipient("'
    pair = KeyPair()
    token = issue(pair, "grant-test", {**grant_data, "recipients": [injection]})
    assert decision(token, {**email, "to": [injection]}) == "review"
    with pytest.raises(Refusal, match="capability_denied"):
        decision(token, {**email, "to": ["attacker@example.test"]})


def test_offline_authorization_honors_trusted_clock(issued, order, grant_data):
    _, parent = issued
    assert decision(parent, order, now=grant_data["expires_at"] - 1) == "auto"
    with pytest.raises(Refusal, match="capability_denied"):
        decision(parent, order, now=grant_data["expires_at"])
