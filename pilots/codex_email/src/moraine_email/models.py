"""Strict, provider-independent inputs for the bounded email pilot."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import time
import unicodedata


class PilotError(Exception):
    def __init__(self, reason: str, status: int = 400):
        super().__init__(reason)
        self.reason = reason
        self.status = status


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def exact(value, fields):
    if type(value) is not dict or set(value) != set(fields.split()):
        raise PilotError("invalid_fields")


def text(value, limit, *, empty=False):
    if type(value) is not str or (not value and not empty):
        raise PilotError("invalid_text")
    try:
        if len(value.encode("utf-8")) > limit:
            raise PilotError("text_too_large")
    except UnicodeError as error:
        raise PilotError("invalid_unicode") from error
    return value


def identifier(value):
    text(value, 128)
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", value):
        raise PilotError("invalid_identifier")
    return value


def address(value):
    text(value, 254)
    # Deliberately a small ASCII addr-spec subset: no display names, lists,
    # comments, quoted local parts, IDNs or local delivery addresses.
    atom = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
    label = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    if not re.fullmatch(rf"{atom}(?:\.{atom})*@{label}(?:\.{label})+", value):
        raise PilotError("invalid_address")
    local, domain = value.rsplit("@", 1)
    if len(local) > 64:
        raise PilotError("invalid_address")
    return local + "@" + domain.lower()


def header(value, limit=512):
    text(value, limit * 4, empty=True)
    if len(value) > limit or any(unicodedata.category(c).startswith("C") or c in "\u2028\u2029" for c in value):
        raise PilotError("invalid_header")
    return value


def validate_grant(body):
    exact(body, "agent account_id expires_at recipient reply_to_ref resources")
    result = copy.deepcopy(body)
    identifier(result["agent"])
    result["account_id"] = address(result["account_id"])
    result["recipient"] = address(result["recipient"])
    identifier(result["reply_to_ref"])
    expiry = result["expires_at"]
    now = time.time()
    if type(expiry) not in (int, float) or not now < expiry <= now + 1800:
        raise PilotError("invalid_expiry")
    resources = result["resources"]
    if type(resources) is not list or not 1 <= len(resources) <= 6:
        raise PilotError("invalid_selection")
    seen, messages, notes, total = set(), 0, 0, 0
    for resource in resources:
        if type(resource) is not dict:
            raise PilotError("invalid_resource")
        common = "resource_ref kind version title text"
        if resource.get("kind") == "message":
            exact(resource, common + " provider_message_id from_address reply_address message_id thread_id")
            messages += 1
            identifier(resource["provider_message_id"])
            identifier(resource["thread_id"])
            resource["from_address"] = address(resource["from_address"])
            resource["reply_address"] = address(resource["reply_address"])
            mid = text(resource["message_id"], 254)
            if not re.fullmatch(r"<[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+>", mid):
                raise PilotError("invalid_message_id")
        elif resource.get("kind") == "note":
            exact(resource, common)
            notes += 1
        else:
            raise PilotError("invalid_resource_kind")
        ref = identifier(resource["resource_ref"])
        if ref in seen:
            raise PilotError("duplicate_resource")
        seen.add(ref)
        if type(resource["version"]) is not int or not 1 <= resource["version"] <= 2**53-1:
            raise PilotError("invalid_version")
        header(resource["title"])
        text(resource["text"], 32768, empty=True)
        total += len(resource["text"].encode("utf-8"))
    if not 1 <= messages <= 5 or notes > 1 or total > 131072:
        raise PilotError("selection_too_large")
    source = next((r for r in resources if r["resource_ref"] == result["reply_to_ref"]), None)
    if not source or source["kind"] != "message" or result["recipient"] != source["reply_address"]:
        raise PilotError("invalid_reply_target")
    return result


def validate_proposal(body):
    exact(body, "grant_id idempotency_key reply_to_ref body_text")
    result = copy.deepcopy(body)
    identifier(result["grant_id"])
    identifier(result["idempotency_key"])
    identifier(result["reply_to_ref"])
    text(result["body_text"], 16384, empty=True)
    return result


def safe_text(value):
    """Inert terminal rendering, preserving lines but exposing control characters."""
    output = []
    for c in str(value):
        if c == "\\":
            output.append("\\\\")
        elif c != "\n" and (unicodedata.category(c).startswith("C") or c in "\u2028\u2029"):
            output.append(f"\\u{ord(c):04x}")
        else:
            output.append(c)
    return "".join(output)


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise PilotError("duplicate_json_key")
            out[key] = value
        return out
    def constant(_):
        raise PilotError("invalid_json_constant")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise PilotError("invalid_json") from error
