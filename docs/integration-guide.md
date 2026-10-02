# Integration guide

This guide is for developers adding the public `v0.4` planner to an existing
host. Continuum defines contracts, not a required application stack.

## Integration contract

The host provides bounded turn metadata, optional last completed state, an
explicit timestamp, and applicable binding inputs. The planner validates those
inputs and returns a deterministic `ThreadPlan`.

The planner decides. The host executes.

## Host responsibilities

The host owns:

- provider calls and local-model execution;
- thread creation, reuse, replacement, and deletion policy;
- persistence and storage transactions;
- retries, timeouts, and failure recovery;
- prompt and context construction;
- application authorization and product policy;
- logging, metrics, and request correlation.

## Planner responsibilities

The planner:

- normalizes and validates bounded metadata;
- validates a supplied stored continuity state;
- checks continuity, lineage, mode, model, epoch, and optional bindings;
- returns exactly one action and one decisive reason code;
- exposes a thread identifier only for a valid `resume` or `catchup`;
- performs no I/O or side effects.

## State lifecycle

Call the planner before persistent-binding reuse. Store new completed state only
after the host operation succeeds.

```text
load state -> plan -> host executes -> success -> store completed state
                         |
                         +-> failure -> do not claim completion
```

`ThreadStateEntry.to_dict()` and `ThreadStateEntry.from_dict()` provide a
strictly allowlisted serialization boundary. Storage format, locking, atomicity,
retention, and encryption remain host decisions.

## Action mapping

| Planner action | Typical host mapping |
|---|---|
| `ephemeral` | Run without establishing or reusing the persistent thread binding. |
| `new` | Create a fresh provider/local binding, run the turn, then store completed state. |
| `resume` | Reuse `plan.thread_id`, run the turn, then store updated completed state. |
| `catchup` | Reuse `plan.thread_id`, include missing history, run the turn, then store updated state. |
| `rebuild` | Reconstruct context by host policy, create a fresh binding, run, then store state. |

The words describe continuity binding actions, not entire application or user
state. See [failure semantics](failure-semantics.md).

## Reason-code logging

`reason_codes` are suitable for observability, debugging, integration tests,
and carefully scoped host policy. Log the action, documented reason code,
bounded continuity epoch/version identifiers where appropriate, and a host
request correlation ID.

Do not log raw prompts, conversations, credentials, or sensitive memory
content merely to explain a planner result. The planner does not require raw
message bodies.

Reason codes are part of the documented contract, but hosts should not infer
new behavior from undocumented strings. The complete decision matrix lives in
the [thread-planning contract](thread-planning.md).

## Current-state version bindings

The planner can compare bounded current-state version/signature metadata. It
does not discover current facts, resolve a state chain, modify durable state,
read memory content, or decide semantic authority.

A host with its own durable state authority may provide the optional version
metadata supported by the public API. A host without such a system should not
invent one merely to use basic thread planning; follow the optional/baseline
semantics in the [public contract](thread-planning.md).

## Optional context window bindings

The planner can validate a bounded window identifier and explicit rebuild flag.
It does not rank evidence, select memories, construct a context window, or
perform semantic retrieval. A host does not need a component called a context
window to use the basic planner.

## Provider abstraction

The kernel is provider-agnostic at the planning boundary. A host may integrate
hosted LLM APIs, provider-side thread APIs, local models, self-hosted inference,
or custom gateways by mapping its own binding semantics onto the five actions.

No specific provider compatibility is claimed without a tested adapter.

## Persistence abstraction

Continuum does not require a database. A host may keep state in memory, a file,
a relational database, a key-value store, or another system, provided it can
load the last completed allowlisted state and update it after success.

The public examples intentionally use only in-memory synthetic state.

## Error handling

- Invalid turn metadata returns an `ephemeral` plan.
- Invalid stored state returns `rebuild`.
- Changed or stale binding inputs return `rebuild` with the first decisive
  reason.
- An actual host/provider failure remains a host error; it may be reported on a
  later planning call through supported inputs such as `resume_failed`.

Fail-closed behavior applies to continuity reuse. It is not a claim that every
host error can be recovered automatically.

## Testing strategy

Test your adapter at three levels:

1. unit-test metadata mapping and persisted-state round trips;
2. table-test action/reason mapping for host-relevant continuity changes;
3. integration-test that state is committed only after successful host work.

Use synthetic metadata. Block network access in planner and example tests where
practical. Keep provider adapter tests separate from the pure planning kernel.

## Migrating from resume-everything

Naive hosts often use stored-thread existence as the only reuse test:

```python
# Conceptual pseudocode
if stored_thread_id:
    resume(stored_thread_id)
else:
    create_thread()
```

Existence alone is insufficient evidence for safe reuse. Add planning first:

```python
# Conceptual pseudocode
plan = plan_thread_turn(...)

if plan.action == "resume":
    host.resume(plan.thread_id)
elif plan.action == "catchup":
    host.resume_with_history(plan.thread_id)
elif plan.action == "new":
    host.create()
elif plan.action == "rebuild":
    host.reconstruct_and_create()
else:
    host.run_ephemeral()
```

Start with the [minimal integration tutorial](getting-started.md), then adapt
the fully synthetic [companion host example](../examples/companion_host.py).
