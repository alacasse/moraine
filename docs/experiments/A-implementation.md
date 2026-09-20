# A implementation: embedded apparitor and Cedar

Implemented and locally validated on 2026-09-20 under the experimental scope in
[EXPERIMENT.md](EXPERIMENT.md). This note records development evidence before the
root team's independent review. Sources are confined to `experiments/a_embedded/`
and this note. No Git, external accounts, real credentials or deployment were used.

## Result and exact reproduction

The embedded `ExecutionGate` owns authorization, preparation, durable approval,
idempotency and provider execution. `host.py` is a loopback fixture adapter;
HTTP hosting is not the proposed reusable product seam. See the small embedded
client example and startup instructions in
[README.md](a-embedded.md).

From `/home/alacasse/projects/moraine/experiments/a_embedded`:

```sh
./setup.sh
./test.sh -q
```

From `/home/alacasse/projects/moraine`:

```sh
python3 experiments/run_campaign.py --approach a \
  --output /home/alacasse/projects/moraine/experiments/a_embedded/evidence/final-campaign
```

Observed development results: **37 local tests passed in 17.76 s**;
**30 common campaign cases passed, 0 failed, in 2.9918 s**, including the common
case's 64 deterministic generated order samples. Campaign startup time was
0.8075 s accumulated over its restarts. These are one machine/run observations,
not a throughput benchmark or a cross-approach ranking. Evidence:
[local log](../../experiments/a_embedded/evidence/local-tests-final.txt),
[campaign report](../../experiments/a_embedded/evidence/final-campaign/report.json),
[runtime versions](../../experiments/a_embedded/evidence/runtime.json), and
[source manifest](../../experiments/a_embedded/evidence/source-manifest.json).

The normal dependency fetch failed on sandbox DNS. The authorized escalation
downloaded public wheels successfully. Normal campaign startup also encountered
the sandbox's socket prohibition; local HTTP and asyncio tests ran with authorized
socket access. This is an environment permission requirement, not evidence of
application isolation. An initial campaign caught a synthetic token beginning
with `-`, which argparse treated as an option; the host now accepts opaque token
values in the documented separate-argument form. The root harness subsequently
prefixed its synthetic tokens. The failed first startup log remains in
`evidence/first-campaign/`.

## Dependencies and real reuse

`requirements.in` pins **apparitor[cedar] 0.1.1** and **cedarpy 4.8.7**;
`requirements.lock` pins and hashes all 18 transitive/test dependencies. Actual
runtime: CPython 3.14.7; Pydantic 2.13.5; httpx 0.28.1; pytest 9.1.1. Installation
uses the local `.venv`, `.uv-cache`, and `.python` paths. The published Cedarpy
wheel was compatible; no custom Cedar substitute or Rust build was needed.

Installed package source confirmed the planner's API findings. Every eligibility
decision calls the actual `AuthorizationEngine.evaluate_requests` with a real
`EvaluationRequest`. `is_allowed_gateway` accepts only a non-error ALLOW; empty
evaluation is rejected. Cache is disabled and engine error policy is `deny`.
Local tests inspect upstream public metrics after real allow, deny and error
decisions; they do not merely assert an import or substitute a fake engine.

| Responsibility | Existing library or custom implementation |
| --- | --- |
| Subject/action/resource request models, engine orchestration, decision aggregation, error-to-block mapping, metrics and gateway verdict predicate | Actual apparitor |
| Eligibility rules, entity equality, membership, numeric caps, policy parsing/schema validation and evaluation | Actual Cedar through Cedarpy |
| Strict input types and extra-field rejection | Pydantic with project-defined shapes |
| Reject Cedar Allow accompanied by diagnostics; map structured IDs and trusted context | Custom `StrictCedarBackend` and policy mapper |
| Fixture identity authentication and HTTP routing | Custom benchmark host |
| Grant authority, SQLite records, 300-second review, snapshot/digest, revocation and idempotency | Custom gate |
| Automatic versus review classification, attachment preparation, bounded provider calls, crash/unknown outcome handling | Custom gate/provider client |

Apparitor's native Cedar backend only checks the returned decision; it does not
reject Cedar diagnostics. The private adapter implements its public
`DecisionBackend` protocol and calls real `is_authorized` / `is_authorized_batch`.
It validates policies against a schema before startup and rejects diagnostics,
malformed results, NoDecision and batch cardinality mismatch. It does not inherit
from private upstream internals. A distinguishing test uses a schema-valid
integer-overflow rule alongside a matching permit: raw Cedar returns Allow plus
an error; the adapter plus actual apparitor returns BLOCK with error status, both
for single and batch evaluations. This supports a concrete upstream contribution
opportunity: optional strict diagnostics in the Cedar adapter.

Review classification remains custom: all emails and orders above the automatic
cap require human review after Cedar eligibility succeeds. No native apparitor
HITL lifecycle is claimed. The experiment also does not use its tool-call
parsers, framework adapters, HTTP decision transport, cache or OAuth machinery.
The existing engine removes decision-orchestration/error-handling work; it does
not remove the larger execution lifecycle implemented here.

## Durable execution and trust boundary

The trusted host creates `Principal` values from its fixture credential map and
configures the provider once. The module does not authenticate an arbitrary
`Principal` constructor: embedding callers must enforce that boundary. The
provider token remains in host process configuration and the HTTP client; no
response, snapshot, SQLite grant/request or sanitized transition record includes
it. Same-user process arguments remain outside the protection claim.

SQLite persists grants and requests, with uniqueness on authenticated actor plus
idempotency key. Submitted canonical JSON includes the grant and complete action.
Pending snapshots include exact recipients/body and fetched attachment bytes;
the digest covers a versioned actor/account/grant/action envelope. Approvals
accept only that digest and recheck the current grant and loaded Cedar policy.
Review expires at the earlier of 300 seconds after submission and grant expiry.
Fresh policy is loaded and validated on restart. The final dispatch checks the
trusted clock again after asynchronous policy evaluation.

A single asyncio lock spans lifecycle mutations and bounded downstream I/O.
An OS advisory file lock refuses a second gate sharing the state directory,
making this explicitly a single-process experiment. SQLite uses WAL and FULL
synchronous mode; dispatch intent and server-generated execution ID commit before
network I/O. Revocation linearizes before or after dispatch and cannot recall a
completed operation. The module's downstream timeout is 3 seconds per httpx
timeout phase, not a strict whole-request deadline; attachment preparation may
make multiple sequential reads. No distributed scaling claim follows.

Explicit downstream rejection becomes failed; connection loss or a malformed
success receipt becomes unknown. Repetition returns that durable outcome without
dispatching again. Startup maps unfinished executing records to unknown and
unfinished preparation to failed. An interrupted live coroutine exposes unknown
instead of leaking an internal lifecycle phase. Unknown outcomes have no
reconciliation UI or blind retry in this prototype. The fake provider's durable
execution-ID uniqueness is additional fixture protection; no exactly-once claim
is made about arbitrary providers.

## Tests, deviations and limits

Local tests use the real root-owned provider over HTTP and inspect its effects
and read records. They cover exact cap boundaries; strict numbers; forbidden BCC,
attachments and reads before disclosure; durable revocation without cache;
actor/key binding; exact snapshot reuse after provider mutation and restart;
grant expiry during attachment preparation; review-age expiry; concurrent
approval; known rejection and accepted-then-disconnected outcomes; cancellation
after a real accepted effect with restart recovery; policy replacement on restart;
state-directory exclusivity; malformed JSON; duplicate authorization headers;
forged body identity; and malformed policy refusing startup before health exists.
The common campaign independently exercises the full HTTP surface and real
process termination/restart. A same-process cancellation test is identified as
such and is not presented as a kernel crash/disk fault test.

The plan's separate `store.py` was folded into `gate.py`: storage is private to
the lifecycle and no interchangeable store abstraction was needed. The file lock,
duplicate JSON/header rejection, finite numeric parsing and opaque-token CLI
handling strengthen fixture behavior without broadening the product interface.
The supplied JSON schema repeats the shared action context explicitly; there is
no runtime schema generation or custom policy DSL.

The host remains a synthetic HTTP authentication example. Arbitrary code in the
trusted process, another same-user process that can read credentials/state, or a
developer adding a direct provider call can bypass an embedded module. Stronger
containment requires separate process identities, filesystem/credential controls
and network enforcement, none of which these tests prove. No actual Gmail/OAuth,
commerce quotes, MIME construction, provider price integrity, aggregate budget
conservation, production identity, distributed workers, cross-platform file lock,
load/DoS resilience, encryption at rest or data retention policy was implemented.
Fixture limits are per operation; a new idempotency key represents a new operation.
Selected document text is returned as data and cannot amend grants or policies.

## Post-review corrections

The coordinator completed A's review after the independent reviewer was
interrupted; provenance and baseline findings are retained in
[A-review.md](reviews/A-review.md). Two temporal defects were confirmed with
three regression instances against the original code: expiry between attachment
reads, and grant/review expiry while a real SQLite writer lock delays dispatch
reservation. All three failed before correction with observable extra reads or
effects, rather than only a differing internal state.

The gate now checks grant expiry before every attachment read and rechecks
grant/review deadlines after the durable executing transition, immediately before
provider IO. The lifecycle lock already preserves grant/policy authority across
these intervals; elapsed time required the additional checks. A known expiry
before IO becomes a persistent denial, including on replay and restart.

The full A suite now passes **40 tests** (23.91 s in the coordinator's recorded
run). See [before](../../experiments/results/root-a-regression-before.log) and
[after](../../experiments/results/root-a-regression-after.log). The original
37-test evidence and source archive are retained. A last local check does not
guarantee the time at which a remote provider accepts an already issued request.
