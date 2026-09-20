# Delegated execution experiments

Three independent prototypes compare an embedded authorization module, an OPA execution broker, and Biscuit capabilities. The governing experiment is [the common contract](EXPERIMENT.md). Synthetic data only. None is production-ready.

See [the comparison and review findings](COMPARISON.md) for results, corrections and the proposed next integration experiment.

The root-owned downstream provider deliberately enforces only its service credential and idempotency; it does not enforce the agents' business grants. This lets the independent harness detect an implementation that returns a denial but still produces an effect.

Each approach is isolated in its own directory and dependency environment. Shared benchmark code is instrumentation, not a common authorization implementation. Local process tests do not establish OS isolation from malicious code running as the same user.

## Run the comparison

From the repository root, on Linux with Python 3.14 and `uv` installed:

```bash
bash experiments/a_embedded/setup.sh
campaign_dir=$(mktemp -d /tmp/moraine-exp-all.XXXXXX)
python3 experiments/run_campaign.py --approach all --output "$campaign_dir"
```

A installs its hash-locked dependencies explicitly. B downloads and verifies the pinned OPA binary and synchronizes its local Python environment on startup. C synchronizes its own Python 3.13 environment and pinned Biscuit binding. First installation needs access to public dependency hosts; execution requires local socket access. No real provider account or credentials are needed. See the [A](a-embedded.md), [B](b-broker.md) and [C](c-capability.md) guides for dependency and trust assumptions.

The runner launches the synthetic provider and each implementation, creates isolated temporary SQLite state and credentials, executes the same HTTP scenarios, records actual downstream effects/reads, and stops its processes. Reports contain case results, source hashes, effects and reads. Process logs are retained beside the report. Temporary application state is deleted on completion. Use a fresh output directory per run.

```bash
campaign_dir=$(mktemp -d /tmp/moraine-exp-b-case.XXXXXX)
python3 experiments/run_campaign.py --approach b --case provider_ambiguous_completion --output "$campaign_dir"
python3 -m unittest discover -s experiments/common -p 'test_*.py' -v
bash experiments/a_embedded/test.sh -q
bash experiments/b_broker/test.sh
bash experiments/c_capability/test.sh -q
```

The common campaign currently has 30 named scenarios per approach; one scenario includes 64 generated boundary samples. Those samples are not an additional 64 named tests. Local suites exercise each real policy dependency's distinct behavior. Elapsed/startup times include test orchestration and restarts and are not throughput or deployment benchmarks.

## Review baseline

```bash
python3 experiments/snapshot.py my-review-baseline
```

This creates an immutable-by-convention source archive and SHA-256 manifest in a new results directory. It excludes installed binaries, environments, caches, runtime state and earlier evidence. Dependency acquisition is recorded by each approach's lockfiles/bootstrap scripts. Source hashes identify what was tested; they are not an independent attestation.

The experimental HTTP credential scheme, same-user processes, per-operation order limits and synthetic order prices deliberately bound the evidence. Passing these tests does not establish production identity, OS containment, aggregate budget enforcement, real payment correctness or developer demand.

After the documentation migration, `run_campaign.py` hashes executable source
and the shared contract; it no longer encounters guides under `experiments/`.
Use `snapshot.py` for a source archive that also includes all guides and plans
under `docs/experiments/`. Earlier manifests retain their original paths and
hashes; see the [migration map](../documentation.md).
