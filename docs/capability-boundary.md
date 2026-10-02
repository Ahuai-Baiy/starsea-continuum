# Capability boundary

Starsea Continuum is a continuity-validity layer for persistent AI systems. It
keeps historical context recoverable while preventing stale state from silently
becoming present state.

Continuum validates continuity. It does not manufacture truth.

## What Continuum owns

Continuum defines contracts for:

- continuity, generation, thread, and binding validity;
- bounded identity required to validate reuse;
- deterministic continuity decisions from bounded metadata;
- fail-closed handling when reuse validity cannot be established;
- separation of temporal validity from relevance and authority.

## What Continuum does not own

Continuum does not own semantic ranking, durable belief or user-state
authority, provider execution, storage, application authorization, prompt
construction, or product policy.

It does not guarantee that retrieved content is factually correct or that an
upstream extractor interpreted source material correctly.

## What the v0.4 kernel can decide

The public planner can decide whether the current turn should be:

- `ephemeral` — no persistent binding for this turn;
- `new` — a fresh binding for this continuity;
- `resume` — reuse of a validated binding;
- `catchup` — reuse of a validated binding with missing history supplied;
- `rebuild` — reconstruction instead of unsafe reuse.

It can validate whether state remains valid for reuse without claiming that
every statement inside that state is objectively true.

## What the host must decide

The host decides how to execute an action. It owns provider calls, thread
lifecycle, context construction, persistence, retries, logging, authorization,
and application policy.

> The planner decides what should happen to continuity state; the host decides
> how that decision is executed.

## Truth vs validity

A context can be historically correct and still be temporally invalid.
Continuum can preserve a historical record while rejecting its reuse as current
state. It does not determine objective truth from arbitrary text or decide what
a user should believe.

## Retrieval vs authority

Retrieval does not confer authority. Relevance may select a historical item,
but a successful lookup cannot make a superseded item current or grant it
durable authority.

## Provider boundary

The kernel is provider-agnostic at the planning boundary. It calls no hosted
provider or local model. Hosts may map supported provider-side threads, local
inference, or custom gateways onto the contract; no universal provider
compatibility is claimed.

## Storage boundary

The kernel performs no filesystem or database I/O. Hosts select their own
storage and transaction model. The planner requires bounded metadata and state,
not raw prompts or conversation bodies.

## Non-goals

Starsea Continuum is not trying to become:

- a vector database or general RAG stack;
- an agent framework or workflow engine;
- a prompt-management platform or model router;
- a memory extractor or database abstraction layer;
- a provider SDK;
- a universal truth engine.

Narrow ownership is a feature of the architecture, not a missing checklist.

Next: [failure semantics](failure-semantics.md) or the
[integration guide](integration-guide.md).
