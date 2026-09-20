# Three approaches to delegated execution — experiment contract

Date: 2026-09-20. Authorized by the user: three independent planning teams, followed by development teams, independent review, comparison, and lessons. This supersedes the earlier no-code constraint for these experiments only. All implementations are experimental, not production security products. No publication, real account credentials, email delivery, payment, or deployment to external infrastructure.

Historical experiment contract. The workflow and permissions below describe
that completed mission, not a new assignment. Its technical benchmark remains
the reference for the three prototypes. See the [comparison](COMPARISON.md) for
delivered results and [current status](../status.md) for subsequent work.

## Questions and distinct approaches

1. **A, embedded module:** integrate an existing Python authorization library (prefer apparitor) and existing policy engine inside a trusted tool backend. Minimize the developer-facing interface; the benchmark HTTP server is a host example, not the product. Determine what lifecycle glue remains.
2. **B, independent broker:** build a small persistent execution service using the real OPA runtime/Rego, with server-side grants and approval state. Optimize an independently deployable interface. No custom policy DSL.
3. **C, attenuated capabilities:** use real Biscuit Python/Rust credentials and attenuation, verified by the trusted executor. Demonstrate which authority can travel in signed credentials, and which revocation/approval/replay state still cannot disappear. No homemade signatures or token substitutes.

Two domains: email delivery and order creation, plus selected document reads to test context disclosure. Plans may challenge their assigned approach but must implement an honest experiment or substantiate a concrete blocker. Do not replace a missing dependency with a fake implementation and claim equivalence.

## Original ownership and workflow

Root owns this contract, `experiments/common/`, campaign runner, independent black-box tests, final comparison, and evidence records. Planners own only their plan under `docs/experiments/plans/`. Developers own one of `experiments/a_embedded/`, `experiments/b_broker/`, `experiments/c_capability/` and its implementation note. All teams share a directory: never revert another team's work. Do not edit AGENTS.md/CLAUDE.md, initialize Git, commit, push, or touch other repositories. No functional Git repository was available during this original mission; its review baselines were file manifests and archived experiment snapshots.

Each planner hands off: interface/invariants; dependency versions and acquisition path; architecture and trust assumptions; persistent state; execution/recovery model; proposed file ownership; local tests; risks and expected learning. Developers must run real dependencies, report deviations, provide one-command startup/tests, lock versions, and write what is inherited versus custom. Independent reviewers assess implementation/spec/security and maintainability/test confidence after development. Fix material findings and rerun relevant tests; retain pre-fix findings as evidence.

## Trust model and evidence scope

Attacker controls requests and agent-facing credentials for agent Alice or Bob, can fabricate body identity fields and approval claims, and can call every advertised endpoint directly. Human authentication, grant store, policy engine, executor, and fake provider are trusted. Provider credentials are never returned to the agent.

Local tests run as processes under the same OS user. They can establish HTTP authentication, authorization, snapshot/replay semantics, and downstream side effects. They do NOT prove containment of arbitrary code with that same user's filesystem/process access, kernel isolation, credential-vault security, or production OAuth correctness. Document deployment separation needed for that stronger claim. Bind servers to loopback; fixture bearer tokens are synthetic and must never be described as production identity infrastructure.

Use actual wall-clock UTC epoch seconds from the trusted host. No agent-supplied time, owner, policy outcome, document classification, or approval boolean can establish authority. All protected endpoints fail closed on missing/malformed credentials. Human and agent capabilities remain separate. Unrecognized input fields must be rejected or demonstrably unable to affect authority; approval endpoint specifically rejects action replacement.

## Common benchmark interface, version 1

Every approach supplies executable `run.sh` in its owned directory. It accepts:

`--port N --state-dir PATH --provider-url URL --provider-token TOKEN --agent-token TOKEN --other-agent-token TOKEN --human-token TOKEN`

The harness generates the fixture tokens. Mappings: agent token = `agent:alice`; other-agent token = `agent:bob`; human token = `human:alice`. Authorization header: `Bearer <token>`. State survives restart using the same directory. `/health` returns HTTP 200 when all required local dependencies are ready. Startup must not mutate other approaches. Use approach-local virtual environments/caches and no global package installation.

### Grant creation and revocation

`POST /grants` requires human credentials. JSON:

```json
{"agent":"agent:alice","account":"alice","expires_at":2000000000,"recipients":["trusted@example.test"],"document_ids":["public-note"],"merchants":["shop.test"],"currency":"CAD","auto_limit_minor":1000,"hard_limit_minor":5000}
```

Return HTTP 201 or 200 and `{"grant_id":"..."}`. C additionally returns `"capability":"..."`, which the harness carries in submissions. Human authority is fixture-limited to account Alice and agent Alice; creating grants for a different account or agent must refuse. Bad limits/expiry/types refuse.

`POST /grants/{grant_id}/revoke` requires human credentials, returns success, and invalidates future execution including pending approvals. Nonexistent or foreign identifiers must not expose protected data.

### Actions and submissions

`POST /requests` requires agent credentials. JSON: `{"grant_id":"...","idempotency_key":"...","action":{...}}`; C also requires `capability` returned from grant creation. Grant must belong to authenticated agent and account. A model-provided principal/role is never authoritative.

Action variants (exact types):

```json
{"type":"email.send","account":"alice","to":["trusted@example.test"],"cc":[],"bcc":[],"subject":"Question","body":"Hello","attachments":[{"id":"public-note","version":1}]}
{"type":"order.create","account":"alice","merchant":"shop.test","sku":"paper","quantity":1,"amount_minor":500,"currency":"CAD","shipping_address_id":"home","recurring":false}
{"type":"document.read","account":"alice","document_id":"public-note"}
```

Email: every recipient in To/Cc/Bcc must be in the grant; at least one recipient; attachment IDs must be permitted, version must match trusted provider metadata. Every permitted send requires human approval. Snapshot the exact body/recipients and attachment content at submission; store and execute the same values. No MIME/raw-HTTP escape hatch.

Order: merchant and currency must match grant; positive integer quantity and amount (booleans, floats, strings, negatives rejected), amount is total in minor units, only `home` destination, no recurring orders. Up to auto limit executes automatically; above auto up to hard limit requires review; above hard limit denies. This fixture tests per-operation caps, NOT aggregate budget conservation; report this exclusion. Unknown action types deny. No assumption of provider quotation integrity: prices are synthetic request inputs in this fixture, an explicit real-commerce integration gap.

Document read: only grant-selected IDs can reach the provider read endpoint; returned content is data, never instructions/authority. Unauthorized reads must produce no provider document access record.

Response is a JSON object with `request_id`, `state`, and `reason` (safe machine-readable reason). States: `denied`, `pending`, `executed`, `failed`, `unknown`. `pending` includes `action_digest`. Executed reads include `result` with selected content. Provider errors are never reported as execution success. Protocol errors may return 4xx; semantic denials can be 200/403. A repeated identical submission with same agent/idempotency key returns the existing request/outcome without duplicate effect; changed payload using that key returns 409. Never use a caller idempotency key as authority or as a cross-agent ownership key.

`GET /requests/{request_id}` is available only to the owning agent or the fixture human, returning safe state and the human-review snapshot when appropriate. No provider tokens or capability signing keys in response/audit. Agent Bob cannot read Alice's requests.

### Approval

`POST /requests/{request_id}/approve` requires human credentials and body `{"action_digest":"..."}`. Digest must match stored pending snapshot, authenticated actor/grant bindings remain valid, and expiry/revocation/current policy are rechecked before execution. Return resulting request state. Reject body-supplied action edits, wrong digests, forged agent approvals and terminal/hard-denied approvals. Concurrent duplicate approval cannot cause duplicate effects. Approval is short-lived (implementation must document a maximum age); request/approval state survives restart. The harness also checks grant expiration while pending.

### Shared fake provider (root-owned)

Runs separately on loopback, SQLite state, header `Authorization: Bearer <provider-token>` on all data endpoints. It is a fixture for observable effects, not a model of Gmail's exact API.

- `GET /documents/{id}` returns `{"id":"public-note","version":1,"content":"Public fixture note","classification":"public"}` or `tax-return` (private fixture). Each authorized provider read is recorded; implementations must reject disallowed IDs BEFORE requesting it. Provider itself does not implement agent task grants.
- `POST /effects` takes `{"execution_id":"...","action":{...}}`. It records the exact submitted normalized action and returns `{"effect_id":"...","execution_id":"..."}`. Durable uniqueness by execution ID; different action with existing ID yields 409. Prepared email attachments must contain `id`, `version`, and `content` resolved from the provider; changing provider content after approval request must never silently substitute new bytes.
- `GET /effects` returns `{"effects":[...]}`. `GET /reads` returns `{"reads":[...]}` for harness verification.
- Root-only test control, also requiring provider token: `POST /control` accepts mode `normal`, `reject_before`, or `accept_then_disconnect`, and optional document mutation `{"document":{"id":"public-note","version":2,"content":"Changed fixture"}}`. Failure mode is used on the next `/effects` call then returns to normal. `reject_before` returns 503 without effect. `accept_then_disconnect` persists effect then closes the connection before response. A connection loss is an unknown outcome; either reconcile/retry with the SAME provider execution ID or leave unknown and do not blindly duplicate. No exactly-once claim about providers that lack this fixture's idempotency.

## Common evidence and evaluation

Root harness will evaluate positive email/order/read paths, cross-agent ownership, unapproved recipients including BCC, denied reads, forged identity and approval, changed payload/digest, expired/revoked grants on resume, duplicate submissions/approvals, concurrent approvals, restart while pending, provider failure/ambiguous completion, direct-provider access, and protocol malformed input. It will inspect effects/reads, not only response decisions.

Each approach adds honest local tests for its distinguishing claim: A real library integration and protected host assumptions; B real Rego/OPA policy errors and dependency failure; C real attenuation/tamper checks, audience/actor/action binding, and offline-vs-online revocation limits. Record all run commands and counts, actual dependency versions, limitations, custom-code responsibilities, startup/integration steps, and elapsed time if measured. No fabricated benchmarks. Do not optimize for a line-count score.

Comparison dimensions: common behavior; architectural trust assumptions; inherited vs custom behavior; integration friction; persistent/distributed state; failure/recovery clarity; extension to second domain; maintenance surface; contribution opportunity. Passing the fixture is evidence for only these cases, not a production security certification or proof of developer demand.
