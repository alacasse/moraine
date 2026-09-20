"""Strict input shapes. These validate proposals, never establish identity."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

MAX_LONG = 2**63 - 1
Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:@-]*$")]
Positive = Annotated[int, Field(gt=0, le=MAX_LONG)]
Nonnegative = Annotated[int, Field(ge=0, le=MAX_LONG)]
Address = Annotated[str, Field(min_length=3, max_length=254, pattern=r"^[^\s@,;<>]+@[^\s@,;<>]+$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Principal(StrictModel):
    """Host-created identity: callers must authenticate before constructing it."""
    kind: Literal["agent", "human"]
    id: Identifier
    account: Identifier


class Grant(StrictModel):
    agent: Identifier
    account: Identifier
    expires_at: Positive
    recipients: Annotated[list[Address], Field(max_length=100)]
    document_ids: Annotated[list[Identifier], Field(max_length=100)]
    merchants: Annotated[list[Identifier], Field(max_length=100)]
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    auto_limit_minor: Nonnegative
    hard_limit_minor: Nonnegative

    @model_validator(mode="after")
    def limits(self):
        if self.auto_limit_minor > self.hard_limit_minor:
            raise ValueError("invalid limits")
        return self


class Attachment(StrictModel):
    id: Identifier
    version: Positive


class Email(StrictModel):
    type: Literal["email.send"]
    account: Identifier
    to: Annotated[list[Address], Field(max_length=100)]
    cc: Annotated[list[Address], Field(max_length=100)]
    bcc: Annotated[list[Address], Field(max_length=100)]
    subject: Annotated[str, Field(max_length=1000)]
    body: Annotated[str, Field(max_length=100000)]
    attachments: Annotated[list[Attachment], Field(max_length=20)]


class Order(StrictModel):
    type: Literal["order.create"]
    account: Identifier
    merchant: Identifier
    sku: Identifier
    quantity: Positive
    amount_minor: Positive
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    shipping_address_id: Identifier
    recurring: bool


class Read(StrictModel):
    type: Literal["document.read"]
    account: Identifier
    document_id: Identifier


Action = Annotated[Email | Order | Read, Field(discriminator="type")]
ACTION = TypeAdapter(Action)


class Submission(StrictModel):
    grant_id: Identifier
    idempotency_key: Annotated[str, Field(min_length=1, max_length=128)]
    action: Action


class Approval(StrictModel):
    action_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Empty(StrictModel):
    pass
