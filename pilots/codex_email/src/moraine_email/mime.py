"""Prepare once; review and dispatch the same MIME bytes."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import SMTP
from email.utils import format_datetime
import hashlib
from typing import TypedDict

from .models import PilotError, address, header, identifier, text


class PreparedReply(TypedDict):
    mime_b64: str
    mime_sha256: str
    preview: dict


def prepare_reply(*, account, recipient, source, body_text, request_id) -> PreparedReply:
    sender, recipient = address(account), address(recipient)
    identifier(request_id)
    text(body_text, 16384, empty=True)
    subject = header(source["title"])
    body = body_text.replace("\r\n", "\n").replace("\r", "\n")
    if not body.endswith("\n"):
        body += "\n"
    msg = EmailMessage(policy=SMTP)
    msg["From"], msg["To"], msg["Subject"] = sender, recipient, subject
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg["Message-ID"] = f"<{request_id}@moraine.invalid>"
    msg["In-Reply-To"] = source["message_id"]
    msg["References"] = source["message_id"]
    msg.set_content(body, charset="utf-8", cte="quoted-printable")
    raw = msg.as_bytes()
    parsed = BytesParser(policy=SMTP).parsebytes(raw)
    rendered = parsed.get_content().replace("\r\n", "\n")
    if rendered != body or parsed.is_multipart():
        raise PilotError("mime_roundtrip_failed")
    preview = {
        "from": str(parsed["From"]), "to": [str(parsed["To"])], "cc": [], "bcc": [],
        "subject": str(parsed["Subject"]), "body_text": rendered, "attachments": [],
        "message_id": str(parsed["Message-ID"]), "in_reply_to": str(parsed["In-Reply-To"]),
        "references": str(parsed["References"]), "thread_id": source["thread_id"],
    }
    return {"mime_b64": base64.b64encode(raw).decode("ascii"),
            "mime_sha256": hashlib.sha256(raw).hexdigest(), "preview": preview}
