# Delegation standards and capability systems: evidence note

Research date: 2026-09-20. This note covers standards and credential systems, not the separate policy-engine, IAM-product, MCP, or agent-framework surveys. Primary source pages and relevant specification sections were read. Protocol support is not evidence that Gmail, a payment API, or another provider implements that protocol. No implementations were installed or tested.

## Strongest conclusion

There is no demonstrated need for a new authorization or delegation primitive. OAuth already delegates limited access; token exchange distinguishes the user from an acting service; rich authorization requests carry transaction details; UMA already distinguishes success, denial, and waiting for the resource owner's intervention. Capability systems already support delegation that can only narrow authority. A potentially useful project would integrate these ideas with a trusted executor, concrete action schemas, and approval state. That is an engineering hypothesis, not evidence that no existing integration supplies it.

## Stable protocols and their actual boundaries

| Mechanism | What it supplies | Approval and mediation | Remaining integration / bypass condition |
|---|---|---|---|
| OAuth 2.0 scopes | Owner-authorized, limited access by a client; scope semantics belong to the service. Not AI-specific. | Initial owner consent can establish delegated access. Read and write operations can both be authorized. | The resource server must enforce the grant. A client with another usable credential can ignore a separate wrapper. OAuth does not standardize each application's policy rules. |
| RFC 8693 token exchange | Exchange a token for another token appropriate to a downstream audience/scope; subject and actor can remain distinct. Not AI-specific. | No general human-approval workflow; authorization-server policy determines issuance. | Does not automatically make each new token narrower, propagate revocation, or validate a complete business delegation chain. Each deployment must impose those rules. |
| RFC 9396 rich authorization requests | Structured `authorization_details` for fine-grained consent, including API-specific fields. Not AI-specific. | The specification's payment example includes amount, currency, and creditor; authorization server and resource server jointly enforce consent. | Defines an extensible representation, not a universal email/calendar/payment ontology. Both servers must support the particular details type. |
| UMA 2.0 | Owner-managed resource permissions, authorization assessment, and permission tickets for asynchronous access. Not AI-specific. | Native success, `request_denied`, and `request_submitted`; the last explicitly requires owner intervention. `need_info` separately handles missing claims. | Strong conceptual overlap with the proposal, but policy administration and provider/resource integration remain implementation work. |

Sources and status: [OAuth 2.0, RFC 6749, October 2012, Standards Track](https://www.rfc-editor.org/rfc/rfc6749.html), [Token Exchange, RFC 8693, January 2020, Standards Track](https://www.rfc-editor.org/rfc/rfc8693.html), [Rich Authorization Requests, RFC 9396, May 2023, Standards Track](https://www.rfc-editor.org/rfc/rfc9396.html), [UMA 2.0 Grant, Kantara Recommendation, January 7, 2018](https://docs.kantarainitiative.org/uma/wg/rec-oauth-uma-grant-2.0.html). UMA is a Kantara recommendation, not an IETF RFC.

**Actor versus subject:** In the simple human-to-agent case, the human is the subject on whose behalf access is requested; the agent/service is the actor. RFC 8693 distinguishes this from impersonation, where the recipient sees the subject's identity within the token's authorized context. The JWT `act` claim can record an actor chain, but nested prior actors are informational: the RFC directs access-control evaluation to top-level claims and the current actor. An `act` history is therefore not itself proof that every predecessor approved the exact requested operation. The RFC also says token exchange does not intrinsically link output-token revocation to input-token revocation. [RFC 8693, §§1.1, 2.1, 4.1](https://www.rfc-editor.org/rfc/rfc8693.html)

**UMA is especially important counterevidence:** `request_submitted` returns a permission ticket and may include a polling interval while the resource owner intervenes. It is much closer to the proposed three-way outcome than a binary policy-engine response. It still does not provide a ready-made approval screen for a specific email's recipients and attachments; the concrete API request must be mapped into resources/scopes and owner policy. Resource servers must reject invalid or insufficient requesting-party tokens. [UMA, §§3.3.4–3.3.6, 3.5](https://docs.kantarainitiative.org/uma/wg/rec-oauth-uma-grant-2.0.html)

## Why provider integration still matters: Gmail

Google's current Gmail scope table documents `gmail.send`, account-level `gmail.readonly`, metadata access, and separate add-on scopes for the current message. It does not document an autonomous OAuth scope restricted to one label or an approved recipient list. Therefore, a label-filtered tool backed by an account-wide token relies on that tool's implementation to preserve the boundary; the label itself does not attenuate the token. This is an inference from the documented scope inventory, not a claim that no Google product can supply narrower access. [Gmail scopes, updated September 10, 2026](https://developers.google.com/workspace/gmail/api/auth/scopes)

The send endpoint takes the message and sends to its `To`, `Cc`, and `Bcc` recipients. An enforcement adapter must inspect the actual message that it will submit, including all recipient fields, rather than trusting a parallel `recipient` field claimed by the agent. [Gmail send API, updated April 15, 2026](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send)

Engineering implication: where upstream scopes are broader than the user's task grant, the upstream credential should stay in a separately protected executor. Its own agent-facing API can expose only selected message IDs, recipients, and supported actions. This moves trust into the executor; it does not eliminate trust or make the upstream token inherently narrower.

## Capabilities: existing restricted authority, not a new AI concept

For this investigation, a capability means a protected reference or credential that grants specific operations on a resource. Attenuation means deriving authority that is no broader than the original. Merely writing `scope="read"` in an agent-supplied object is not a capability: the resource/executor must validate who issued it and enforce its restrictions.

| System | Delegation and restrictions | Approval / context / action support | What would still be needed |
|---|---|---|---|
| Macaroons | Chained HMAC bearer credentials can be attenuated by adding caveats; first-party caveats are checked by the target, third-party caveats require discharge proofs. | Applicable to reads and writes. A discharge service can withhold proof until an approval condition is met; the credential construction does not supply the human workflow. | Shared-key handling, caveat semantics, request facts, revocation strategy, and an enforcing target. Retaining an unrestricted parent credential defeats a policy imposed only on a derivative. |
| Eclipse Biscuit | Signed credentials with public-key verification, offline attenuation, and existing Datalog-based checks/policies. | Concrete request facts can include operation, resource, time, and rights. An application still orchestrates human approval. | Provider integration, trusted contextual facts, credential isolation, and stateful constraints. Adds an existing policy language, so unnecessary if a basic application already uses OPA/Cedar and has no distributed-token need. |
| UCAN | Signed delegation chains between identified principals; separate delegation and invocation specifications, attenuated capabilities, validity bounds, and a revocation specification. | Can represent human-delegated authority when the human's issuer key/account is bound appropriately. Both read and write capabilities are possible. No universal human-approval UX is established by the core model. | Root trust and identity enrollment, operation semantics, executor integration, revocation distribution, and replay tracking. A service must accept and verify UCAN for it to constrain that service. |

[Macaroons, original NDSS 2014 paper](https://www.ndss-symposium.org/wp-content/uploads/2017/09/04_3_1.pdf); [Eclipse Biscuit introduction](https://doc.biscuitsec.org/getting-started/introduction); [UCAN core specification, README identifies Version 1.0.0](https://github.com/ucan-wg/spec). These are general distributed authorization mechanisms, not inherently AI-specific. The project documentation is a current snapshot, not an independent security assessment.

Macaroons explicitly discuss revocation through expiry, epoch counters, valid/invalid credential databases, and short-lived third-party checks. Thus decentralized verification does not imply instantaneous revocation without fresh information. [Macaroons paper, §V.E](https://www.ndss-symposium.org/wp-content/uploads/2017/09/04_3_1.pdf)

Biscuit has [Apache-2.0 Python bindings over its Rust library](https://github.com/eclipse-biscuit/biscuit-python); the README labels the API pre-1.0 and lists building, attenuating, parsing, authorizing, and querying tokens. It is a credible reuse/contribution candidate if the experiment discovers a need for portable attenuated credentials. Do not create a new signed-grant format merely to have one.

## Credential theft and replay are separate from action authorization

OAuth's current security BCP recommends minimum privilege, audience restriction, and sender-constrained access tokens such as mTLS or DPoP. Sender constraint limits misuse of a stolen token without the associated key; it does not stop compromised client software that can use both token and key. [RFC 9700, January 2025, BCP, §§2.2–2.3 and 4.10](https://www.rfc-editor.org/rfc/rfc9700.html)

DPoP binds a proof to the HTTP method and URI and can bind the access token. It does not, by default, sign an email body, payment amount, or the other request payload. A transaction-specific approval still needs application-level binding to the exact authorized action. [RFC 9449, September 2023, Standards Track, §§4.2–4.3](https://www.rfc-editor.org/rfc/rfc9449.html)

Design inference for a small experiment: load a grant by an authenticated owner/actor binding from trusted server state, materialize the exact action, authorize immediately before execution, and reserve/consume an approval or budget atomically with local execution state. A signed JSON grant alone supplies neither one-time use nor safe retries. Remote side effects still require provider idempotency support or reconciliation; a local database cannot guarantee exactly-once email delivery across crashes.

## Relevant IETF work: distinguish drafts from standards

| Document observed September 20, 2026 | Verified status / date | Why it matters |
|---|---|---|
| [Transaction Tokens, draft-ietf-oauth-transaction-tokens-11](https://datatracker.ietf.org/doc/draft-ietf-oauth-transaction-tokens/) | Active OAuth WG Internet-Draft; revision July 30, 2026; WG state “Waiting for Write-Up”; not an RFC. | Propagates user identity, workload identity, and authorization context through a call chain inside a trust domain. Useful context-preservation work, not a turnkey human approval service. |
| [Attenuated Delegation Profile for Automated Agents, draft-hamr-oauth-agent-delegation-01](https://datatracker.ietf.org/doc/draft-hamr-oauth-agent-delegation/) | Active individual Internet-Draft, September 2, 2026; no WG adoption shown. | Proposes checking each link's narrowing scope, expiry, and conditions across domains. A proposal to watch, not established interoperability. |
| [On-Behalf-Of User Authorization for AI Agents, draft-oauth-ai-agents-on-behalf-of-user-02](https://datatracker.ietf.org/doc/draft-oauth-ai-agents-on-behalf-of-user/) | Expired and archived individual draft; last revision August 25, 2025; expired status February 26, 2026. | Often discoverable as “OAuth for agents,” but must not be described as an active adopted standard. |

The first two documents' abstracts and Datatracker status were checked directly. An Internet-Draft can be submitted by anyone; an agent-related title is not evidence of IETF consensus, deployment, or security review.

## The remaining hypothesis to test

The plausible gap is reusable enforcement integration: turn a specific operation into trustworthy authorization facts, bind a delegated grant and any human approval to that operation, and execute it using credentials inaccessible to the agent. Context filtering is a read-side instance of mediation, and must occur before protected data reaches the model. An approval outcome is useful only if it leaves execution stopped until the required authority is obtained.

A library imported into the same unrestricted Python interpreter as attacker-controlled agent code does not establish this isolation. A model restricted to proposing tool calls is a different threat model from an agent allowed to run arbitrary code, read environment variables, or call network services directly. The latter needs an OS/process/container and credential boundary, or enforcement by the resource service itself. This is an architectural conclusion from the enforcement requirements above, not a guarantee supplied by any of the credential formats.

Novelty would have to be demonstrated in the integration contract and usable adapters. The three decision labels, a grant data class, and a signature format are already well covered conceptually.
