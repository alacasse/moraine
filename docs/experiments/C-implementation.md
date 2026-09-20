# C implementation: Biscuit capability executor

Implemented 2026-09-20 in `experiments/c_capability/`; planning handoff:
[C-capability.md](plans/C-capability.md). This is the authorized experiment,
not a production security system. Developer owned only that directory and
this note. No common contract/provider/campaign modifications, global installs,
Git actions, external accounts or external effects were performed.

## Delivered behavior

The executable server implements the common grant/revoke/request/lookup/approve
interface. Grant responses contain genuine Biscuit credentials. The executor
verifies the signature chain with its persisted public key, binds the root
revocation ID to the requested grant, and authorizes the actual actor/account/
audience/time/action using scoped Biscuit Datalog. Default scope excludes facts
from holder-added blocks from server policy and ancestor checks. JSON values
enter Datalog only through library parameter APIs.

Offline `attenuate.py` appends amount/action/optional input-digest restrictions
using only a parent token and public key. Separate-process tests create a child
without a private-key file and distinguish parent-allowed from child-denied
operations. An additional descendant cannot override the child's restrictions
with forged request facts. The token remains bound to **agent Alice**; transfer
or delegation to a different authenticated agent is **not demonstrated**.

Human approval uses the digest of the immutable prepared snapshot, including
provider attachment content. It has a maximum age of **300 seconds** and
rechecks the stored token, current policy and online revocation before dispatch.
The input digest used by holder attenuation is separate from this approval
digest. Both use SHA-256 of compact, sorted-key, UTF-8 JSON; array order remains
significant. Body-provided identity/time/policy/approval/replacement fields refuse.

SQLite persists grant roots/revocation, original capability and input, prepared
snapshot, digests, review deadline, approval record, stable execution ID and
outcome. A unique actor/idempotency-key pair binds the whole submission.
Thread locking serializes lifecycle decisions through provider dispatch; an
exclusive OS lock enforces one process per state directory. A committed
dispatch reservation becomes `unknown` on restart if unfinished. Unknown
outcomes do not retry, and terminal approvals refuse. Revocation orders before
a dispatch or after an already started effect; it cannot undo that effect.

## Actual dependencies and API adjustments

Installed public pinned wheel successfully under approach-local uv-managed
**CPython 3.13.13**. Runtime imports and tests verify **biscuit-python 0.4.0**,
**httpx 0.28.1**, **pytest 8.4.2**; **uv 0.11.6** drives local setup. All resolved
Python packages and hashes are in `uv.lock`. The Linux x86_64 Biscuit wheel hash
is `abe3ef892cee2c757d1428d927fd44aa41503c27e53a55acbf9e71719631723e`, matching the plan.
The planner's Cargo.lock inspection reported biscuit-auth 6.0.0/PyO3 0.24.1;
these Rust versions are not exposed by Python runtime version metadata.

The published live 0.4.0 limit API differs from a possible guessed `RunLimits`
class: use the object returned by `AuthorizerBuilder.limits()`, assign its
`max_facts`, `max_iterations`, `max_time` fields, then `set_limits(object)`.
Configured bounds: **32,768 encoded characters, eight blocks, 2,048 facts,
32 iterations, 50 ms**. JSON input is capped at 1 MiB with exact field shapes,
duplicate keys/nonfinite values rejected, and bounded list/string/numeric types.

An initial distinguishing test attempted fresh-variable arithmetic assignment
in a recursive Datalog rule; the real parser correctly rejected that syntax
before authorization. The test was corrected to use a finite reverse dependency
chain longer than the evaluator's 32-iteration budget. The initial failure is
retained, and the corrected real budget test passes. No runtime workaround or
substitute policy evaluator was added.

## Validation and evidence

Commands from the repository root:

```bash
./experiments/c_capability/test.sh -q \
  --junitxml=evidence/custom-final.xml
python3 experiments/run_campaign.py --approach c \
  --output experiments/c_capability/evidence/common-final
```

The test script changes to its own directory, so the XML path is approach-local.
Downloads and loopback process tests used authorized sandbox escalation.

- Initial common campaign: **30 passed, zero failed**, including 64 generated
  order boundary samples in one case. Root independently reported **30/30**
  before review as well; that independent report is root-owned.
- Initial custom suite: **34 passed, one failed** due to the test-only Datalog
  syntax assumption described above. Retained as `evidence/custom-initial.log`
  and `custom-initial.xml`.
- Pre-review final custom suite: **35 passed in 14.17 seconds**, actual JUnit/log evidence
  in `evidence/custom-final.xml` and `custom-final.log`.
- Pre-review final common rerun: **30 passed, zero failed**, **2.334 seconds** including
  **0.4068 seconds** summed application startup time across restarts. Evidence:
  `evidence/common-final/report.json` and process logs, including effects/reads.
- Runtime/package evidence: `evidence/dependencies.json`; frozen source manifest:
  `evidence/source-manifest.json`.

The custom suite checks separate-process keyless attenuation; action/amount/
digest restrictions; retained parent authority; descendant fake rights and
request facts; actor/audience/root-key binding; byte tampering; malformed/large/
many-block credentials; genuine Datalog budget failure; parameter injection;
online-versus-offline revocation of the same child; no read on forged document
rights; capability/grant rebinding; attenuation expiry at approval; review age;
exclusive startup lock; persisted key/snapshot/revocation; interrupted reservation
recovery; ambiguous provider completion/replay; and malformed HTTP JSON.

## Independent review corrections

The independent review retained three reproducible findings under the
root-owned `experiments/results/review-c/`: authorization could expire while
SQLite committed the dispatch reservation; one slow attachment response could
allow a second attachment read to begin after expiration; an escaped unpaired
Unicode surrogate reached UTF-8 hashing and closed the HTTP connection.
Those findings and pre-review evidence/manifests remain unchanged.

Corrections in the owned sources:

- `dispatch()` now rechecks the complete capability/current online authority
  **after** the durable reservation commit and immediately before provider IO.
  It also checks that review has approval and its deadline remains valid. An
  elapsed authority/deadline produces a durable terminal denial with no provider
  call. A crash before that denial is saved still recovers as unknown and does
  not blindly retry.
- Attachment preparation now rechecks authority before **every** selected
  document read. Earlier reads are allowed only under their own local preflight
  check; a slow response cannot carry authorization into the next read.
- String validation refuses unpaired surrogates with HTTP 400 before UTF-8
  canonicalization, hashing, policy evaluation or provider access.

The final local check cannot establish the time of remote provider acceptance;
process scheduling and network transit can occur after it. No such remote-time
guarantee is claimed.

Six new regressions use the unchanged real common provider. Three take an
actual SQLite `BEGIN IMMEDIATE` write lock until expiry, separately covering
approved orders, automatic orders and document reads. An observation wrapper
only signals the reservation attempt; the real SQLite write still blocks.
They assert no provider effect/read, durable denial and no repeated execution.
One delays the first actual attachment response beyond expiry and asserts a
second read never starts. Two send escaped high/low surrogates through HTTP and
require a 400 response, healthy subsequent service and zero provider accesses.

Before fixes, all six fail as expected; retained evidence:
`evidence/review-regressions-before.log` and `.xml` (**6 failed in 13.30 seconds**).
Post-fix evidence is separate; no previous source manifest or execution snapshot
was rewritten:

- Targeted regressions: **6 passed in 12.54 seconds**, in
  `evidence/review-regressions-after.log` and `.xml`.
- Complete C suite: **41 passed in 26.71 seconds**, in
  `evidence/custom-post-review.log` and `.xml`.
- Common campaign: **30 passed, zero failed in 3.0942 seconds**, including
  **0.4067 seconds** summed startup time, in
  `evidence/common-post-review/report.json`.
- The unchanged independent review probe functions were called without their
  root-writing `__main__` entry point. Only new C-owned outputs were written:
  `evidence/review-probes-after.json` and `.log`. All three confirm the fixes:
  surrogate HTTP 400/no access; one attachment read before expiry/none after;
  SQLite wait past expiry followed by denied request/zero effects.
- New source manifest: `evidence/post-review-source-manifest.json`; the original
  `evidence/source-manifest.json` remains the pre-review baseline.

Commands run from the approach directory for targeted/full suites:

```bash
./test.sh tests/test_review_regressions.py -q --junitxml=evidence/review-regressions-before.xml
./test.sh tests/test_review_regressions.py -q --junitxml=evidence/review-regressions-after.xml
./test.sh -q --junitxml=evidence/custom-post-review.xml
```

The first command ran before source fixes; the later two after. The common
rerun used `python3 experiments/run_campaign.py --approach c --output
experiments/c_capability/evidence/common-post-review` from the repository root.

The common campaign supplies independent HTTP and downstream-effect checks for
the broader fixture contract. Passing local checks is limited evidence about
these cases, not proof of production safety.

## Inherited and custom responsibilities

| Responsibility | Source |
|---|---|
| Signature chain, serialization, signed attenuation material, cryptographic verification | biscuit-python / biscuit-auth |
| Datalog evaluation, block provenance/trust scopes, evaluator runtime limits | biscuit-python / biscuit-auth |
| Issued authority schema, server checks/policies, safe factual context | Custom `capabilities.py` |
| Exact action/grant schemas and canonical action hashing | Custom `actions.py` |
| Identity fixtures, HTTP framing/routes and response redaction | Custom `server.py` |
| Online root revocation, approval/deadline, immutable snapshots, replay, recovery and locking | Custom `executor.py` + SQLite |
| Provider credential use, content resolution and domain dispatch | Custom executor provider adapter |
| Offline command-line attenuation client | Custom `attenuate.py` invoking genuine library append |

No homemade cryptography, custom policy language or fake Biscuit substitute is
used. The significant remaining lifecycle code is the learning: portable signed
restrictions reduce issuer involvement for narrowing, but do not remove the
trusted online executor, revocation service, human approval or replay state.

## Limitations

The same child remains cryptographically acceptable offline after online grant
revocation; fresh revocation knowledge is an explicit verifier responsibility.
Holder attenuation cannot revoke a retained parent, grant human approval, add
one-use consumption, or transfer Alice's independent authenticated identity.

Same-user local processes do not establish filesystem/process containment or
production secret storage. A deployment needs separate service identities and
inaccessible key/provider/state storage. SQLite plus the startup lock is one
host/process ownership, not a distributed execution protocol. There is no key
rotation, state migration, distributed revocation or unknown-outcome reconciliation.
Evaluator limits do not bound overall HTTP concurrency or prevent every denial
of service attack. Recovery favors no duplicate effects over automatic liveness.

Orders use synthetic prices and per-operation caps, with no aggregate budget
conservation or real quotation integrity. The provider's durable execution IDs
are a fixture contract; other providers may not provide equivalent deduplication.
No real email, payment, production OAuth or external deployment was exercised.

Usage, modules and exact HTTP startup flags are in the
[approach README](c-capability.md). API references:
[Python basic use](https://python.biscuitsec.org/basic-use),
[parameter binding](https://python.biscuitsec.org/datalog),
[Datalog scoping](https://doc.biscuitsec.org/reference/datalog),
[pinned PyPI files](https://pypi.org/project/biscuit-python/0.4.0/#files).
