# B — independently deployed execution broker with OPA

Status: development handoff, plan only. Date: 2026-09-20. Governing interface: [experiment contract](../EXPERIMENT.md). No implementation, installation, or execution evidence is claimed here.

## Experiment and module seam

Build one autonomous, credential-holding broker module. Its interface is the contract's authenticated HTTP operations plus `run.sh`; callers never evaluate Rego, load grants, resume a callback, or call the provider. A separately running, real OPA process evaluates the broker's Rego. SQLite contains the grants, immutable review snapshots, approval records, and execution records. This is the experiment's independently deployable module, not an embedded Python SDK and not a signed transferable capability.

The intended depth is that the HTTP caller learns one submission/review protocol while authentication, authorization, persistence, deduplication, snapshots, execution and recovery remain local to the broker implementation. Deleting this module would move those responsibilities into every trusted tool backend. Do not add a generic policy-engine interface, plugin registry, alternate persistence adapter, message queue or distributed worker framework: this experiment has one actual implementation of each.

The interesting question is how much machinery remains after OPA owns policy evaluation. Hypothesis: OPA substantially improves policy locality and testability, but does not supply trusted identity, grants, consent, transactions or external-effect recovery. The second action domain must reuse the same execution lifecycle and change only action validation/preparation and Rego rules.

## Exact external interface

Implement the common contract unchanged, with `Authorization: Bearer <fixture-token>` required on every operation except `/health`. The harness's three tokens must be nonempty and pairwise distinct; fail startup otherwise. Map tokens to principals in trusted startup configuration; never merge identity from JSON. Use constant-time token comparison. Do not print command arguments, tokens, provider headers or complete HTTP request bodies.

| Operation | Additional implementation decision |
| --- | --- |
| `POST /grants` | Human Alice only; exactly the documented fields, account `alice`, agent `agent:alice`. Return `201 {grant_id}`. IDs are random UUIDs. A grant is immutable except revocation. |
| `POST /grants/{id}/revoke` | Human Alice only; persist revocation and invalidate pending requests atomically. Revoking an owned already-revoked grant is successful. Foreign/nonexistent identifiers have the same `404` result. |
| `POST /requests` | Agent only; exactly `grant_id`, `idempotency_key`, `action`. No capability/token/owner/approval fields. Use `(authenticated_agent, idempotency_key)` as unique lookup key. Same normalized input returns the stored outcome; changed input returns `409`. |
| `GET /requests/{id}` | Owning agent or human owner only. Foreign/nonexistent requests produce indistinguishable `404`. Pending response contains digest, prepared snapshot and snapshot expiry; executed reads contain the stored selected document result. |
| `POST /requests/{id}/approve` | Human Alice only; body contains exactly `action_digest`. `409` for wrong digest or terminal state; include the safe existing state for an owned terminal request. A duplicate cannot dispatch again. Never accept action replacement. |
| `GET /health` | `200` only after storage recovery and authenticated OPA health plus a valid decision probe pass; otherwise `503`. Return a small status object without secrets or paths. |

All non-protocol request outcomes contain `request_id`, a contract state, and a fixed machine-readable reason. Semantic authorization denials use HTTP 200 with `state: denied`; malformed requests use 400, authentication failures 401, wrong credential class 403, conflicts 409, and dependency failure before request creation 503. Never include arbitrary OPA/provider exception text in external responses. Unknown routes/methods do not expose generic proxying or administrative endpoints.

Reject duplicate JSON keys, non-object bodies, unknown fields at every nesting level, nonfinite JSON numbers and invalid UTF-8. Reject booleans where an integer is required: use exact integer checks rather than Python's `isinstance(value, int)` alone. Set documented finite limits, sufficient for the fixture: 256 KiB request bodies, 100 recipients, 20 attachments, 1,000-character scalar identifiers, 128-character idempotency keys, numeric values no greater than `2^53-1`. Reject invalid content lengths and unsupported transfer encodings rather than implementing a partial chunked decoder. These bounds are transport/resource limits, not new authority rules.

The three action shapes, allowed accounts, recipient union including BCC, attachment versions, merchant/currency checks, `home` destination, no recurrence, thresholds and permitted document IDs are exactly those in the common contract. Normalize only object-key order for hashing; preserve recipient/attachment order, strings and every supplied action value. Document content is data even when it contains imperative text. No raw MIME, arbitrary URL, raw HTTP or arbitrary callable interface exists.

## Dependencies and acquisition

Host facts observed during planning: Linux x86_64, CPython **3.14.7**, SQLite **3.51.2**, uv **0.11.6**, global pytest **8.4.2**. The global pytest is not a reproducibility pin and must not be modified.

| Dependency | Pin and purpose | Acquisition |
| --- | --- | --- |
| CPython | `3.14.7` host runtime; standard library JSON, hashing, HTTP listener, SQLite, process management and locking | Use the available executable; record `sys.version` and `sqlite3.sqlite_version` in evidence. Fail clearly for an unsupported interpreter. |
| OPA | **1.9.0**, genuine standalone runtime, Rego v1 | Official [versioned release](https://github.com/open-policy-agent/opa/releases/tag/v1.9.0), Linux x86_64 asset `opa_linux_amd64_static`; do not use `latest`. |
| HTTPX | **0.28.1**, provider HTTP and OPA Unix-socket transport | [Maintainer-published package](https://pypi.org/project/httpx/0.28.1/), approach-local uv project and frozen lock. |
| pytest | **9.0.2**, local test runner with declared Python 3.14 support | [Maintainer-published release](https://pypi.org/project/pytest/9.0.2/), local development dependency; lock transitive packages. |

OPA 1.9.0 is a verified, deliberately fixed experiment version; this plan does not claim it is the latest release or recommend it for production. Obtain the binary and matching `opa_linux_amd64_static.sha256` from `https://github.com/open-policy-agent/opa/releases/download/v1.9.0/`. Planning confirmed the release page and checksum asset redirect, but the web reader could not retrieve the checksum bytes. The developer must acquire those bytes, verify the actual binary, record the exact SHA-256 in `dependencies.lock.json`, and verify that pinned checksum on every startup. Do not fabricate the checksum or silently replace this version. Report an actual acquisition blocker if the official artifact cannot be fetched; no Python evaluator or fake OPA fallback is acceptable.

Keep the binary under `experiments/b_broker/.tools/opa-1.9.0/`, uv cache under `.cache/uv/`, virtual environment under `.venv/`, and lockfiles within this approach. Use uv with its cache directory explicitly set and interpreter auto-download disabled. `run.sh` may perform the first verified local bootstrap; subsequent startup uses the frozen files. Do not install globally or require Docker. The static binary avoids making Go compilation a prerequisite.

## Process topology and OPA lifecycle

```text
agent/human fixture HTTP clients
              |
     broker listener on 127.0.0.1
              |
  trusted identity -> durable lifecycle -> provider HTTP
              |                |
         SQLite state       real OPA child
                            private Unix socket
```

Use a small standard-library `ThreadingHTTPServer` listener, explicitly described as an experiment transport. All stateful broker operations enter one process-wide reentrant lock; no claim of parallel throughput. A process-lifetime `flock` on the selected state directory rejects a second broker process before it opens state. HTTP handler threads allow health/shutdown handling and realistic simultaneous callers, while the lifecycle lock supplies an intentionally simple ordering model.

The launcher owns the OPA child. Create a short temporary directory under `/tmp` with mode 0700 for its socket, avoiding the Unix socket path-length limit with arbitrary harness state-directory paths. Start OPA with explicit local policy files and a generated, private auth-data file:

```sh
opa run --server --addr "unix://$OPA_SOCKET" \
  --authentication=token --authorization=basic --disable-telemetry \
  --log-level=error policy/broker.rego policy/system_authz.rego "$OPA_AUTH_DATA"
```

The variables above describe internal launcher values, not additional user requirements. Launch using an argument list, not a shell string. Generate a random OPA-only bearer token at startup, distinct from every harness token. The Rego `system.authz` policy permits only that identity's `GET /health` and `POST /v1/data/broker/decision`; deny all other routes, including policy/data writes, compilation, config and dumps. Never give clients this token or return it through health/debug output. OPA otherwise starts with authentication and authorization disabled, so this is a required configuration, not an optional hardening step. [OPA security configuration](https://www.openpolicyagent.org/docs/security)

The Unix socket is supported by OPA's `--addr` option; HTTPX supplies a real `HTTPTransport(uds=...)`. Instantiate dedicated OPA/provider clients with `trust_env=False`, redirects disabled, retry count zero and bounded connect/read/write timeouts (2 seconds OPA, 5 seconds provider). The configured provider URL must be a loopback HTTP origin in this local experiment; action fields can never supply its host or path prefix. [OPA CLI](https://www.openpolicyagent.org/docs/cli), [HTTPX transports](https://www.python-httpx.org/advanced/transports/)

Before accepting requests: verify binary version/hash, run `opa check --strict`, acquire storage ownership, initialize/recover SQLite, start OPA, then wait up to 10 seconds for authenticated health and a decision probe whose expected answer is deny. Require the correct JSON shape, not only HTTP 200. On invalid Rego, child exit, readiness timeout or malformed probe, fail startup nonzero. Runtime OPA failure makes health unhealthy and prevents new dispatches; retain readable historical outcomes and permit revocation. Do not automatically replace a crashed OPA with a different version or cached allow decision.

SIGTERM/SIGINT stops accepting new work, permits a bounded in-flight completion, closes clients/database, terminates and waits for the child, and removes only this run's temporary directory. Tests own the complete subprocess group so forced termination also cleans the child. Document that SIGKILL of the broker alone can orphan an OPA child; the owned launcher/process-group supervisor must be used. No unauthenticated administrative endpoint is added to make tests easy.

## Rego decision contract

Call `POST /v1/data/broker/decision?strict-builtin-errors=true` with exactly one trusted `input` object. The broker constructs that object; callers cannot provide arbitrary facts. The internal schema is:

```json
{
  "phase": "preflight",
  "now": 1789920000,
  "subject": {"principal": "agent:alice", "account": "alice"},
  "grant": {"id": "...", "owner": "human:alice", "agent": "agent:alice", "account": "alice", "expires_at": 2000000000, "revoked": false, "recipients": ["trusted@example.test"], "document_ids": ["public-note"], "merchants": ["shop.test"], "currency": "CAD", "auto_limit_minor": 1000, "hard_limit_minor": 5000},
  "action": {"type": "order.create", "account": "alice", "merchant": "shop.test", "sku": "paper", "quantity": 1, "amount_minor": 500, "currency": "CAD", "shipping_address_id": "home", "recurring": false},
  "snapshot": null,
  "approval": null
}
```

`phase` is `preflight` or `execute`. `now` is fresh trusted host epoch seconds on every call. At execute, `snapshot` carries the stored digest, policy revision, prepared timestamp, review expiry and prepared action; `approval` is either null or the stored authenticated human principal, matching digest and approval timestamp. These are internal schemas, not new public input fields. The originating agent remains the immutable stored subject when a human resumes the request. The broker independently enforces ownership and record/digest consistency before constructing these facts.

OPA's result is exactly `{ "decision": "allow" | "review" | "deny", "reason": "<fixed-code>" }`. Validate the object and enum; unknown decision/reason, boolean-only result, `null`, missing `result`, malformed response, timeout or any non-200 response never grants authority. Map infrastructure/evaluation faults to `failed/policy_unavailable` or `failed/policy_invalid_result` before dispatch, and leave the provider untouched. In particular, HTTP 200 with an absent `result` means an undefined decision, not success. Request strict builtin errors rather than letting a runtime evaluation error accidentally take an alternate permissive path. [OPA Data interface semantics](https://www.openpolicyagent.org/docs/rest-api)

Write native Rego v1 rules with a default deny and explicit common validity predicates. The domain policy lives here: grant bindings, revocation/expiry, recipient union, selected documents, permitted merchants/currency/destination/recurrence, integer and positive numeric constraints, review classification and execute-time review eligibility. Transport shape checks, snapshot immutability and authenticating consent remain Python responsibilities. Do not duplicate the policy as a Python allow/deny fallback. Rego does not call the provider or interpret document content.

Preflight must authorize every requested attachment/document ID before **any** provider document call. Email passing scope checks returns review; order within auto cap and selected document reads return allow; order between caps returns review; above hard cap returns deny. At execute, recompute these same scope checks using current trusted grant/time. A review operation can become allow only with matching stored human consent that is still fresh. An allow decision does not itself dispatch anything: durable lifecycle checks still apply.

Policies are loaded from fixed files at startup without watch/hot reload or remote policy management. Store `policy_revision = SHA256(ordered policy file bytes)` with every snapshot. On restart with changed policy, re-evaluate pending work against current policy, then conservatively deny old-revision consent with `policy_changed`; require a new request for fresh review. No approved request silently inherits a broader policy. The random OPA auth data is excluded from the domain-policy revision.

## Immutable snapshot and consent

Use two different hashes for different questions:

1. `input_digest`: SHA-256 over a canonical JSON envelope of `grant_id` and the validated original action. This answers whether an idempotency key was reused with changed input; it never contains freshly fetched provider data.
2. `action_digest`: SHA-256 over a versioned snapshot envelope containing request ID, originating principal/account, grant ID, prepared action, policy revision, creation timestamp and review expiry. This binds consent to exact content and context. Canonical JSON is UTF-8, sorted object keys, compact separators and no nonfinite numbers; arrays retain order. Persist the canonical bytes and their digest once.

For email, fetch selected attachments only after successful preflight. Validate each provider response's ID and exact integer version against the requested metadata. Persist `id`, `version` and `content` in the prepared action along with exact To/Cc/Bcc/subject/body. One provider response supplies metadata and content together. Human review displays that same prepared action; execution reads stored bytes and never fetches attachments again. Document mutation between review and approval must leave the outgoing approved content unchanged. Invalid/missing/version-mismatched metadata fails without any send.

Set review expiry to `min(grant.expires_at, prepared_at + 300 seconds)`. Approvals are valid for at most **60 seconds** after authenticated acceptance and never beyond review/grant expiry. Submission and approval use real host time; no agent-supplied clock field. A pending request whose grant expires or is revoked cannot execute. Snapshot age limits and approval age are separate checks. Because the broker dispatches synchronously, persisted approved-but-not-dispatched work is never automatically resumed after a crash.

The approval body is exactly the digest, with no way to replace an action or nominate an approver. Within the lifecycle lock: reload pending request and current grant, authenticate the human owner, verify digest and expiry, call current OPA, recheck fresh host expiry immediately before durable execution claim, insert approval and execution intent atomically, then dispatch the stored prepared action. A policy failure does not leave an executable approval behind.

## Persistent records and transition model

Use SQLite in the chosen state directory, `foreign_keys=ON`, WAL, `synchronous=FULL`, a finite busy timeout, explicit transactions and a schema version. Do not depend on Python sqlite3's evolving transaction default: set transaction mode deliberately and use explicit `BEGIN IMMEDIATE` for writes. SQLite allows only one simultaneous writer; this plan also permits only one broker process. No multi-host or network-filesystem guarantees are claimed. [Python sqlite3 transaction control](https://docs.python.org/3.14/library/sqlite3.html), [SQLite transactions](https://www.sqlite.org/lang_transaction.html)

| Record | Required durable fields and constraints |
| --- | --- |
| `grants` | ID primary key; human owner; agent/account; original validated scope JSON; expiry; creation time; nullable revocation time. |
| `requests` | ID primary key; originating agent/account; grant ID; idempotency key; input digest; original action; prepared canonical snapshot and digest; policy revision; created/review-expiry timestamps; internal phase; public state/reason; safe final result. Unique `(agent, idempotency_key)`. |
| `approvals` | Request ID unique foreign key; authenticated human; action digest; acceptance/expiry timestamps. Never store fixture tokens. |
| `executions` | Execution ID primary key, generated by broker and unrelated to caller idempotency key; request ID unique; exact payload digest; dispatch-intent timestamp; completion state; effect ID/safe result if available. |

Do not split the authoritative state into JSON files plus SQLite. A small safe event/audit table is optional only if needed to explain transitions; it must not become a second recovery mechanism. Snapshot content is intentionally persisted for review/recovery; directory permissions and eventual retention are deployment responsibilities, with no production data in this fixture.

```text
new -> preparing -> denied
                 -> failed
                 -> pending -> denied / failed
                            -> executing -> executed / failed / unknown
                 -> executing -> executed / failed / unknown

restart: preparing -> failed(preparation_interrupted)
         executing -> unknown(execution_interrupted)
         pending and terminal outcomes remain durable
```

`preparing` and `executing` are internal phases, never additional public contract states. Concurrent callers wait for the same lifecycle lock; normal HTTP responses therefore see a stable public state. A persisted interrupted phase is reconciled before readiness. An existing unknown/failed/denied/executed row is terminal for this key. A repeated same-key request returns it without provider access. A new key expresses a new request, not proof that an earlier unknown effect did not happen; explain that limitation in the implementation note.

## Transactions, ordering and ambiguous results

1. Authenticate and validate the incoming schema before acquiring a request record. Under the lifecycle lock, look up `(agent, key)`. Resolve identical replay/conflict first. Persist a new `preparing` row before preparation/provider reads so a lost response cannot lead a same-key retry to silently create another request.
2. Load the current grant, call OPA preflight, and prepare the immutable snapshot if authorized. Keep the lifecycle lock across preparation so revocation cannot interleave between its authorization and document reads. Recheck time/scope before subsequent protected provider calls. No SQLite transaction remains open during HTTP calls.
3. Commit denied/failed/pending outcome, or for automatic actions call execute-time OPA and atomically commit the prepared snapshot plus one `executing` intent with its random execution ID. For approval, atomically persist consent with that intent. **Commit before calling the effect provider.** A failed commit means no dispatch.
4. Keep the lifecycle lock through bounded provider IO and final persistence. Revocation is ordered either before execution eligibility, preventing dispatch, or after an already-started dispatch, unable to recall it. Return success from revoke only once its durable change is committed. This is the explicit linearization model; it does not promise cancellation of an in-flight external request.
5. For email/order send `POST /effects` with the persisted execution ID and exact prepared action. Only a valid success response with the matching execution ID becomes `executed`. Contract fixture `reject_before` returns 503 with no effect and becomes `failed/provider_rejected`. Connection loss/timeout, an invalid success body, or loss of final local persistence becomes `unknown/provider_outcome_unknown`; never advertise success without evidence. For providers without the fixture's definite-rejection semantics, a generic 5xx may also need to be unknown.
6. Do **not** automatically retry ambiguous dispatches, in the live path or after restart. This deliberately chooses the contract's permitted durable-unknown branch. Retain the execution ID for trusted investigation; do not add a new reconciliation route. The provider's idempotency remains a safety layer, not an exactly-once claim. Restart after intent commit but before send may conservatively produce unknown with zero effects; that availability loss is intentional and must be reported.
7. Selected document reads use the same durable request/execution intent before their provider GET, cache the selected result, and never reread on an identical submission. A crash after read but before result persistence yields unknown. Email attachment preparation interrupted before effect dispatch becomes failed; no hidden resume reads or effect occur.

The process lock is held across IO for clarity at this experimental scale. It limits throughput and delays unrelated revocations by at most the bounded active operation; it is not a design for a distributed broker. Removing it later would require per-record claims, fencing/leases, a clear revocation order and recovery semantics, not merely starting more workers. Neither SQLite nor OPA creates an atomic transaction with an external provider.

## Developer ownership and executable handoff

Developer B owns only `experiments/b_broker/` and `docs/experiments/implementation/B-broker.md`. The planner owns this file. Root owns the provider, common harness and contract. Do not change another approach, root fixtures or contract to accommodate B; report integration issues to root.

Suggested small file allocation:

```text
experiments/b_broker/
  run.sh                    # stable contract launcher, local bootstrap
  test.sh                   # one command: real Rego + Python integration tests
  pyproject.toml
  uv.lock
  dependencies.lock.json    # binary URL, exact checksum, versions
  bootstrap.py              # verified local OPA acquisition
  broker.py                 # HTTP, strict input handling, lifecycle and SQLite
  opa.py                    # child lifetime, auth, readiness, decision validation
  policy/broker.rego
  policy/system_authz.rego
  policy/broker_test.rego
  tests/test_broker.py       # caller-facing behavior, real broker/provider/OPA
  tests/test_opa_failures.py # real dependency faults and isolation checks
  README.md                 # interface, startup, limits, inherited/custom split
```

Keep the lifecycle and storage implementation together initially; split it only if actual locality warrants it. There is no obligation to create a file for every conceptual noun above. Preserve one externally visible module interface. Tests can use private startup parameters to supply a real failing policy fixture or observe an owned child process; do not expose test policy selection through HTTP or add a fake production engine.

The executable launcher must support exactly the common flags:

```sh
./experiments/b_broker/run.sh \
  --port 8102 --state-dir /tmp/moraine-b-state \
  --provider-url http://127.0.0.1:8099 \
  --provider-token "$PROVIDER_TOKEN" \
  --agent-token "$AGENT_TOKEN" \
  --other-agent-token "$OTHER_AGENT_TOKEN" \
  --human-token "$HUMAN_TOKEN"
```

The harness supplies those synthetic tokens and owns provider startup. Do not bake tokens into code or require additional startup options. Local `test.sh` may start a root-owned provider using its documented command once root supplies it, or call the common fixture utilities read-only. It must run from any working directory, use isolated temporary state/ports, perform real OPA `check/test` and Python subprocess tests, clean owned children, and return nonzero on any failure. Document the exact successful command, dependency outputs and test counts; no planned count is a result.

Implementation sequence:

1. Acquire and lock actual dependencies; prove `opa version`, `opa check --strict` and a real deny probe. Stop and report a concrete blocker if this cannot be done.
2. Implement Rego native tests for common scope plus both action domains and reads.
3. Implement strict HTTP authentication/validation, SQLite records and replay/ownership rules.
4. Add authorized preparation, immutable pending snapshots and authenticated approval-to-execution.
5. Add durable intents, unknown recovery, child lifecycle and readiness; run local failure tests.
6. Run the common harness with root, fix material findings within owned files, then write the implementation note with actual evidence and deviations from this plan.

## Required local evidence

Use the module's HTTP interface and inspect the root provider's durable effect/read records. Rego tests cover policy behavior directly because Rego is also the policy maintainer's genuine interface; they do not replace end-to-end enforcement tests. OPA's official testing command executes native Rego tests. [OPA policy testing](https://www.openpolicyagent.org/docs/policy-testing)

| Test group | Evidence required |
| --- | --- |
| Policy | Explicit deny default; To/Cc/Bcc union; attachment/read IDs; integer/type attacks; caps at exact limits; merchant/currency/destination/recurring constraints; agent/account binding; expired/revoked grant; approval digest/owner/age. |
| OPA unavailable | Kill the actual child after readiness, submit a fresh automatic order and approve a pending email. Neither creates an effect; health is 503; outcomes are fail-closed. No cached decision is reused. |
| Undefined decision | Start real OPA with a test package deliberately lacking `broker.decision` or making it undefined. Assert an actual 200 response without `result`, then verify startup/decision rejection and zero effects. This is not a mocked OPA response. |
| Rego errors | Invalid Rego must block startup; a real conflicting-rule or strict builtin error during evaluation must produce failure without effect. A real policy returning malformed result shape is also rejected. |
| OPA exposure | No/agent/human token cannot query its protected decision/data routes or mutate policies. Even the broker token cannot access management routes. Confirm only the private Unix listener is used. |
| Snapshot | Submit email, inspect human snapshot, mutate provider document, approve original digest; exact original bytes/recipients reach effects. Changed action in approval body and wrong digest fail. |
| Idempotency | Same agent/key/action before/after completion and after restart returns one record/outcome; same key changed grant/action is 409; another agent cannot adopt that record. Exact effect count stays one. |
| Concurrency | Race at least two approvals and repeated submissions through real HTTP connections. At most one provider effect; one execution row. A second process using the same state directory refuses startup. |
| Revocation/expiry | Pending expiry uses real host time; restart does not extend review/consent lifetime. Revoking pending grant prevents approval and creates zero effects. Check the documented serialization order for revoke versus a dispatch already underway. |
| Definite/ambiguous provider failure | `reject_before` is failed with zero effects. `accept_then_disconnect` is unknown with exactly one effect; repeats and restart do not send another effect. Verify execution ID is retained and unchanged. |
| Crash windows | Terminate broker after durable intent but before/after effect using an owned process-control test hook, restart same directory, assert unknown/no re-dispatch. Hooks are local test controls, not advertised HTTP endpoints. Pending restart preserves the identical digest. |
| Disclosure/protocol | Disallowed document causes zero reads; deny forged principal/approval/current-time fields, duplicate JSON keys and bool/float/string integers. Bob cannot GET Alice's request. Provider bearer token never appears in responses/audit. |

Prefer a handful of carefully constructed lifecycle scenarios over exhaustive combinations mirroring implementation branches. No assertion of import aliases, module topology or line counts substitutes for behavior.

## Limits, risks and expected learning

The trusted broker must own provider credentials and the only permitted execution path. A remote model/agent receives only its broker token. In a real deployment it must not share the broker's OS identity, filesystem, process namespace, secret store or unrestricted provider network access. OPA's private socket/policy files and broker state need equivalent protection. Human identity must come from a real authenticated channel with appropriate account binding. The fixture's command-line bearer secrets and loopback HTTP do not establish those properties.

These local tests establish the stated HTTP semantics under trusted host processes. An attacker with arbitrary code as the same OS user can inspect files/process arguments, change code or read secrets; loopback and a private socket do not prove containment against that attacker. Production transport, TLS, identity infrastructure, provider credential vaulting, process supervision, policy rollout, encryption/retention, durable backups, rate limits and operational monitoring remain integration work. The standard-library HTTP listener is deliberately a local experiment transport.

Remaining functional exclusions are explicit: per-operation order caps do not conserve an aggregate budget; requested prices are synthetic and do not establish genuine merchant quotes; attachment authorization is grant ID selection with version verification, not an enterprise data-classification system; provider idempotency is a fixture property; unknown effects require trusted investigation. A fresh key can express a second legitimate operation and cannot be used to infer that a preceding unknown failed.

Expected comparison result: B offers a stable, language-independent interface and central policy/state ownership at the cost of an additional process/runtime, online dependency, persistent lifecycle implementation and deployment ownership. OPA supplies real Rego evaluation and its testing toolchain. Custom code still supplies identity binding, strict schemas, grant administration, content capture, digest/consent binding, storage transactions, replay handling, recovery and credential-holding execution. Record those costs even if every common case passes; fixture success is not production certification or evidence of market demand.
