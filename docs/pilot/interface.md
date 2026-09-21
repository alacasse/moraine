# Local simulated pilot implementation contract

Scope: implemented local email pilot, Linux deployment preparation and the
separate local test console. Source paths below are relative to
`pilots/codex_email/`. See [architecture](../architecture.md) for the component
map, [current status](../status.md) for validation boundaries and
[Linux deployment](linux-deployment.md) for the installation still to qualify.
Historical worker assignments and deliveries are recorded in
[parallel workstreams](../plans/parallel-workstreams.md); they do not assign
ownership of future changes.

## Broker interface

`Broker(state_dir: Path, policy, provider, *, owner='human:owner', agent='agent:pilot', account='pilot@example.test', resource_sets=None)`.

All operations are synchronous and serialized by the broker; return dictionaries or raise `models.PilotError(reason, status=400)`. No HTTP tuples. Authentication happens in the transports. Actor strings passed to this trusted in-process interface are never taken from client payloads. The configured owner is the only human; the configured agent is the only grant target. `close()` closes the broker's storage; the launcher owns closing policy/provider.

Methods:

- `request_access(agent, resource_set_ref, idempotency_key)` -> durable access receipt.
- `get_access(agent, resource_set_ref)` -> latest own receipt/current grant, or absence; no provider IO.
- `list_access_requests(human)` -> latest 100 receipts for the configured identities.
- `review_access(human, request_id)` -> frozen scope, digest, nonce, review deadline.
- `decide_access(human, request_id, scope_digest, nonce, decision)` -> receipt after rejection or bounded capture/publication.
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

Input grant exact keys: `kind`, `agent`, `account_id`, `expires_at`, `resources`, plus `recipient` and `reply_to_ref` only for `kind=reply`. `kind=context_read` permits no reply proposal. Resources are synthetic captures supplied through the trusted human channel or fetched after an access decision, never supplied by an agent tool. A message has exact keys `resource_ref`, `provider_message_id`, `kind` (`message`), `version` (positive integer), `title`, `text`, `from_address`, `reply_address`, `message_id`, `thread_id`. A note has exact keys `resource_ref`, `kind` (`note`), `version`, `title`, `text`. For reply grants, `reply_to_ref` must select a message; `recipient` must match that message's normalized `reply_address`. Identities and stable provider message IDs are distinct from grant IDs and resource refs.

Bounds: 1–5 messages plus optional one note, text <=32 KiB each and <=128 KiB total, reply <=16 KiB, subject <=512 characters. Agent IDs, resource refs, provider message IDs and thread IDs use simple ASCII token syntax, <=128 characters; `message_id` instead uses the specific `<local@domain>` syntax and allows <=254 ASCII bytes. Resource `version` is an integer from 1 through `2**53-1`; idempotency key <=128 characters; expiry future and <=30 minutes. No files/URLs or attachments from callers. Grant resource input is copied and immutable.

Stored request states: `pending`, `processing`, `rejected`, `denied`, `accepted`, `failed`, `unknown`. Projection always includes request_id/state/reason. Internal `processing` is exposed as `unknown` with reason `unresolved_dispatch_intent`, without a snapshot. A `pending` projection includes action_digest/review_expires_at/preview only before review expiry; agent access additionally requires a matching policy revision and current authorization. Otherwise it can remain `pending` with only the safe receipt fields. The human owner can inspect the stored snapshot outside `processing`, including after review expiry. Terminal results are immutable; expired/revoked agent access returns only a safe receipt. Foreign request IDs are indistinguishable from absent ones. Known transient state never becomes a false accepted result.

Snapshot envelope: schema version, request_id, principal, account_id, grant_id, stable source key, context refs/versions/digests, prepared reply, policy_revision, prepared_at, review_expires_at. Digest is canonical SHA-256. Review max 300s; consent max 60s bounded by review and grant. OPA fail closed; guard after durable intent immediately before IO. Durable unresolved-intent/unknown barrier by account + provider_message_id applies to preexisting requests as well as new proposals and survives restart.

## Validation, MIME, policy and provider

### Synthetic access capture

`resource_sets` is trusted configuration, not an MCP input: at most eight public
names, each selecting 1–5 unique provider IDs in the configured account.
`request_access` accepts exactly `resource_set_ref` and `idempotency_key`;
`get_access` accepts exactly `resource_set_ref`. A request freezes owner, agent,
account, sorted IDs, public reference, read-only kind, grant TTL and request
deadline. The scope digest covers that entire object. No email metadata or
body is returned before capture and authorization.

SQLite schema version 2 adds `access_requests`, separate from reply requests
and decisions. Version 1 is refused without migration. A fresh runtime is
required for the first run; version 2 supports subsequent restarts.

Decision states: `pending`, `rejected`, `expired`, `approved`. Retrieval states:
`not_started`, `fetching`, `ready`, `failed`. Approval and `fetching` are persisted
atomically before IO. The human reviews the scope, digest and nonce; the nonce
is consumed with the decision. Request lifetime is 30 minutes; review lifetime
is at most five minutes, bounded by the request. Activation must finish within
both deadlines. Grant lifetime is 30 minutes from publication.

Same agent/key/input returns the same request. A changed public reference under
an existing key is `idempotency_conflict`. A different key for an already pending
selection or active access receives `access_already_exists` and is not consumed.
The client should consult `get_access`; a later explicit request using that
previously refused key can create a new request after rejection/expiry.
Catalogue changes do not mutate a frozen request or silently enlarge a grant.

`provider.fetch_selected(message_ids)` returns a list of synthetic messages.
The HTTP adapter uses one POST `/messages` with `{message_ids}`, receives
`{messages}`, and enforces a four-second total timeout, 256 KiB response cap,
loopback origin, no redirects, no environment proxies and no retries.
Message exact keys: `provider_message_id`, `title`, `text`, `from_address`,
`reply_address`, `message_id`, `thread_id`. Missing, additional, duplicate,
oversized or invalid messages reject the whole capture. Existing field/text
bounds still apply. The broker assigns local refs, version 1 and resource
digests. Published metadata adds `source_digest` for the canonical provider
object, independently comparable with the provider's `reads.jsonl`.

The broker checks live OPA read policy and activation deadlines before IO and
again before publication, including after SQLite BEGIN. No database transaction
is held during HTTP. The grant, all resources and `ready` are committed together.
Expired activation yields `approved/failed` with `activation_expired`; other
capture errors yield `retrieval_failed`, without upstream error text. An
interrupted capture becomes `retrieval_interrupted` on restart, with no retry.

Receipts expose request ID, public reference, decision, retrieval, fixed reason
and current access state (`none`, `active`, `revoked`, `expired`, `unavailable`).
Only active access exposes `grant_id`; a published grant also exposes its
deadline. Terminal retrieval history is preserved after revocation/expiry.
Lookup never fetches provider data. Normal read operations still recheck policy
and current grant validity. This is a synthetic JSON exercise, not the proposed
real MIME inspection/publication pipeline.

### Existing reply path

`models`: `PilotError`, `canonical(value)`, `digest(value)`, `validate_grant(body)` returns normalized deep-copied dict, `validate_proposal(body)` returns validated copy, `safe_text(value)` for inert terminal display.

`mime.prepare_reply(*, account, recipient, source, body_text, request_id)` returns a JSON-compatible PreparedReply dictionary with `mime_b64`, `mime_sha256`, `preview`. Preview fields: `from`, `to`, `cc`, `bcc`, `subject`, `body_text`, `attachments`, `message_id`, `in_reply_to`, `references`, `thread_id`. Built with EmailMessage once, CRLF normalized before review; no caller-supplied raw MIME.

`provider.send_prepared(prepared: dict, execution_id: str)` returns `{state: 'accepted'|'failed'|'unknown', reason: str, result: dict}`. Network exceptions must conservatively become unknown in broker. Adapter is synchronous, bounded, no retries, loopback synthetic provider only, result contains no secrets. The independent provider records attempts, MIME bytes and effects separately and has NO deduplication. Modes: normal, reject_before, accept_then_disconnect, malformed_success. Test-only control never exposed by MCP.

Core owns the exact OPA facts shape. Policy provides `OPA(binary: Path, policy_dir: Path | None = None, *, runtime_dir: Path | None = None)`, `.revision`, `.decide(facts)` and `.close()`. A configured runtime directory must be private and service-owned. The OPA checksum lock copied from experiment B remains unchanged.

## Transports

Official MCP Python SDK, Streamable HTTP, loopback bearer auth. Exactly request_access, get_access, list_context, read_context, propose_reply, get_request. Reject unknown input keys at protocol boundary; do not let SDK signature filtering silently discard authority fields. Bind authenticated agent from trusted configuration. Return safe errors, no exception content. Use bounded request bodies and Origin validation; no human routes on the broker HTTP listener.

Human socket uses SO_PEERCRED and configured allowed UID, no claimed human field. Strict operation whitelist maps to broker methods; bounded newline JSON protocol, duplicate JSON keys rejected, no interpolation. CLI interactive review displays exact snapshot inertly and sends matching digest+nonce; explicit refusal supported. Fixtures may use current UID but must never claim OS isolation. Main launcher accepts paths to token/config files (not token values), state dir, OPA binary, simulated provider URL/token file, human UID/socket and loopback port; no test hooks in production interface.

The launcher also accepts optional `--resource-sets` (a synthetic JSON catalogue of at most eight public names, each mapping to 1–5 unique IDs), `--human-socket-gid` and `--opa-runtime-dir`. The human socket stays service-owned, with mode 0600 by default or 0660 for a group held by the service; the group permits connection, while SO_PEERCRED still authorizes the exact human UID. A stable lock protects endpoint creation and stale-socket recovery. The launcher watches OPA termination and retires the broker on failure; systemd group cleanup after a broker SIGKILL remains a separate installation qualification.

## Local operator console

The separate `lab/` package owns its HTTP operator console and subprocess harness.
It uses the actual MCP and human socket transports; it does not add agent tools
or change broker authority. Its operator token permits simulating human actions
only within this test laboratory. See the [local lab guide](local-lab.md) for
its endpoints, scenarios, private runtime and independent delivery evidence.
