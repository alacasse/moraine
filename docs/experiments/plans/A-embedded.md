# A — Embedded delegated execution module

Planning handoff, 2026-09-20. Governing contract: [EXPERIMENT.md](../EXPERIMENT.md). This is a proposed implementation, not an executed validation or an accepted product architecture. The documentation root is `docs`; no functioning Git repository or documentation-root override is available.

## Question and interface

Can a trusted Python tool backend gain durable delegated execution through one deep module, while genuinely reusing apparitor and Cedar? The external seam sits immediately before privileged provider access. The benchmark HTTP host is an adapter at this seam; it is not the product interface.

Proposed interface:

```python
gate = ExecutionGate(state_dir=state_dir, provider=provider_client)
grant = await gate.create_grant(authenticated_human, grant_spec)
outcome = await gate.submit(authenticated_agent, grant.id, key, action)
snapshot = await gate.inspect(authenticated_human, outcome.request_id)
outcome = await gate.approve(authenticated_human, snapshot.id, snapshot.digest)
await gate.revoke(authenticated_human, grant.id)
await gate.aclose()
```

These are proposed project methods, not upstream apparitor methods. Authentication belongs to the host; typed principals passed here must originate from verified credentials. Callers never separately authorize and then execute, supply provider credentials per action, or reconstruct approved payloads. The module owns action parsing, authorization, preparation, durable review, idempotency and execution. Its interface includes serialized execution, bounded provider timeouts and potentially `unknown` outcomes. This depth gives both domains locality without a plugin framework or a general workflow language.

## Verified dependencies and acquisition

Use `apparitor[cedar]==0.1.1` and `cedarpy==4.8.7`. Apparitor's release extra requires `cedarpy>=4.8,<4.9`; do not silently upgrade to Cedarpy 4.12. PyPI supplies an apparitor universal wheel and a Cedarpy CPython 3.14 Linux x86-64 wheel. The inspected host is Python 3.14.7, x86-64, glibc 2.43, with uv 0.11.6, so the published manylinux 2.17 wheel fits its platform tags. Installation/import compatibility still needs execution during development. [Apparitor release](https://pypi.org/project/apparitor/0.1.1/), [release requirements](https://github.com/jhawlwut/apparitor/blob/v0.1.1/pyproject.toml), [Cedarpy release files](https://pypi.org/project/cedarpy/4.8.7/#files).

Developer creates `experiments/a_embedded/requirements.in` containing those two pins plus `pytest>=8,<10`; apparitor already brings httpx and Pydantic. From that directory:

```sh
uv --cache-dir .uv-cache venv --python python3 .venv
uv --cache-dir .uv-cache pip compile --python .venv/bin/python --generate-hashes requirements.in -o requirements.lock
uv --cache-dir .uv-cache pip sync --python .venv/bin/python --require-hashes --only-binary :all: requirements.lock
.venv/bin/python -c 'import apparitor, cedarpy; from importlib.metadata import version; print(version("apparitor"), version("cedarpy"))'
```

Retain the generated transitive lock and actual versions. This uses no global installation, Rust compilation or managed-Python download. A concrete resolution failure is evidence to report, not permission to replace Cedar with Python conditionals. Implement HTTP hosting with the standard library, forwarding work to one asyncio event loop, to avoid an unrelated web-framework dependency.

## Real reuse and one necessary adapter

The actual apparitor interface is `AuthorizationEngine(config, client=backend)` followed by `await engine.evaluate_requests([EvaluationRequest(...)])`. The request uses `Subject(type, id)`, `Action(name)`, `Resource(type, id)` and `context`; `is_allowed_gateway(verdict)` accepts a clean ALLOW and rejects SKIP/error. Disable its cache and select `on_error="deny"`. [Engine](https://github.com/jhawlwut/apparitor/blob/v0.1.1/src/apparitor/engine.py), [models](https://github.com/jhawlwut/apparitor/blob/v0.1.1/src/apparitor/models.py), [verdict check](https://github.com/jhawlwut/apparitor/blob/v0.1.1/src/apparitor/decision.py).

Two source facts affect implementation: the supplied CedarBackend forwards IDs and context, not `Resource.properties`, and its allow check does not inspect Cedar diagnostics. Its result also has no advisory context, so native `review_predicate` cannot supply approval routing. [Native adapter](https://github.com/jhawlwut/apparitor/blob/v0.1.1/src/apparitor/cedar.py).

Provide a small private `StrictCedarBackend` implementing the existing `DecisionBackend` interface: `evaluate`, `evaluate_batch`, `aclose`. Use real `cedarpy.is_authorized(request, policies, entities, schema)` and `is_authorized_batch`; reject any `result.diagnostics.errors`, malformed result or non-Allow result. Convert errors to apparitor's `MalformedPDPResponseError`. Validate policies against the schema at startup. Do not subclass private apparitor internals or monkeypatch upstream. Cedar intentionally skips errored rules; this adapter selects stricter host semantics. [Backend interface](https://github.com/jhawlwut/apparitor/blob/v0.1.1/src/apparitor/backends.py), [Cedarpy functions and diagnostics](https://github.com/k9securityio/cedar-py/blob/v4.8.7/cedarpy/__init__.py), [Cedar semantics](https://docs.cedarpolicy.com/auth/authorization.html).

Concrete internal call, with `policy_context` built only by the module:

```python
engine = AuthorizationEngine(
    ScannerConfig(backend="cedar", cache_enabled=False, on_error="deny"),
    client=StrictCedarBackend(policy_path, schema_path),
)
verdict = await engine.evaluate_requests([EvaluationRequest(
    subject=Subject(type="agent", id=actor.id),
    action=Action(name=action.type),
    resource=Resource(type="account", id=action.account),
    context=policy_context,
)])
```

Cedar owns eligibility: authenticated agent/account match, active unexpired grant, recipient/document/merchant membership, currency, quantity, amount and hard cap, home destination and nonrecurring orders. Represent principal/account identities as structured Cedar entity identifiers, with host-derived grant identity references in context. Pass normalized proposed fields separately from trusted grant fields; never merge arbitrary input into context. Pydantic strict schemas reject extra fields, coerced numerics and unknown action variants before mapping. Use signed-64-bit integer bounds compatible with Cedar.

After a clean policy allow, the module performs the contract's explicit review classification: every email, and orders above the grant's automatic limit, require review. Reads and smaller orders execute. This small Python classifier is custom lifecycle glue, not Cedar's native three-way decision. Document that split and test both sides of each threshold. Apparitor still supplies real evaluation orchestration, strict result aggregation, error handling and decision metrics/logging; Cedar supplies the policy evaluation.

## Lifecycle and persistent state

SQLite stores grants, requests and sanitized transition records. Grants bind creator, agent, account, restrictions, expiry and revoked status. Requests bind authenticated actor, grant, idempotency key, submitted canonical JSON, prepared snapshot, digest, policy hash, review deadline, state, provider execution ID and safe result. Enforce uniqueness on `(actor, idempotency_key)`. Tokens stay in process configuration and never enter snapshots or audit records.

One asyncio lock serializes mutations, including revoke and provider dispatch; SQLite transactions make each persisted transition atomic. Keep the lock across the bounded provider call but commit the dispatch record before network I/O. This intentionally sacrifices throughput for understandable experiment semantics; revocation linearizes before or after a dispatch, never promises to recall an already-sent effect.

Submission checks idempotency before preparation. The same normalized submission returns its existing outcome, including terminal/unknown outcomes; changed payload returns 409. Eligibility must pass before any provider document read. Then resolve permitted email attachments, verify requested versions, and persist their exact contents with recipients/body. No denied document ID is fetched. Preparation errors become `failed` with no effect.

Digest a versioned canonical JSON envelope containing actor, account, grant and complete prepared action. Human review exposes that snapshot. Review lasts at most 300 seconds from creation and never beyond grant expiry. Approval accepts only the stored digest, checks human/account ownership, pending state, deadline, current grant and loaded policy, then authorizes the stored action again. Recheck trusted wall-clock expiry immediately before automatic or approved dispatch, including after slow attachment preparation. Pending grants revoked while waiting cannot resume. Policy changes take effect on restart; persist policy hashes for diagnosis and reevaluate against the newly loaded policy.

Durably mark internal `executing` with a server-generated execution ID before `/effects`. On success commit `executed`; an explicit provider rejection becomes `failed`; connection loss becomes `unknown`. On restart map unfinished `executing` to `unknown`. This first experiment leaves unknown outcomes unresolved and returns the same outcome on repeat submission, avoiding another effect; terminal approvals refuse. Never send a new execution ID for an ambiguous prior attempt. The common contract permits this conservative result. Review consumption and provider success are distinct transitions; no exactly-once claim follows from them.

## HTTP contract fit and trust claims

`run.sh` accepts `--port N --state-dir PATH --provider-url URL --provider-token TOKEN --agent-token TOKEN --other-agent-token TOKEN --human-token TOKEN` and binds loopback. It constructs the token-to-principal map from fixture arguments, rejects colliding/missing tokens, and routes all advertised protected endpoints through the module. Human credentials alone create/revoke grants or approve requests, limited to Alice's account/agent. Grant creation rejects malformed types, expired grants and limits outside `0 <= auto_limit_minor <= hard_limit_minor`. Agent credentials alone submit. Owners and the fixture human inspect requests; Bob receives no Alice snapshot. `/health` succeeds only after database opening and policy validation. Startup also verifies the provider is reachable with configured credentials without reading a document.

Return the specified state/reason/request ID objects; pending adds digest and executed reads add selected content. Use 4xx for malformed/authentication errors, 409 for changed idempotency payloads and safe generic refusals for foreign IDs. No raw provider errors, credentials, action-replacement approval fields, raw HTTP or MIME submission path is exposed. Strictly reject unknown action and approval fields.

The protected-host claim assumes attackers can only invoke these HTTP endpoints and have agent credentials. A developer can bypass any Python module by writing another provider call; arbitrary code in the trusted process or the same OS user's readable credential space is outside this experiment. Production would need separate process identities, credential access and network controls. Per-operation order caps do not conserve an aggregate budget; synthetic amounts do not verify merchant quotes.

## Implementation handoff and evidence

Developer owns only `experiments/a_embedded/` and `docs/experiments/A-implementation.md`. Suggested files: `gate.py` for the external interface/lifecycle; `policy.py` plus `policy.cedar`/`schema.json` for mapping and strict adapter; `store.py` for transactions; `provider.py` for bounded HTTP access; `host.py`; `run.sh`; dependency files; and tests. Keep these internal modules private; avoid speculative interchangeable stores or executors.

Provide `./test.sh` for local pytest and `./run.sh` for common hosting. Tests exercise the external interface against real apparitor/Cedar, then HTTP integration against the root provider. Required distinguishing checks: policy errors alongside an otherwise matching permit fail closed; malformed startup policy fails health; cache disabled revocation; no body-supplied identity/context affects authority; empty evaluation cannot execute; trusted versus bypassable host assumptions are explicit.

Behavioral tests cover both domain thresholds, BCC, attachment mutation after pending, denied-read zero access, strict numeric types, cross-agent access, changed idempotency payload, concurrent duplicate approval, expired/revoked review, restart while pending and ambiguous dispatch recovery. Inspect provider effects and reads. Record commands, counts, lock versions, deviations and inherited/custom responsibilities. Expected learning: whether interface depth repays custom persistence and executor glue, whether the strict adapter is a useful upstream contribution, and how much host integration work remains once authorization itself is reused.
