# Frequently asked questions

## Is Starsea Continuum a memory system?

No. It validates continuity and reuse boundaries. A memory system may provide
historical material, but recall and continuity validity are different jobs.

## Is it a RAG framework?

No. RAG retrieves relevant material. Continuum asks whether recovered or bound
state still belongs to the current continuity and may safely be reused.

## Does it decide what is objectively true?

No. Continuum validates continuity; it does not manufacture truth. It can reject
stale reuse without certifying every statement inside a context.

## Does it store my conversations?

No. The public kernel performs no storage or filesystem I/O and does not require
raw message bodies.

## Does it call my model provider?

No. It returns a plan. The host owns provider or local-model execution.

## Does it require a database?

No. The host chooses how, or whether, to persist completed continuity state.

## Does it require a vector database?

No. Vector retrieval is optional and outside the planner's ownership.

## Does it require an authority store, scheduler, or context window?

No. Those names describe optional generic roles in the architecture
documents. Basic `v0.4` thread planning does not require any of them.

## Can I use only the thread planner?

Yes. Stage 1 is a standalone public kernel with zero runtime dependencies.

## Can I use it in a companion AI?

Yes, when the host needs persistent-binding validity. See the generic
[companion AI guide](companion-ai-guide.md).

## Can I use it with a local model?

Yes, if the host maps its binding semantics to the public contract. No tested
local-model adapter is claimed.

## Can I use it with a hosted provider?

Yes at the planning boundary, subject to the same mapping requirement. The
project does not claim verified compatibility with every provider.

## What does rebuild mean?

The prior binding is not safe to reuse as-is. The host decides how to
reconstruct. It does not mean conversation deletion, data loss, or model
failure.

## What does catchup mean?

The existing binding remains valid, but it missed known intervening turns. The
host reuses that binding while supplying the missing history for this turn.

## Why not resume any stored thread?

A stored identifier proves existence, not current validity. Mode, model,
lineage, epoch, operation, or other bindings may have changed.

## Are current facts implemented in v0.4?

No. Current facts are `DOCUMENTED`. The planner can compare optional bounded
version bindings, but it does not discover, resolve, or mutate durable state.

## Is the project production-ready?

No. `v0.4.0` is an experimental public preview and narrow reference
implementation of the first planning contract.

## Why are some architecture components documented but not shipped?

Architecture contracts clarify ownership and future composition. Only the
persistent-thread planner is `SHIPPED`; other areas are `DOCUMENTED` or
`ROADMAP` to keep delivery claims precise.

Start with [Getting Started](getting-started.md) or review the
[capability boundary](capability-boundary.md).
