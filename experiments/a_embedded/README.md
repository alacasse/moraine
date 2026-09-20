# Embedded execution experiment

This directory is a trusted Python backend module plus a benchmark HTTP host. It
uses actual apparitor 0.1.1 and Cedarpy 4.8.7. It is not a production credential
vault, isolation boundary, aggregate budget system, or email provider integration.

From this directory, install the hash-locked dependencies locally:

```sh
./setup.sh
./test.sh -q
```

`setup.sh` requires `uv` and a compatible Python interpreter; this run used
CPython 3.14.7 on Linux x86-64. Caches and the environment remain in this directory.
The lock only installs public wheels; it does not compile Rust or install globally.
Tests require permission to create loopback sockets, including asyncio wakeups.

The common benchmark starts the host with synthetic fixture tokens:

```sh
./run.sh --port 8765 --state-dir ./example-state \
  --provider-url http://127.0.0.1:8766 --provider-token fixture-provider \
  --agent-token fixture-agent --other-agent-token fixture-other \
  --human-token fixture-human
```

The provider must already be running. Startup verifies provider connectivity and
credentials, validates Cedar policies, and acquires exclusive state ownership
before exposing `/health`. The HTTP interface is specified in
[`EXPERIMENT.md`](../../docs/experiments/EXPERIMENT.md).

To embed the module, place this directory on the trusted backend's import path.
The host constructs `Principal` **after authentication**. A model or request body
must never select its principal, provider token, policy files, state directory,
or current time. For example, from this directory:

```python
from pathlib import Path
from gate import ExecutionGate
from models import Principal
from provider import ProviderClient

async def trusted_tool_backend(state_dir, provider_url, provider_token,
                               authenticated_agent_id, authenticated_account,
                               grant_id, key, proposal):
    # Authenticate before calling this function; this fixture supports Alice/Bob.
    actor = Principal(kind="agent", id=authenticated_agent_id,
                      account=authenticated_account)
    gate = ExecutionGate(Path(state_dir), ProviderClient(provider_url, provider_token))
    try:
        return await gate.submit(actor, grant_id, key, proposal)
    finally:
        await gate.aclose()
```

A real host should keep one gate alive for its process lifetime and map account
from authenticated context, as `host.py` does. The other public operations are
`create_grant(human, spec)`, `inspect(actor, request_id)`,
`approve(human, request_id, action_digest)`, and `revoke(human, grant_id)`.
No caller separately authorizes and then reconstructs/executes an action.

`Refusal` carries a safe reason and HTTP-oriented status; Pydantic validation
errors mean malformed input. Outcomes contain a durable request ID, state and
safe reason. Review lasts at most 300 seconds. Unknown provider outcomes remain
unknown and cannot be retried or approved under another execution ID. Repeating
the same actor/idempotency key returns the stored outcome; changing its grant or
action conflicts. A new key is a distinct request, not an aggregate-budget check.

Grant expiry is checked before every attachment read. Grant/review deadlines are
checked again after durable dispatch reservation, before provider IO. These
checks govern local admission, not the time a remote provider accepts a request.

The benchmark host and provider run under one OS user. Passing their HTTP tests
does not contain code that can read that user's files, process arguments or
memory, or call the provider through a bypass added by a trusted developer.

See [`A-implementation.md`](../../docs/experiments/A-implementation.md) for measured
results, inherited versus custom responsibilities and deployment limitations.
