# Delegated execution: comparative development campaign

The user authorized three separately planned and implemented approaches, followed by independent review and comparison. The target is a generic open-source building block for developers. These experiments test engineering fit and bounded behavior; they do not establish market demand or production security.

- [Common experiment contract](EXPERIMENT.md)
- [Comparison, findings and lessons](COMPARISON.md)
- [A: embedded module plan](plans/A-embedded.md)
- [B: independent OPA broker plan](plans/B-broker.md)
- [C: Biscuit capability plan](plans/C-capability.md)
- [Shared test instrumentation](../../experiments/README.md)
- Reviews of the frozen baseline: [A and campaign assertions](reviews/A-review.md), [B and provider oracle](reviews/B-review.md), [C](reviews/C-review.md). Correction status and final evidence are tracked in the comparison.
- [Prior ecosystem investigation](../research/delegated-authority-investigation.md)

Planning and implementation are assigned to different agents. The common provider and black-box campaign are maintained separately from all three implementations. Reviewers will receive the same specification and inspect both functional/security behavior and test/maintenance quality. Findings are retained even when fixed.

All provider messages, documents, orders, identities and credentials are synthetic. Actual libraries/engines must be used. The side-effect oracle records downstream operations separately from authorization responses, including failure modes before acceptance and after acceptance without a response.

No Git repository is usable in this workspace. Review evidence therefore uses file hashes, test reports and a frozen source archive; no commit or publication is implied.

## Comparison questions fixed before results

1. Does the same common behavior work for both action domains and selected reads?
2. Which authority originates from verified identity, server state, policy data or signed credentials?
3. Can attacker-controlled proposal/approval fields change that authority?
4. What guarantees survive expiry, revocation, concurrency, restart and an ambiguous downstream result?
5. Which responsibilities does the reused project actually remove, and what glue remains?
6. What must a developer configure, deploy and maintain?
7. What would change under a truly compromised agent runtime rather than an HTTP adversary?
8. Does the evidence suggest adopting/contributing to an existing project, a narrow new module, or only an example integration?

The winner is not selected by code volume, test count, framework novelty or number of agents involved. Any proposed extraction must earn its interface through reduced caller responsibility and honest deployment assumptions.
