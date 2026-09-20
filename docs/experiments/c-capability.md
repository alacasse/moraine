# C: signed, attenuated Biscuit capabilities

Experimental implementation of the [shared contract](EXPERIMENT.md).
It uses **biscuit-python 0.4.0** (the real Rust-backed `biscuit_auth` module),
CPython 3.13, SQLite, stdlib HTTP and httpx. Nothing substitutes for Biscuit's
signature chain, scoped Datalog evaluator or attenuation mechanism.

Source and local dependency directories: `experiments/c_capability/`.
Shell commands below start at the repository root.

## Run

Prerequisite: `uv` on PATH; this run used uv 0.11.6. `uv.lock` pins all Python
packages. First launch downloads the public CPython 3.13 runtime and packages;
later launches use the local environment. `.venv`, `.python` and `.uv-cache`
live in that source directory. No global install is needed.

Start the root-owned synthetic provider first, then run:

```bash
./experiments/c_capability/run.sh \
  --port 8762 --state-dir /tmp/moraine-c-example \
  --provider-url http://127.0.0.1:8761 --provider-token fixture-provider \
  --agent-token fixture-agent-alice --other-agent-token fixture-agent-bob \
  --human-token fixture-human-alice
```

The seven flags and HTTP routes implement the shared contract. `/health` only
succeeds after importing Biscuit, loading the durable key/database, acquiring
the exclusive state-directory lock and executing a real policy smoke test.
The provider origin must be loopback HTTP. All bearer tokens in this example
are synthetic fixture identities.

Run distinguishing tests or the common campaign from the repository root:

```bash
./experiments/c_capability/test.sh -q
campaign_dir=$(mktemp -d /tmp/moraine-exp-c.XXXXXX)
python3 experiments/run_campaign.py --approach c \
  --output "$campaign_dir"
```

Both commands exercise loopback sockets, which require the applicable sandbox
permission. Tests never use external account credentials or effects.

## Offline attenuation

`POST /grants` returns a parent capability. The state directory's `issuer.pub`
contains its public verification key. A client can narrow a parent credential
without any private key or issuer call:

```bash
experiments/c_capability/.venv/bin/python experiments/c_capability/attenuate.py \
  --public-key 'ed25519/<public-key-hex>' --max-amount 500 < client-input.json
```

`client-input.json` is `{"capability":"<parent>","action":{...}}`. The optional
`action` must be an exact common action. Supplying it binds the child to the
SHA-256 digest of that normalized action. Omitting it permits any order within
the narrowed amount and the parent's existing rights. Stdout is the child
capability. The helper appends genuine signed-chain restrictions:
`req:action("order.create")`, amount at most the limit, and optional input
digest. `issuer.key` is never an input. Parent possession still permits parent
rights; attenuation does not erase a parent's credential or transfer Alice's
authentication to Bob.

## Enforcement and lifecycle

Signed authority contains the grant, actor, account, audience, expiry, domains,
recipient/document/merchant rights, currency and caps. The executor constructs
facts from authenticated identity, host time and exact validated action fields.
Biscuit checks every ancestor restriction. Server checks/policies retain the
default authority+authorizer trust scope, excluding holder-added facts.
Dynamic values use library parameter binding, never string-built Datalog.

Domain decisions are real Datalog policies: selected document reads and orders
up to the automatic cap execute; emails and orders up to the hard cap require
human review. Python validates JSON types/shapes, enriches attachments and
owns state. Every To/Cc/Bcc recipient and attachment ID gets an authorization
check before provider access. Unknown action/identity/approval fields refuse.

Two digests intentionally differ. The input digest hashes exact validated
action JSON, with sorted object keys, compact separators and UTF-8 unescaped
Unicode; array order is preserved. The approval digest uses the same encoding
over the prepared snapshot, including actual attachment bytes. Approval never
refetches or replaces that snapshot. The review maximum age is **300 seconds**;
grant expiry, holder-added time checks, actor/account/audience binding,
revocation and current policy are rechecked before dispatch.
Every attachment read also repeats authorization immediately before that
provider call, so a slow earlier read cannot authorize a later expired read.

SQLite persists root revocation IDs, immutable grants, full private request
records, capability chains, input and prepared actions, digests, stable
execution IDs and outcomes. A unique `(authenticated actor, idempotency key)`
binds retries to the entire grant/action/capability submission. A lifecycle
lock serializes preparation, approvals, revocation and the bounded provider
call; an OS file lock prevents two executors owning one state directory.
Revocation linearizes before dispatch or after an already started dispatch.

Before effects, a dispatch reservation is committed. The provider call
is preceded by another authorization check **after** that commit,
including the review deadline when approved. If persistence consumed the
validity window, the reserved request becomes a terminal denial without
provider IO. A crash before persisting that denial still recovers as `unknown`.
This is a local preflight check; it does not guarantee the remote acceptance
time or remove the scheduling/network interval after the check.
Confirmed provider rejection becomes `failed`; lost/malformed success responses become `unknown`.
Restart converts unfinished dispatches to `unknown`. Unknown outcomes never
retry automatically. The root provider has durable execution-ID deduplication,
but this executor makes no general exactly-once claim.

The root key is generated by Biscuit and saved with mode 0600; the server uses
umask 077. Public responses expose neither issuer keys, provider credentials
nor stored capabilities. Approved snapshots are readable by the owning agent
and fixture human; Bob receives no Alice request data.

## Resource limits and scope

Tokens are limited to 32,768 encoded characters and eight blocks. Datalog
uses 2,048 facts, 32 iterations and 50 milliseconds. The library's live 0.4.0
API supplies `builder.limits()`; modify its fields and call `set_limits()`.
No `RunLimits` public class or dict-taking setter is assumed. JSON bodies are
bounded to 1 MiB, exact schema fields are required, and duplicate JSON fields,
nonfinite values and ambiguous framing are rejected.
Unpaired Unicode surrogates are rejected as invalid strings before canonical
hashing, policy construction or provider access.

Biscuit supplies cryptography, serialization, attenuation and scoped Datalog.
Custom code still supplies identity fixture mapping, schemas/facts/policy,
online revocation, approval state, snapshot digests, replay and recovery,
provider adapters, persistence and HTTP integration. A revoked token remains
valid for an offline verifier lacking fresh revocation state; tests demonstrate
that same token being rejected by the online executor.

These same-user process tests do not prove OS isolation, vault security,
production OAuth, multi-host locking or provider behavior outside the fixture.
A real deployment must prevent agent processes accessing executor state,
provider secrets and issuer keys. Order prices are synthetic inputs and caps
are per operation: no aggregate budget or trustworthy commercial quotation
claim. Datalog resource limits are not an overall HTTP concurrency or denial
of service defense. SQLite/state schema migration, signing-key rotation,
distributed revocation and unknown-outcome reconciliation are not implemented.

Evidence and deviations: [implementation note](C-implementation.md).
API references: [Biscuit Python basic use](https://python.biscuitsec.org/basic-use),
[safe Datalog parameters](https://python.biscuitsec.org/datalog),
[scoping reference](https://doc.biscuitsec.org/reference/datalog),
[pinned release files](https://pypi.org/project/biscuit-python/0.4.0/#files).
