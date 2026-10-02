# Companion AI integration guide

Persistent personal and companion AI systems often need both historical recall
and editable current state. The two must not be confused.

This guide is generic. It assumes no particular provider, memory system,
persona architecture, or application stack.

## The stale-state problem

Consider a fully synthetic preference:

```text
T1  daily_summary = true
T2  user changes daily_summary = false
T3  an old conversation still contains daily_summary = true
T4  retrieval selects the T3 conversation
```

The T3 statement is historically accurate: the preference once existed. It is
not currently authoritative after T2. A persistent system should remember that
the old preference existed without silently restoring it.

Continuum validates continuity; it does not decide whether arbitrary user text
is objectively true. Durable preference authority remains host-owned.

## Generic composition

```text
User
  |
  v
Application Host
  |-- Memory / retrieval (optional)
  |-- Durable state authority (optional)
  |-- Continuity metadata
  |        |
  |        v
  |   Continuum planner
  |        |
  |        v
  |   action + reason
  |
  `-- Provider / local model
```

Memory is optional. A vector database is optional. Provider-side threads are
implementation-specific. The host maps its own binding semantics onto the
planner contract.

Name and build your components however you like; the planner only sees the
metadata you pass in.

## Smallest usable v0.4 integration

1. Maintain bounded thread continuity metadata.
2. Persist the last completed planner state.
3. Call the planner before reusing a persistent binding.
4. Map the returned action into host behavior.
5. Persist the next completed state only after success.

That is enough to adopt the first public kernel. Recovery, current facts,
attention, and compiler implementations are not required.

## What the planner catches

Depending on supplied public-contract inputs, a prior binding may be rebuilt
when continuity epoch, model, preset, mode, channel, lineage, operation,
current-state version binding, or bounded context-window binding changes.

The planner does not inspect dialogue or rank memories. It needs bounded
metadata rather than raw content.

## Try the synthetic host

```bash
python examples/companion_host.py
```

The example uses an in-memory fake provider and demonstrates:

- first persistent turn → `new`;
- valid direct continuation → `resume`;
- continuity epoch change → `rebuild`.

It makes no model call, stores no conversation, and contains no personal data.

Next: [example source](../examples/companion_host.py),
[integration guide](integration-guide.md), and
[capability boundary](capability-boundary.md).
