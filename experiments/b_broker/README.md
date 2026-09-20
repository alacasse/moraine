# B: independently deployed OPA execution broker

A local experimental service using genuine OPA 1.9.0/Rego v1, a protected Unix-socket policy child, and durable SQLite grants, snapshots, approvals and execution intents. The common HTTP contract is [EXPERIMENT.md](../../docs/experiments/EXPERIMENT.md). This fixture is not production security infrastructure.

From any working directory, launch the executable `run.sh` with:

```sh
./experiments/b_broker/run.sh \
  --port 8102 --state-dir /tmp/moraine-b-state \
  --provider-url http://127.0.0.1:8099 \
  --provider-token "$PROVIDER_TOKEN" --agent-token "$AGENT_TOKEN" \
  --other-agent-token "$OTHER_AGENT_TOKEN" --human-token "$HUMAN_TOKEN"
```

The root-owned fake provider must already be running. The four synthetic tokens must be nonempty, ASCII and distinct; actor mappings are fixed by the common contract. The listener binds only `127.0.0.1`. Requires Linux x86_64, Python 3.14 and uv. Actual verified host runtime is Python 3.14.7, SQLite 3.51.2 and uv 0.11.6. Python patch versions are recorded rather than downloaded; `uv` disables interpreter downloads. No global installation is performed.

First startup obtains the fixed official OPA artifact, checks its SHA-256 against `dependencies.lock.json`, and installs the frozen HTTPX dependency graph under `.venv` using `.cache/uv`. Every startup verifies OPA checksum/version and runs `opa check --strict`. The cached binary is under `.tools/opa-1.9.0`. `uv.lock` includes full package hashes; `run.sh --inexact` retains existing development dependencies so concurrent local test runners are not uninstalled.

```sh
./experiments/b_broker/test.sh
python3 experiments/run_campaign.py --approach b --output experiments/b_broker/evidence/campaign
```

`test.sh` performs native OPA strict checking, 12 native Rego tests, then 17 real process/HTTP tests. The consent expiry regression deliberately waits for the actual 60-second lifetime. The common campaign provides the broader domain/snapshot/replay checks and observes downstream effects. Tests require permission to open Unix and loopback sockets. Evidence and detailed deviations are in [B-implementation.md](../../docs/experiments/B-implementation.md).

## Lifecycle and policy boundary

OPA supplies domain authorization: grant/agent/account bindings, grant lifetime, recipients, selected document IDs, merchant/currency/destination/recurrence, order limits, automatic versus human-reviewed classification, and execute-time consent checks. Policy responses are a fixed decision/reason pair. Undefined, malformed, conflicting, strict builtin errors or dependency outage cannot dispatch. OPA's own authorization policy permits the random private broker identity to call only health and strict decision evaluation; even it cannot use management/data routes. There is no Python policy fallback.

Custom broker code supplies fixture authentication, strict schemas and size bounds, server-side grant administration, SQLite transactions, immutable content snapshots, action digest binding, consent acceptance, serialized replay/ownership handling, provider credentials and durable execution/recovery. No claim is made that OPA supplies these responsibilities. Python rejects malformed numeric types before Rego, and checks expiry immediately before an execution claim; these are input/lifecycle guards.

A process-lifetime `flock` permits one process per state directory. One lock serializes all lifecycle changes through bounded provider IO, including revocation. A revocation accepted before an execution claim prevents dispatch; a revocation waiting behind an already dispatched operation cannot recall it. No SQLite transaction is held over HTTP. Incoming bodies are capped at 256 KiB, 100 total recipients, 20 attachments, 1,000-character identifiers and 128-character idempotency keys. IO timeouts are 2 seconds for OPA and 5 seconds for the provider per call; multiple attachments can accumulate these delays.

Review expires at the earlier of grant expiry or preparation plus 300 seconds. Accepted consent expires within 60 seconds, further capped by review expiry. Every execution rechecks current Rego and trusted time. After the durable execution intent is committed, it checks grant, review and consent deadlines again immediately before provider IO; expiry becomes a terminal denial with no dispatch or replay. This last local guard does not guarantee when a remote provider accepts an already in-flight request. Changed policy revision denies old pending consent with `policy_changed`; submit a new request for fresh review. Prepared email content is never refetched at approval.

The SQLite database owns grants, original request/input hashes, exact canonical snapshots, approvals and unique execution intents. `(agent, idempotency_key)` identifies replay; changed grant/action returns 409. Caller keys never become execution IDs. Execution intent is committed before provider IO. Definite synthetic 503 rejection becomes failed; connection loss or malformed effect success becomes unknown. Unknown is terminal: no implicit retry/reconciliation occurs. Recovery converts interrupted preparation to failed and interrupted execution to unknown. A crash after intent but before dispatch can therefore leave unknown with zero effects. A new caller key denotes new work, and cannot establish that an earlier unknown operation failed.

## Trust and limits

Fixture authentication, trusted broker/OPA/provider host processes, Rego files, SQLite state and real host wall clock are trusted. Agent HTTP fields and document text cannot create authority. The provider credential is never returned; the OPA private token is generated per run. No external account credentials, real email, payments or production providers are used.

All processes run as the same local OS user, so these tests **do not prove containment of arbitrary same-user code**. Deployment needs separate OS identities/process namespaces, restricted filesystem and provider network access, protected secrets, real human/agent identity, authenticated transport, supervision and retention/backup policy. Command-line fixture credentials and loopback HTTP are not a production identity solution. A supervisor must terminate the process group on forced shutdown; SIGKILL of the broker alone can orphan its OPA child. Normal SIGTERM waits for active handler completion and cleans the child/socket.

Order limits apply per operation, not to aggregate spending. Requested prices are synthetic inputs, not verified merchant quotations. Attachment authorization selects document IDs with version verification, not enterprise classification policy. Provider idempotency is a fixture property, not an exactly-once guarantee for arbitrary providers. Unknown effects require trusted investigation. SQLite and the lifecycle lock are intentionally single-host/single-process; distributed workers would require a new recovery/ordering design.

Tests additionally use trusted launch-only environment controls `B_BROKER_TEST_POLICY` (real alternative Rego file) and `B_BROKER_TEST_PAUSE` (`after_intent`/`after_effect`, marker plus SIGSTOP). These have no HTTP endpoint and do not grant an agent capabilities. They are local test instrumentation, consistent with the trusted host assumption.
