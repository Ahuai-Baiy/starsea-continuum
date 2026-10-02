# Architecture

## System problem

Continuity is the validity of recovered context across time, generations,
checkpoints, interruption, and persistent-thread reuse. It is not the same as
retrieval relevance or durable authority.

## Conceptual layers

### 1. Continuity / Representation

Representation describes enough ordered history to reconstruct a bounded prior
state. Its design contracts include temporal order, provenance, generation
identity, checkpoint identity, lineage, explicit gaps and recent tails.

It answers: **what recoverable material exists, and where did it come from?**

### 2. Recovery / Consumption

Recovery constructs a bounded package. Consumption validates that package again
against the current generation, temporal identity and ownership binding.

It answers: **is this material still valid for this owner and this attempt?**

The public v0.4 repository documents this layer but does not ship its recovery
kernel.

### 3. Attention / Distribution

This layer determines which eligible material may occupy current context.
Current facts correction and recent high-resolution context are documented as
separate mechanisms; a complete public attention/distribution implementation is
not included.

### 4. Compiler

The compiler remains a future design. If implemented, it may present an already
selected set of material to a target context budget. It must not silently become
a second ranker or authority source.

## Public implementation

The only implementation shipped in public v0.4 is the persistent-thread
planning kernel. Given bounded metadata and optional prior state, it decides
whether a host should:

- avoid persistence (`ephemeral`);
- create a binding (`new`);
- reuse a valid binding (`resume`);
- discard and reconstruct a binding (`rebuild`).

The kernel executes none of those actions. It has no storage, process,
provider, database or model access.

## Adoption and host boundary

Continuum defines contracts, not a required application stack. An integration
does not need components with particular names and does not need to reproduce
another system's architecture.

The public planner receives bounded metadata, validates continuity state and
returns an action plus reason code. The host owns provider calls, persistent
thread creation or replacement, storage, retries, context construction,
observability and application policy.

The kernel is provider-agnostic at the planning boundary. A host may sit in
front of hosted APIs, provider-side thread APIs, local models, self-hosted
inference or custom gateways when it can map its continuity semantics onto the
public contract. No vendor adapter is claimed by `v0.4`.

Maturity labels used by the project are:

- `SHIPPED` — working public implementation exists in this repository;
- `DOCUMENTED` — public design or contract exists, but implementation does not;
- `ROADMAP` — possible future work, not a delivery commitment.

## Authority flow

```text
historical events
      |
      v
representation and provenance
      |
      v
bounded recovery
      |
      v
temporal / generation validation
      |
      v
eligible context ------> current-state correction
      |
      v
attention / distribution
      |
      v
target context

durable authority remains independently resolved
```

## Failure posture

Continuum fails closed on stale temporal ownership. An invalid optional
contribution may be removed while ordinary safe context continues. Historical
records remain historically readable; invalidity prevents current use instead
of rewriting the past.

## Design invariants

- Truth != Ranking
- Deterministic Coverage != Relevance
- Representation != Consumption
- Consumption != Attention
- Historical Truth != current facts
- Recoverable Context != Durable Authority

See [authority boundaries](docs/authority-boundaries.md) and the
[architecture decisions](decisions/).
