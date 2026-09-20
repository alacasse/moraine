# Local simulated pilot implementation contract

Scope: plan steps 1–2 only. No Gmail/OAuth, system installation, real account, Codex configuration or real send. Preserve `experiments/` unchanged. This file fixes the collaboration interface; README will document the delivered executable interface.

## Ownership

- Core worker: `src/moraine_email/broker.py`, `store.py` if needed, `policy.py`, `policy/`, `tests/test_lifecycle.py`, `tests/test_policy.py`.
- Transport worker: `src/moraine_email/mcp_server.py`, `human_server.py`, `human_cli.py`, `server.py`, `tests/test_mcp.py`, `tests/test_human_review.py`.
- Coordinator: models/MIME, simulated adapter and independent provider fixture, packaging, shared test fixtures, integration, evidence and documentation.

Workers are not alone: do not revert others' changes, do not edit files owned by another worker without coordination, and do not initialize/commit Git or modify experimental files.

## Broker interface

`Broker(state_dir: Path, policy, provider, *, owner='human:owner', agent='agent:pilot', account='pilot@example.test')`.

All operations are synchronous and serialized by the broker; return dictionaries or raise `models.PilotError(reason, status=400)`. No HTTP tuples. Authentication happens in the transports. Actor strings passed to this trusted in-process interface are never taken from client payloads. The configured owner is the only human; the configured agent is the only grant target. `close()` closes the broker's storage; the launcher owns closing policy/provider.

Methods:

- `create_grant(human, body)` -> `{grant_id, expires_at}`.
- `revoke_grant(human, grant_id)` -> `{grant_id, state:'revoked'}`.
- `list_context(agent, grant_id)` -> selected metadata only.
- `read_context(agent, grant_id, resource_ref, version)` -> selected text, version and digest.
- `propose_reply(agent, body)` -> request projection.
- `get_request(actor, request_id)` -> request projection; human can inspect full snapshot.
- `review(human, request_id)` -> `{request_id,action_digest,nonce,review_expires_at,snapshot}`.
- `decide_review(human, request_id, action_digest, nonce, decision)` where decision is `approve` or `reject` -> projection. Consume nonce atomically with decision.
- `resolve_unknown(human, request_id, acknowledge_duplicate_risk)` -> receipt; only true permits resolution, old outcome unchanged.

Input proposal exact keys: `grant_id`, `idempotency_key`, `reply_to_ref`, `body_text`.

Input grant exact keys: `agent`, `account_id`, `expires_at`, `recipient`, `reply_to_ref`, `resources`. Resources are captured synthetic content supplied through the trusted human channel, never an agent tool. A message has exact keys `resource_ref`, `provider_message_id`, `kind` (`message`), `version` (positive integer), `title`, `text`, `from_address`, `reply_address`, `message_id`, `thread_id`. A note has exact keys `resource_ref`, `kind` (`note`), `version`, `title`, `text`. `reply_to_ref` must select a message; `recipient` must match that message's normalized `reply_address`. Identities and stable provider message IDs are distinct from grant IDs and resource refs.

Bounds: 1–5 messages plus optional one note, text <=32 KiB each and <=128 KiB total, reply <=16 KiB, subject <=512 characters, IDs <=128 ASCII characters (resource refs and provider IDs simple token syntax), idempotency key <=128 characters; expiry future and <=30 minutes. No files/URLs or attachments from callers. Grant resource input is copied and immutable.

Request states: `pending`, `processing`, `rejected`, `denied`, `accepted`, `failed`, `unknown`. Projection always includes request_id/state/reason. Pending also has action_digest/review_expires_at/preview. Terminal results are immutable; expired/revoked agent access returns only a safe receipt. Foreign request IDs indistinguishable from absent ones. Known transient state never becomes a false accepted result.

Snapshot envelope: schema version, request_id, principal, account_id, grant_id, stable source key, context refs/versions/digests, prepared reply, policy_revision, prepared_at, review_expires_at. Digest is canonical SHA-256. Review max 300s; consent max 60s bounded by review and grant. OPA fail closed; guard after durable intent immediately before IO. Durable unresolved-intent/unknown barrier by account + provider_message_id applies to preexisting requests as well as new proposals and survives restart.

## Coordinator-owned functions and provider

`models`: `PilotError`, `canonical(value)`, `digest(value)`, `validate_grant(body)` returns normalized deep-copied dict, `validate_proposal(body)` returns validated copy, `safe_text(value)` for inert terminal display.

`mime.prepare_reply(*, account, recipient, source, body_text, request_id)` returns a JSON-compatible PreparedReply dictionary with `mime_b64`, `mime_sha256`, `preview`. Preview fields: `from`, `to`, `cc`, `bcc`, `subject`, `body_text`, `attachments`, `message_id`, `in_reply_to`, `references`, `thread_id`. Built with EmailMessage once, CRLF normalized before review; no caller-supplied raw MIME.

`provider.send_prepared(prepared: dict, execution_id: str)` returns `{state: 'accepted'|'failed'|'unknown', reason: str, result: dict}`. Network exceptions must conservatively become unknown in broker. Adapter is synchronous, bounded, no retries, loopback synthetic provider only, result contains no secrets. The independent provider records attempts, MIME bytes and effects separately and has NO deduplication. Modes: normal, reject_before, accept_then_disconnect. Test-only control never exposed by MCP.

Core owns the exact OPA facts shape. Policy constructor to provide `OPA(binary: Path, policy_dir: Path | None = None)`, `.revision`, `.decide(facts)` and `.close()`. Copy OPA checksum lock from B; coordinator supplies a verified local copy of the binary without changing B.

## Transports

Official MCP Python SDK, Streamable HTTP, loopback bearer auth. Exactly list_context, read_context, propose_reply, get_request. Reject unknown input keys at protocol boundary; do not let SDK signature filtering silently discard authority fields. Bind authenticated agent from trusted configuration. Return safe errors, no exception content. Use bounded request bodies and Origin validation; no human routes on HTTP.

Human socket uses SO_PEERCRED and configured allowed UID, no claimed human field. Strict operation whitelist maps to broker methods; bounded newline JSON protocol, duplicate JSON keys rejected, no interpolation. CLI interactive review displays exact snapshot inertly and sends matching digest+nonce; explicit refusal supported. Fixtures may use current UID but must never claim OS isolation. Main launcher accepts paths to token/config files (not token values), state dir, OPA binary, simulated provider URL/token file, human UID/socket and loopback port; no test hooks in production interface.
