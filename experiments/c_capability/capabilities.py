"""Real Biscuit issuance, scoped Datalog decisions and public-key attenuation."""
from __future__ import annotations

from datetime import timedelta
import os
from pathlib import Path
import time

from biscuit_auth import AuthorizerBuilder, Biscuit, BiscuitBuilder, BlockBuilder, Check, Fact, KeyPair, PrivateKey

from actions import Refusal, digest

AUDIENCE = "moraine:c:v1"
MAX_TOKEN_BYTES = 32768
MAX_BLOCKS = 8

AUTHORITY = """
cap:grant({grant}); cap:actor({actor}); cap:account({account}); cap:audience({audience});
cap:expiry({expiry}); cap:currency({currency}); cap:auto({auto}); cap:hard({hard});
cap:action("email.send"); cap:action("order.create"); cap:action("document.read");
check if req:grant({grant});
check if req:actor({actor});
check if req:account({account});
check if req:audience({audience});
check if req:time($time), $time < {expiry};
check if req:action($action), cap:action($action);
"""

POLICY = """
check if cap:grant({grant}), cap:actor({actor}), cap:account({account}), cap:audience({audience});
allow if req:action("document.read");
allow if req:action("order.create"), req:merchant($m), cap:merchant($m),
         req:currency($c), cap:currency($c), req:shipping("home"), req:recurring(false),
         req:amount($n), cap:hard($hard), $n <= $hard, cap:auto($auto), $n <= $auto;
allow if req:action("email.send");
allow if req:action("order.create"), req:merchant($m), cap:merchant($m),
         req:currency($c), cap:currency($c), req:shipping("home"), req:recurring(false),
         req:amount($n), cap:hard($hard), $n <= $hard;
"""


def keypair(state_dir: Path) -> KeyPair:
    path = state_dir / "issuer.key"
    if path.exists():
        if path.stat().st_mode & 0o077:
            raise RuntimeError("issuer key permissions must be 0600")
        return KeyPair.from_private_key(PrivateKey(path.read_text().strip()))
    pair = KeyPair()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        output.write(repr(pair.private_key) + "\n")
        output.flush()
        os.fsync(output.fileno())
    (state_dir / "issuer.pub").write_text(repr(pair.public_key) + "\n")
    return pair


def issue(pair: KeyPair, grant_id: str, grant: dict) -> Biscuit:
    builder = BiscuitBuilder(AUTHORITY, {
        "grant": grant_id, "actor": grant["agent"], "account": grant["account"],
        "audience": AUDIENCE, "expiry": grant["expires_at"], "currency": grant["currency"],
        "auto": grant["auto_limit_minor"], "hard": grant["hard_limit_minor"],
    })
    for field, template in (
        ("recipients", "cap:recipient({value})"),
        ("document_ids", "cap:document({value})"),
        ("merchants", "cap:merchant({value})"),
    ):
        for value in grant[field]:
            builder.add_fact(Fact(template, {"value": value}))
    return builder.build(pair.private_key)


def verify(encoded: str, public_key) -> Biscuit:
    if not isinstance(encoded, str) or not 0 < len(encoded) <= MAX_TOKEN_BYTES:
        raise Refusal("capability_size", 403)
    try:
        token = Biscuit.from_base64(encoded, public_key)
        if token.block_count() > MAX_BLOCKS:
            raise Refusal("capability_blocks", 403)
        return token
    except Refusal:
        raise
    except Exception:
        raise Refusal("invalid_capability", 403) from None


def authorize(token: Biscuit, *, grant_id: str, actor: str, action: dict,
              audience: str = AUDIENCE, now: int | None = None) -> str:
    """Offline decision: deliberately has no revocation or approval database."""
    builder = AuthorizerBuilder(POLICY, {"grant": grant_id, "actor": actor,
                                      "account": action["account"], "audience": audience})
    limits = builder.limits()
    limits.max_facts = 2048
    limits.max_iterations = 32
    limits.max_time = timedelta(milliseconds=50)
    builder.set_limits(limits)
    for template, value in (
        ("req:grant({value})", grant_id), ("req:actor({value})", actor),
        ("req:account({value})", action["account"]), ("req:audience({value})", audience),
        ("req:time({value})", int(time.time()) if now is None else now),
        ("req:action({value})", action["type"]), ("req:action_digest({value})", digest(action)),
    ):
        builder.add_fact(Fact(template, {"value": value}))
    if action["type"] == "email.send":
        for recipient in set(action["to"] + action["cc"] + action["bcc"]):
            builder.add_check(Check("check if cap:recipient({value})", {"value": recipient}))
        documents = [a["id"] for a in action["attachments"]]
    elif action["type"] == "document.read":
        documents = [action["document_id"]]
    else:
        documents = []
        for field, template in (
            ("merchant", "req:merchant({value})"), ("currency", "req:currency({value})"),
            ("amount_minor", "req:amount({value})"), ("shipping_address_id", "req:shipping({value})"),
            ("recurring", "req:recurring({value})"),
        ):
            builder.add_fact(Fact(template, {"value": action[field]}))
    for doc_id in set(documents):
        builder.add_check(Check("check if cap:document({value})", {"value": doc_id}))
    try:
        index = builder.build(token).authorize()
    except Exception:
        raise Refusal("capability_denied", 403) from None
    return "auto" if index in (0, 1) else "review"


def attenuate(encoded: str, public_key, *, maximum: int, action_digest: str | None = None) -> str:
    """Holder operation: only parent credential and public key, no issuer secret."""
    token = verify(encoded, public_key)
    block = BlockBuilder("check if req:action(\"order.create\"); "
                         "check if req:amount($n), $n <= {limit};", {"limit": maximum})
    if action_digest is not None:
        block.add_check(Check("check if req:action_digest({digest})", {"digest": action_digest}))
    return token.append(block).to_base64()
