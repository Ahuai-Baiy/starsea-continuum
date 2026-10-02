# Adoption path

Continuum can be adopted progressively. Only Stage 1 has a shipped public
implementation in `v0.4.0`.

## Stage 1 — Thread continuity planning

**Public maturity: SHIPPED**

**When you need it:** A host persists a provider/local thread binding and needs
to decide safely between `ephemeral`, `new`, `resume`, and `rebuild`.

**What you add:** Bounded turn metadata, last completed continuity state, one
planner call before reuse, host-side action mapping, and post-success state
storage.

**Continuum owns:** Validation and deterministic action/reason selection.

**Host owns:** Provider execution, reconstruction, persistence, retries,
context, observability, and policy.

Start with [Getting Started](getting-started.md).

## Stage 2 — Recovery and checkpoint validation

**Public maturity: DOCUMENTED**

**When you need it:** A larger system reconstructs bounded context from
checkpoints, gaps, or recent tails and must validate ownership before use.

**What you add:** An application-specific recovery package and consumption
boundary aligned with the public architecture.

**Continuum owns:** Documented recovery/consumption validity contracts.

**Host owns:** Storage, checkpoint construction, package transport, and model
execution.

No public recovery kernel ships in `v0.4.0`.

## Stage 3 — Current facts integration

**Public maturity: DOCUMENTED**

**When you need it:** Durable application or user state may be revised while old
conversation history remains retrievable.

**What you add:** A host-owned durable state authority and bounded
version/signature bindings where supported.

**Continuum owns:** Documented separation of historical truth, currentness, and
continuity validity.

**Host owns:** Discovering, resolving, admitting, and mutating durable state.

The current-facts consumer is not shipped in `v0.4.0`. See the
[Current facts design](current-facts.md).

## Stage 4 — Attention and distribution

**Public maturity: DOCUMENTED**

**When you need it:** A larger persistent system has more eligible context than
fits in the current model window.

**What you add:** Host-specific selection/distribution mechanisms and explicit
ownership boundaries.

**Continuum owns:** Documented separation between representation, consumption,
and attention.

**Host owns:** Ranking, allocation, retrieval, and model-context construction.

No general public attention/distribution implementation ships in `v0.4.0`.

## Stage 5 — Compiler

**Public maturity: ROADMAP**

**When you may need it:** A future system wants to present an already selected
set of material within a target context budget.

**What you add:** Nothing today; this is future design space.

**Continuum owns:** No shipped compiler contract in `v0.4.0`.

**Host owns:** All present compilation and context assembly.

ROADMAP means possible future work, not a delivery commitment.

## Composition, not stack replication

You do not need to reproduce the architecture of any other application.
Continuum defines contracts, not a required application stack. Adopt only the
stage that solves a real continuity problem in your host.

Next: [integration guide](integration-guide.md) or
[capability boundary](capability-boundary.md).
