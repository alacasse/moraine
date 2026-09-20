# C — Biscuit capabilities in a protected executor

Planning handoff, 2026-09-20. Implements the [experiment contract](../EXPERIMENT.md); no implementation or installation performed during planning. Documentation root is `docs`: local Git configuration is unavailable and no documentation `AGENTS.md` exists. Ownership for development: `experiments/c_capability/` and its implementation note only.

## Decision and dependency evidence

Use genuine `biscuit-python==0.4.0`, importing `biscuit_auth`, for issuance, signature verification, offline attenuation and Datalog authorization. The protected executor alone holds the provider credential. The provider accepts its existing bearer credential; it does not understand Biscuit. Public-key verification therefore protects the executor interface, with an adapter translating authorized operations into the root-owned provider interface.

PyPI publishes 0.4.0, released September 26, 2025, including `biscuit_python-0.4.0-cp313-cp313-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`. Its SHA-256 is `abe3ef892cee2c757d1428d927fd44aa41503c27e53a55acbf9e71719631723e`; no CPython 3.14 wheel is listed. Use approach-local uv-managed CPython 3.13 rather than assuming compatibility with host Python 3.14.7. [Published files](https://pypi.org/project/biscuit-python/0.4.0/#files)

Read-only inspection of the published source archive verified `biscuit-auth==6.0.0` and `pyo3==0.24.1` in Cargo.lock, and the interfaces below. The archive SHA-256 is `9f5ec05e3adcb84efbbee1137678c7a9c72185b125fb7df912dfa8a9e2fdca21`. Current main already differs in PyO3 version; install the release wheel and record its actual import/version smoke test. Wheel installation has not yet been tested. [Release source](https://files.pythonhosted.org/packages/a1/ac/46547c8a05196bada4dbb4d2e11baea68736a2997033a3df96e099916f69/biscuit_python-0.4.0.tar.gz)

Use stdlib HTTP/SQLite plus `httpx==0.28.1`; development dependency `pytest==8.4.2`. Those versions and uv 0.11.6 are present on the host. Generate an approach-owned `uv.lock`, constrain Python to 3.13, keep `UV_CACHE_DIR` and `UV_PYTHON_INSTALL_DIR` inside the approach, and use `uv sync --frozen` after initial locking. Wheel acquisition failure is a recorded blocker, not permission to substitute custom cryptography. A Rust build is a separately documented fallback if necessary.

## Interface and module depth

The module's public interface is exactly the common HTTP contract plus an offline attenuation helper. `POST /grants` returns both `grant_id` and `capability`; `/requests` requires that capability and authenticated agent credentials. All grant, revoke, lookup and approval routes retain their specified ownership checks and response shapes. The helper needs a parent token and trusted public key, never the issuer's private key. No additional HTTP endpoint is required.

Internally, concentrate lifecycle behavior behind `Executor.submit(principal, submission)`, `approve(human, request_id, digest)`, `get(principal, request_id)`, and grant operations. HTTP parsing stays thin. Two concrete domain adapters prepare emails and orders; document reads have a dedicated selected-content path. Inject the provider client and state directory. Avoid generic arbitrary-URL or raw MIME execution. The seam earns depth by keeping authentication bindings, snapshots, authorization, state transitions and effects together for every caller.

## Authority and fact provenance

The issuer persists one locally generated root key with restrictive permissions; restart reloads it. Only fixture human Alice can create grants for account Alice and agent Alice. Validate exact JSON shapes, future integer expiry, limits, and list values before issuing. No keys or complete bearer capabilities appear in audit responses.

The signed authority block carries namespaced grant/account/actor/audience bindings, expiry, the three permitted action types, recipient/document/merchant sets, currency and limits. Authority checks require `req:actor`, `req:account`, `req:audience`, `req:time` and the actual operation facts to satisfy these restrictions. The audience is a fixed executor identifier such as `moraine:c:v1`, never a caller field.

The executor verifies with its configured public key using `Biscuit.from_base64`; unknown keys, malformed tokens and authorization errors fail closed. It injects `req:*` facts from authenticated headers, the trusted clock, strict normalized action fields and provider metadata. The issuer never emits `req:*` facts. Ignore no authority-sensitive unknown fields: reject them, including approval-body action replacements. Use parameter dictionaries and `Fact`/`Check` builders; never concatenate user text into Datalog. [Binding parameters](https://python.biscuitsec.org/datalog)

Authorizer policies and authority checks retain default Biscuit trust scopes: authority plus authorizer, excluding facts from holder-added blocks. Do not enable blanket trust of previous blocks or attacker-selected keys. A forged descendant fact such as `cap:recipient("evil")` or `req:actor("agent:alice")` cannot satisfy ancestor checks or the executor's policy. All token checks must pass and a server policy must allow. [Datalog scoping](https://doc.biscuitsec.org/reference/datalog)

Represent all To/Cc/Bcc recipients as one normalized set and require it to be a subset of the signed allowed set; require nonempty actual recipients separately. Likewise check every requested document ID before any provider read. Order checks enforce merchant/currency, strict positive integers, home shipping, nonrecurrence and the hard cap. The authorizer distinguishes automatic from review outcomes; emails always require review. Python schema checks provide trustworthy facts, not an alternative grant decision engine.

## Genuine attenuation demonstration

Verified release interfaces support this illustrative, not-yet-executed client code:

```python
from biscuit_auth import Biscuit, BlockBuilder

parent = Biscuit.from_base64(capability, trusted_public_key)
narrow = parent.append(BlockBuilder("""
    check if req:action("order.create");
    check if req:amount($n), $n <= {limit};
    check if req:action_digest({digest});
""", {"limit": 500, "digest": expected_action_digest}))
child_capability = narrow.to_base64()
```

Issuance uses `BiscuitBuilder(source, parameters).build(private_key)`; execution uses `AuthorizerBuilder(source, parameters).build(verified_token).authorize()`. These operations exist in the published release, not just a conceptual token interface. [Python examples](https://python.biscuitsec.org/basic-use)

`req:action_digest` is SHA-256 over documented canonical normalized action JSON. The helper computes it for an order, whose fields need no provider enrichment. Approval uses a separate digest over the fully prepared snapshot, including attachment contents. Persist both; never confuse a holder's chosen constraint with human approval.

An appended block adds restrictions using the token's attenuation material, not the root signing key. Existing checks remain effective. Further blocks cannot make the 500-unit child accept 501 or another action digest. Tampering with signed bytes must fail verification. Retaining the original parent permits its original rights; attenuation does not erase it, transfer Alice's authentication to Bob, or create one-use authority. [Token construction](https://doc.biscuitsec.org/reference/specifications)

## Persistent state and execution

SQLite stores immutable grant bindings and authority-block revocation ID, revocation status, requests, submission hash, full submitted capability, canonical input, prepared snapshot, both digests, review deadline, stable execution ID and outcome. A unique `(authenticated_actor, idempotency_key)` prevents cross-agent collision. Identical retries return existing outcomes; changed action, grant or capability returns 409. Never re-execute a terminal or unknown request through replay.

Require the verified root revocation ID and claimed grant ID to match the stored grant. Revoking that grant invalidates every descendant and pending request. The database remains authoritative for current revocation; an offline verifier with no fresh revocation information can still accept the same cryptographically valid token. Approval, one-time consumption and replay likewise require online state. No aggregate budget accounting is claimed.

At submission, authenticate and validate, authorize before reading selected documents, resolve attachment versions/content, then persist the exact review snapshot. Reject version mismatch. Provider document content remains opaque data. Never refetch attachments at approval. Set a maximum review age of 300 seconds from submission, bounded additionally by grant expiry.

Approval accepts only the digest, authenticates the human, and reloads the stored request and capability. Recheck actor/account/audience bindings, every attenuation check, trusted current time, revocation, review age and current executor policy against the stored action. A wrong digest, hard denial or terminal state cannot authorize an effect.

Run one executor process per state directory with an exclusive startup lock. Acquire a lifecycle lock before idempotency lookup and preparation, so duplicate submissions share one snapshot. Serialize final authorization/reservation, approval and revocation with that lock and SQLite transactions. Persist a stable execution ID and internal dispatch reservation before contacting the provider; hold the lock through that bounded call. Concurrent revocation therefore linearizes before dispatch or after its result, with no promise to undo an already-started effect.

Known provider rejection becomes `failed`. Connection loss after dispatch becomes `unknown`; restart converts unfinished reservations to `unknown`. For this experiment, leave those outcomes unresolved rather than automatically retrying. Repeated approval/submission cannot create a fresh execution ID. A future reconciliation adapter could reuse the provider's durable ID, but generic exactly-once delivery is not established. Reads persist their selected result and return it only to permitted request owners.

## Development files, commands and evidence

Proposed files: `run.sh`, `test.sh`, `pyproject.toml`, `uv.lock`, `server.py`, `executor.py`, `capabilities.py`, `actions.py`, `store.py`, `provider.py`, `attenuate.py`, `tests/`, and `IMPLEMENTATION.md`, all under `experiments/c_capability/`. Keep keys/databases in the supplied state directory. Developer may consolidate files if that improves locality.

`./experiments/c_capability/run.sh` accepts all seven common flags and binds loopback. `/health` succeeds only after library import, key/store initialization and policy smoke checks; missing dependencies do not produce a healthy server. `./experiments/c_capability/test.sh` provisions only its local environment and runs local pytest. Record interpreter, resolved dependencies, exact startup/test commands and actual results.

Local tests add to the root's common campaign: keyless attenuation in a separate client process with only parent/public key; parent-allowed/child-denied action, amount and digest cases; forged appended facts; wrong actor/audience/root key; byte tampering; parameter-injection strings; descendant invalidation after grant revoke; offline verification still passing when an online executor refuses; and restart retaining key, pending snapshot and revocation state. Exercise malformed tokens and token size/block/runtime limits. The release source exposes authorizer runtime limits; verify their actual binding and choose bounded limits before accepting holder-controlled Datalog.

Inherited behavior: signature chains, serialization, attenuation and scoped Datalog evaluation. Custom behavior: identity enrollment fixtures, schemas, fact construction, policy templates, approval UX/protocol, provider adapters, durable lifecycle, revocation lookup, replay control and recovery. The principal learning is whether portable narrowing rights justify these costs when an online executor and state are still required. Same-user local tests cannot prove filesystem/process isolation; a deployment needs separate identities and inaccessible provider/key storage. Synthetic order prices and per-operation caps do not validate real commerce quotations or conserved budgets.
