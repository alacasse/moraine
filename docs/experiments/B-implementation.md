# B implementation: real OPA execution broker

Implemented and locally validated on 2026-09-20. Ownership: `experiments/b_broker/` and this note. The governing interface is [EXPERIMENT.md](EXPERIMENT.md); the development handoff is [B-broker.md](plans/B-broker.md). This is an experimental independently launched HTTP service, not an embedded authorization SDK or a production security product.

The executable entry point is [run.sh](../../experiments/b_broker/run.sh); [README.md](b-broker.md) documents its exact common flags, prerequisites and integration steps. The provider runs separately. No external credentials, actual emails, payments, Git changes or global package installs were used.

## Implemented boundary

The agent holds a synthetic broker bearer credential. The broker authenticates it, validates a strict action schema, loads a server-side grant, calls an independently running **OPA 1.9.0** process, records an immutable snapshot and executes through its private provider credential. The real Rego policy handles scope, bindings, expiry/revocation, email review, order thresholds and document selections. There is no substitute Python policy interpreter or cached allow fallback.

OPA starts on a private Unix socket, with a random per-run token, token authentication and Rego API authorization. Its broker identity can only call health and strict decision evaluation. Management, arbitrary data access and tracing query parameters are denied even with that identity. Invalid policy syntax prevents startup. Real undefined/malformed results, conflicting decisions, strict builtin errors and killed OPA cause fail-closed outcomes without effects.

SQLite owns grants, original requests/input digests, prepared canonical snapshots/action digests, approvals and unique execution intents. WAL, `synchronous=FULL`, foreign keys, explicit `BEGIN IMMEDIATE`, a finite busy timeout and a schema version are configured. A process-lifetime `flock` rejects a second broker on the same state. One lifecycle lock serializes submissions, approvals and revocation across bounded provider IO; SQL transactions never stay open over HTTP.

Consent binds the exact prepared content, actor/account/grant, policy revision, request ID and timestamps. Email attachment IDs are authorized before reads, then versions and content are captured. Approval sends those saved bytes. Review lasts at most 300 seconds and is capped by grant expiry; accepted consent lasts at most 60 seconds and is capped by review expiry. Fresh host time is checked before each protected read/dispatch; the post-review correction below adds the missing check after a delayed durable reservation. Changed policy revision denies existing pending consent.

Execution intent commits before provider IO. Definite rejection in this specific fixture becomes failed; lost response or invalid success becomes unknown. Unknown is terminal, including after restart, with its original execution ID retained. Recovery converts interrupted preparation to failed and interrupted execution to unknown. Crash after intent but before send can yield unknown with zero effects; this is a deliberate availability tradeoff. Same-agent/key replay never re-prepares or redispatches, and a changed action/grant returns 409.

## Dependencies actually executed

[dependencies.lock.json](../../experiments/b_broker/dependencies.lock.json) records the official OPA URL and checksum; [uv.lock](../../experiments/b_broker/uv.lock) freezes Python packages and artifact hashes. [dependencies.json](../../experiments/b_broker/evidence/dependencies.json) records the actual runtime output.

| Component | Observed version |
| --- | --- |
| OPA | 1.9.0; Rego v1; Linux amd64; commit `c49e670294e45bb3fd76b9e945cf821478a4bbfc` |
| Python | 3.14.7 |
| SQLite | 3.51.2 |
| uv | 0.11.6 |
| HTTPX | 0.28.1 |
| pytest | 9.0.2 |

The downloaded binary and official checksum asset both yielded SHA-256 `66fa66f3b730b2fb086003863428b382b2898d343adb4b5dfab5598b4d739eed`. The checksum/version are verified on startup, and policy files pass strict checking before OPA starts. The `.tools`, `.cache/uv` and `.venv` directories are approach-local. Python downloads are disabled.

Acquisition source: [official OPA 1.9.0 release](https://github.com/open-policy-agent/opa/releases/tag/v1.9.0). API configuration follows the official [security documentation](https://www.openpolicyagent.org/docs/security) and [Data API semantics](https://www.openpolicyagent.org/docs/rest-api); actual support was verified by the executed tests below.

## Recorded validation before independent review

Commands run from the repository root, with loopback/Unix socket and public dependency access permitted by the execution environment:

```sh
./experiments/b_broker/test.sh
python3 experiments/run_campaign.py --approach b --output experiments/b_broker/evidence/campaign-final
python3 -m py_compile experiments/b_broker/*.py experiments/b_broker/tests/test_broker.py
```

The final test invocation was timed with `/usr/bin/time -p`; its complete output is [local-tests.log](../../experiments/b_broker/evidence/local-tests.log).

- OPA `check --strict policy`: success.
- Native Rego: **12 passed / 12**, including defaults, all recipient fields, document scope, order boundary/type constraints, binding/expiry/revocation, consent owner/digest/age and snapshot age/revision.
- Local Python process/HTTP tests: **13 passed**, **18.77 s** pytest time; full test script **19.15 s** elapsed. This includes real OPA kill, actual undefined 200 result and readiness rejection, invalid Rego startup, runtime conflict/builtin error/malformed results, socket/API authorization, second-process exclusion, strict protocol, concurrent approval with one durable intent, both crash windows and changed policy revision.
- Root-authored common campaign: **30 passed / 30**, **0 failed**, **3.8004 s** reported campaign time. The cumulative application startup time across its restarts was **1.618 s**, not a standalone latency benchmark. It observed **16 effects** and **14 document reads**. The generated order-boundary case includes the root harness's deterministic input matrix.
- Python compilation: success.

The [final campaign report](../../experiments/b_broker/evidence/campaign-final/report.json) contains each case, source hashes and observed provider records. Its companion application/provider logs are in the same directory. The earlier [initial campaign](../../experiments/b_broker/evidence/campaign-initial/report.json) is retained separately. The final run used the corrected root harness that does not treat 5xx as an authorization refusal. These are developer-run executions of the independent harness; root's independent rerun/review remains separate evidence.

## Practical departures and scope of evidence

- This note uses the coordinator-assigned `docs/experiments/B-implementation.md`, superseding the plan's proposed nested implementation path.
- Python 3.14.7 and SQLite 3.51.2 are the observed host runtime. The project requires Python 3.14; it does not acquire or enforce the exact patch release. OPA and Python package versions are pinned and verified/frozen.
- Pending work with a changed revision is conservatively denied before evaluating the new policy; no old consent is offered to a potentially broader revision. The plan proposed both reevaluation and denial; the implemented behavior takes the safe immediate-denial branch.
- Scalar subject/body limits and resource bounds live in the strict Python transport validator. Rego additionally checks positive integral domain values; Python enforces the lexical JSON distinction between `1` and `1.0`/booleans.
- `run.sh` uses frozen `uv sync --no-dev --inexact` so it does not uninstall pytest while tests launch subprocesses from the same local environment. This retains already-installed development dependencies; it does not change the frozen application dependency graph.
- Trusted launch-only environment controls load actual alternative Rego fixtures or pause a process after intent/effect for crash tests. They are not HTTP endpoints or agent-controlled fields. Forced tests kill the whole subprocess group.
- The plan's scenario list was broader than the implemented local suite. There is no dedicated interrupted-preparation crash test, storage-failure injection, or concurrent revoke-versus-in-flight-dispatch test. Preparation recovery and revoke ordering are implemented and documented; those specific fault windows are not independently proven by this evidence.

## What OPA supplies, and what remains custom

OPA supplies authentic Rego evaluation, deny defaults, strict checking, native tests and HTTP API authorization. It separates policy from lifecycle code and provides an independently callable policy process. The external developer interface remains the broker's HTTP submission/review protocol; callers do not learn internal Rego input schemas or database structure.

Custom code still owns fixture identity, human/agent separation, grant creation/revocation, schema validation, provider selection/credentials, document preparation, snapshots/digests, consent handling, state transitions, concurrency, durable execution intent, replay and crash recovery. Adding the order domain reused that lifecycle and added its action shape plus Rego predicates. OPA does not eliminate online state or the credential-holding executor.

## Remaining limits

All processes are trusted and run as one local user. Private socket permissions and fixture tokens do not contain arbitrary code executing as that user, who could inspect arguments/state or change policy. Real deployment needs separate OS identities and process/file/network boundaries, proper user/human authentication, secure transport, credential protection, supervision, retention, backups and operational controls. Normal shutdown cleans OPA; SIGKILL of only the broker can orphan its child, so forced shutdown must target the supervised process group.

The lifecycle lock limits throughput and can delay revocation behind an already-running bounded operation. Provider timeouts are per call, so attachment preparation can accumulate delay. No multi-process, multi-host or network-filesystem behavior is established. Unknown effects need trusted investigation; a fresh caller key is new work, not proof that an earlier unknown failed. This fixture's idempotency and definite-503 semantics are not general provider guarantees.

Order caps are per operation, not aggregate budgets. Price inputs are synthetic, not authenticated merchant quotes. Attachment grants select IDs/versions, not an enterprise classification system. Passing these cases establishes only their HTTP/process/state/effect behavior, not production security certification or developer demand.


## Independent review correction: B-R1

The independent [B review](reviews/B-review.md) found that the last time check preceded the SQLite intent transaction. Waiting for a write lock could cross grant expiry, then execute after the reservation committed. The retained [pre-fix reproduction](../../experiments/results/review-b/reproduction.json) demonstrated an actual provider effect after expiry. This corrects a gap in the original validation; the earlier passing counts did not cover that interval.

`Broker.execute()` now obtains fresh host time after intent commit and the local test pause, immediately before protected provider IO. It checks the immutable grant expiry, review deadline and, when present, accepted consent expiry and its 60-second maximum age. An expired operation persists `denied/authorization_expired` in both request and execution records. It sends nothing, and submission replay, repeated approval and restart cannot turn that expired intent into an effect. The guard applies to document reads and email/order effects. It does not promise the time at which a remote provider accepts a request already in flight.

Four real integration regressions were added:

- Hold a real SQLite `BEGIN IMMEDIATE` while approving, let grant expiry pass, release the lock, and assert no effect plus terminal replay/restart behavior.
- Repeat with a still-valid grant and an aged canonical review snapshot whose digest is recomputed by the trusted test fixture; actual host time crosses its review deadline while waiting. No clock is substituted and no five-minute delay is required.
- Pause a document read after its committed intent, resume after grant expiry, and assert zero provider reads or effects, including on replay/restart.
- Pause approval after its committed intent and let the **real 60-second consent lifetime** expire while the grant/review remain valid. Resume and verify terminal denial, no IO, repeated-approval refusal and no effect after restart. This intentional wait accounts for most added suite time.

The shared-provider finding B-R2 belongs to the coordinator and was corrected there. B changed only its own source, tests and documentation. Pre-review logs, campaign outputs, source manifest and independent review evidence are retained unchanged. The original source manifest continues to identify the reviewed baseline rather than the corrected sources.

### Validation after B-R1 correction

Commands from the repository root:

```sh
./experiments/b_broker/test.sh -k 'expiry_during_intent_lock or expiry_after_committed_intent_pause'
./experiments/b_broker/test.sh
python3 experiments/run_campaign.py --approach b --output experiments/b_broker/evidence/campaign-post-review
```

- Targeted regressions: **4 passed**, 13 deselected, **72.87 s**; native Rego also remained **12/12**. [Targeted log](../../experiments/b_broker/evidence/post-review-regressions.log).
- Complete corrected suite: strict policy check successful, **12/12 Rego** and **17/17 Python**, **91.93 s** pytest time; script elapsed **92.30 s**. [Complete log](../../experiments/b_broker/evidence/post-review-local-tests.log). The real consent expiry wait explains most added duration; this is not a performance benchmark.
- Strengthened current common campaign: **30/30**, zero failures, **4.3557 s**, cumulative startup **1.6181 s**, **16 effects / 14 reads**. [Post-review campaign](../../experiments/b_broker/evidence/campaign-post-review/report.json). Its harness and provider hashes were checked against the current root-owned sources, including valid grant bodies under agent credentials and strengthened provider-failure assertions.
- Python compilation of the modified broker/tests: success.

The separate [post-review source manifest](../../experiments/b_broker/evidence/post-review-source-manifest.json) identifies corrected frozen sources. The original [source manifest](../../experiments/b_broker/evidence/source-manifest.json) continues to identify the pre-review baseline; neither it nor the independent pre-fix proof was overwritten.
