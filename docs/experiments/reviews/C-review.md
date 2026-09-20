# Independent review of C — Biscuit capability executor

Date: 2026-09-20. Reviewer developed B, not C; C implementation and tests were reviewed without modifying either approach. Scope: shared contract, C planning/implementation notes, frozen C sources, real Biscuit authorization/provenance, lifecycle and focused test quality. Applied `test-quality-review` in focused mode.

## Verdict

**Changes required: three reproduced findings, one high risk and two medium risk.** C uses genuine Biscuit rather than substitute cryptography and its attenuation/provenance tests are materially useful. Its 35 existing tests pass independently, but do not cover authority expiring during preparation or a blocked durable reservation. Those windows allow a provider read or effect after expiry. Malformed Unicode also escapes the HTTP refusal boundary.

The frozen [C manifest](../../../experiments/c_capability/evidence/source-manifest.json) matched **16/16 files** before review; [verification evidence](../../../experiments/results/review-c/manifest-verification.json) records the check. Existing suite: **35 passed in 13.66 s**, [log](../../../experiments/results/review-c/custom-independent.log), [JUnit](../../../experiments/results/review-c/custom-independent.xml). The coordinator's independent common campaign had already established 30/30 for this frozen version; this review did not substitute another campaign pass for the targeted probes.

## High-risk behavioral gaps

### C-1 — [P1 / high] Revalidate authority after the durable reservation, before provider IO

**Location:** [executor.py:259](../../../experiments/c_capability/executor.py#L259), especially the save at line 261 and provider call at line 267; approval's last authorization is at line 249. Automatic dispatch uses the same path after line 207.

`dispatch()` can wait in SQLite after the last time-sensitive Biscuit authorization. Once the save returns it performs the effect without obtaining a fresh decision. This is observable with ordinary SQLite locking, without changing the implementation, token, database contents or trusted clock.

**Reproduction:** issue a grant expiring in three seconds, submit a pending order, hold a separate SQLite `BEGIN IMMEDIATE`, approve while the grant is still valid, and release the write lock after expiry. In the recorded run approval started at **1789929074.7103353**, grant expiry was **1789929077**, and the lock released at **1789929077.2000358**. The provider received the effect at **1789929077.2426183**; C returned **`executed`**, with **one provider effect**. Full result: [probes.json — expiry_during_reservation](../../../experiments/results/review-c/probes.json).

**Impact:** a blocked reservation lets a valid approval outlive its grant before the protected effect even starts. The same location can outlive holder-added time restrictions or the review deadline. This is an expiry enforcement bug, not a claim that an attacker may edit the database or that revocation can recall an already-started effect. The lock is fault-injection to reproduce a scheduling/storage delay.

**Action:** after durable reservation and immediately before protected IO, re-evaluate the stored original capability/current authenticated context with fresh host time, including the review/consent deadline. Persist a terminal refusal if it no longer holds; do not dispatch. Cover automatic and approved work, including an attenuated deadline, with a real blocked-commit regression that asserts zero effects.

### C-2 — [P2 / medium] Recheck authority between attachment reads

**Location:** [executor.py:151](../../../experiments/c_capability/executor.py#L151), the attachment loop at lines 155–160; enclosing authorization calls occur only before and after the whole preparation at lines 204 and 207.

An email's initial authorization covers the selected IDs, but preparation fetches every attachment without rechecking the grant or capability's current time. If the first response is slow, subsequent provider reads start after authority has expired. Denying after preparation is too late to protect those accesses.

**Reproduction:** submit two permitted attachments with a grant expiring in two seconds. A subclass of the root provider handler delays only the first document response, after that first access was recorded; it preserves the root provider's authentication, data and storage behavior. Expiry was **1789929074**. Reads began at **1789929072.5798566** and **1789929074.2014832**. C ultimately returned `denied/capability_denied`, but the provider recorded **two reads, one started after expiry**. No email was sent and no document content was returned to the agent. Evidence: [probes.json — expiry_during_preparation](../../../experiments/results/review-c/probes.json).

**Action:** carry the stored authenticated submission into preparation and reauthorize before each new provider document call. Include fresh host-time evaluation of holder-added restrictions, not only the copied grant expiry. Add a delayed-first-response regression whose second read count stays zero. The existing denied-document tests prove selected-ID enforcement but do not protect this timing boundary.

## Weak or misleading tests

### C-3 — [P2 / medium] Reject non-UTF-8-encodable JSON strings at the protocol boundary

**Location:** [actions.py:30](../../../experiments/c_capability/actions.py#L30), `text()` accepts lone surrogate code points; [actions.py:21](../../../experiments/c_capability/actions.py#L21) then UTF-8-encodes canonical JSON. [server.py:110](../../../experiments/c_capability/server.py#L110) catches only `Refusal`. Adjacent coverage: `test_malformed_protocol_json_returns_400`, [test_http.py:22](../../../experiments/c_capability/tests/test_http.py#L22).

**Reproduction:** an otherwise valid authenticated email submission with JSON subject `"\ud800"` is parsed into a Python string, passes validation, and raises uncaught `UnicodeEncodeError` while computing `submission_hash`. The client receives **`RemoteProtocolError`**, not a JSON 4xx refusal. The server prints a traceback; subsequent health remains 200. There were **zero effects and zero reads**, so this is a protocol robustness failure, not an authorization bypass or full service crash. [Exact traceback and result](../../../experiments/results/review-c/probes.log).

**Action:** reject strings that cannot be encoded as UTF-8 before canonical hashing or Datalog parameter construction, and return the normal stable refusal response. Expand the malformed-string HTTP test beyond syntactic JSON failures and assert a 4xx JSON body, no provider access and subsequent healthy operation.

## Regression coverage findings

The three regressions above are the recommended additions. Existing grant/attenuation expiry tests wait until expiry **before** approval starts; they cannot detect C-1 or C-2. The existing malformed JSON cases cover duplicate keys, nonfinite numbers, syntax and non-object values, but not valid JSON escape sequences that create invalid Unicode scalar values.

Recovery confidence has a specific limit: `test_unfinished_dispatch_restarts_unknown_without_retry` constructs a `dispatching` record with `save()` and reopens the executor. It usefully protects recovery from that durable state, but does not exercise a real process dying around the production reservation/provider boundary. The common ambiguous-completion test covers a different failure window. This review does not claim that an actual crash-window defect was demonstrated; stronger process-control evidence would be needed for that claim.

## Mocking and fixture friction

**Low concern.** Most capability tests call the actual Rust-backed Biscuit library, and lifecycle tests use the real root provider and SQLite, checking effects or read records. The separate-process attenuation test has no private-key file and verifies parent-allowed/child-denied behavior. This gives stronger confidence than checking token structure or successful signatures alone.

The keyless test's block-count/revocation-ID assertions are supplementary; the authorization differences are the useful proof. Tests of fake `cap:*` and `req:*` facts, actor/audience/root-key binding, descendant constraints, budget failure and parameter injection exercise the real trust boundary. No mock policy engine or mocked signature verification was found.

The review's delayed provider handler and separate SQLite writer are explicit timing fault-injection. They do not replace authorization or forge provider acceptance. The protocol probe uses the actual HTTP server; timing probes call the actual executor's public lifecycle methods against a real loopback provider.

## Design signals revealed by tests

1. **Biscuit contributes a narrow, defensible primitive:** portable signed restrictions with provenance-aware checks. Default block scoping excludes holder-added facts from the authorizer/ancestor checks; the implementation keeps that default and supplies dynamic values through library parameters. The executed tests support that boundary, consistent with the official [scoping reference](https://doc.biscuitsec.org/reference/datalog) and [parameter binding API](https://python.biscuitsec.org/datalog).
2. **Fresh authorization and durable effect handling remain executor responsibilities.** The two timing findings arise between library calls, preparation and persistence. Cryptographic validity does not create a transaction joining time, revocation, SQLite and the provider. The useful reusable seam is the protected execution lifecycle around Biscuit, with explicit revalidation at protected IO boundaries.
3. **Separate offline and online guarantees remain necessary.** The test that verifies a revoked child offline while the online executor rejects it is honest, useful evidence. Alice-bound attenuation narrows authority but does not transfer authenticated identity to Bob, erase a retained parent, supply human consent or remove replay/revocation state. These are admitted limits, not findings.

## Comparative validity across A, B and C

The common contract is useful for comparing observable authentication, grant scope, review snapshots, replay and synthetic-provider outcomes. It also makes the remaining custom lifecycle work visible in all approaches. Distinguishing tests add meaningful evidence: embedded-library integration for A, real policy-process failure for B, and offline signed attenuation/provenance for C.

The comparison cannot establish a universal architecture winner. It forces every approach through a common HTTP host and online trusted executor: that standardizes behavior but does not directly measure A's embedded developer interface, B's operational deployment value, or C's possible multiple-verifier/offline deployment benefits. C demonstrates narrowing for the same Alice actor, not delegation between independent authenticated principals. That is within the accepted experiment.

The reported test totals are different suites, not comparable quality scores. Startup/campaign durations include different process/restart/runtime work and are not controlled latency or throughput benchmarks. All approaches use one local host, one synthetic provider and small fixture data; passing 30 common cases does not prove security completeness, same-user process containment, distributed correctness, real OAuth/provider semantics, aggregate budgets or developer demand. The timing findings are direct evidence for keeping these conclusions bounded.

## Recommended actions and reproducible commands

Fix C-1, C-2 and C-3, add their targeted regressions, then rerun the C suite, common campaign and retained review probes. Preserve this pre-fix report and probe outputs; record post-fix evidence separately. No source corrections were made during this review.

Independent suite command, executed from `experiments/c_capability`:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  --junitxml=/home/alacasse/projects/moraine/experiments/results/review-c/custom-independent.xml
```

Probe command, executed from repository root (requires loopback socket permission):

```sh
PYTHONDONTWRITEBYTECODE=1 experiments/c_capability/.venv/bin/python \
  experiments/results/review-c/probes.py
```

The probe source is [probes.py](../../../experiments/results/review-c/probes.py). It writes `probes.json`; captured stdout/stderr are retained in `probes.log`. Only synthetic local credentials and provider records were used.
