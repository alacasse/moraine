"""Exact public schemas; these establish types, never grant authority."""
from __future__ import annotations

import hashlib
import json
import re
import time


class Refusal(Exception):
    def __init__(self, reason: str, status: int = 400):
        self.reason, self.status = reason, status
        super().__init__(reason)


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def shape(value: object, keys: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise Refusal("invalid_fields")
    return value


def text(value: object, maximum: int = 256, empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not value and not empty):
        raise Refusal("invalid_string")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise Refusal("invalid_string") from None
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise Refusal("invalid_string")
    return value


def identifier(value: object) -> str:
    value = text(value, 128)
    if not re.fullmatch(r"[A-Za-z0-9_.:@-]+", value):
        raise Refusal("invalid_identifier")
    return value


def integer(value: object, minimum: int = 1) -> int:
    if type(value) is not int or not minimum <= value <= 2**53 - 1:
        raise Refusal("invalid_integer")
    return value


def strings(value: object, *, ids: bool = False) -> list[str]:
    if not isinstance(value, list) or len(value) > 64:
        raise Refusal("invalid_list")
    return [(identifier(item) if ids else text(item)) for item in value]


def grant_input(value: object) -> dict:
    g = shape(value, {"agent", "account", "expires_at", "recipients", "document_ids",
                      "merchants", "currency", "auto_limit_minor", "hard_limit_minor"})
    if g["agent"] != "agent:alice" or g["account"] != "alice":
        raise Refusal("grant_owner_forbidden", 403)
    integer(g["expires_at"])
    if g["expires_at"] <= time.time():
        raise Refusal("invalid_expiry")
    integer(g["auto_limit_minor"], 0)
    integer(g["hard_limit_minor"])
    if g["auto_limit_minor"] > g["hard_limit_minor"]:
        raise Refusal("invalid_limits")
    for key in ("recipients", "merchants"):
        strings(g[key])
    strings(g["document_ids"], ids=True)
    identifier(g["currency"])
    return g


def action_input(value: object) -> dict:
    if not isinstance(value, dict):
        raise Refusal("invalid_action")
    kind = value.get("type")
    common = {"type", "account"}
    if kind == "order.create":
        a = shape(value, common | {"merchant", "sku", "quantity", "amount_minor", "currency",
                                   "shipping_address_id", "recurring"})
        for key in ("merchant", "sku", "currency", "shipping_address_id"):
            text(a[key])
        integer(a["quantity"])
        integer(a["amount_minor"])
        if type(a["recurring"]) is not bool:
            raise Refusal("invalid_boolean")
    elif kind == "email.send":
        a = shape(value, common | {"to", "cc", "bcc", "subject", "body", "attachments"})
        for key in ("to", "cc", "bcc"):
            strings(a[key])
        if not a["to"] + a["cc"] + a["bcc"]:
            raise Refusal("no_recipient")
        text(a["subject"], 1024, empty=True)
        text(a["body"], 65536, empty=True)
        if not isinstance(a["attachments"], list) or len(a["attachments"]) > 32:
            raise Refusal("invalid_attachments")
        for attachment in a["attachments"]:
            shape(attachment, {"id", "version"})
            identifier(attachment["id"])
            integer(attachment["version"])
    elif kind == "document.read":
        a = shape(value, common | {"document_id"})
        identifier(a["document_id"])
    else:
        raise Refusal("unknown_action", 403)
    identifier(a["account"])
    # Round-trip detaches caller-owned mutable objects and establishes canonical JSON.
    return json.loads(canonical(a))


def submission_input(value: object) -> dict:
    s = shape(value, {"grant_id", "idempotency_key", "action", "capability"})
    identifier(s["grant_id"])
    text(s["idempotency_key"], 256)
    text(s["capability"], 32768)
    return {**s, "action": action_input(s["action"])}
