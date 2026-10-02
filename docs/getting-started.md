# Getting started

This tutorial introduces the `v0.4.0` persistent-thread planning kernel. It
takes about 5–10 minutes and requires only Python 3.11 or newer.

## What the planner does

The planner decides whether a host should treat the current turn as
`ephemeral`, establish a `new` persistent binding, `resume` a validated binding,
`catchup` missed history into it, or `rebuild` instead of reusing a stale
binding.

It validates bounded metadata. It does not call a model, create a provider
thread, store state, construct prompts, or execute any returned action.

## Install and run

```bash
git clone https://github.com/Ahuai-Baiy/starsea-continuum.git
cd starsea-continuum
python -m pip install -e .
python examples/minimal_host.py
python examples/companion_host.py
```

Both examples are synthetic, deterministic, and offline.

## Lifecycle

```text
turn arrives
    |
    v
host builds continuity metadata
    |
    v
plan_thread_turn(...)
    |
    v
ephemeral / new / resume / catchup / rebuild
    |
    v
host executes its own provider/context action
    |
    v
successful model turn
    |
    v
host stores completed continuity state
```

Provider or model execution is always host-side.

## Required inputs

`plan_thread_turn()` receives:

- `enabled`: whether persistent-thread planning is enabled for this turn;
- `metadata`: normalized `TurnMetadata` or parsed `ContinuityMetadata`;
- `state`: the last completed `ThreadStateEntry`, if one exists;
- `now`: an explicit host timestamp;
- `developer_digest`: the current developer-instruction digest;
- `accepted_backend`: the host's own lowercase backend label, the only backend
  allowed to have produced the previous turn of a resumable thread;
- optional idle, turn-count, context-capacity, and resume-failure inputs.

`max_turns` enables rollover after a binding reaches the supplied completed
turn count (`None` or `0` disables it). Context-capacity rollover requires all
three of `context_tokens`, `context_window`, and `capacity_ratio`. Optional
`lineage` carries up to 64 ancestor user-message identifiers, nearest first,
so the planner can recognize missed intervening turns without storing lineage.

Without a valid `developer_digest` and `accepted_backend`, the planner never
returns `resume`; it fails closed to `rebuild`.

Conversation, preset, and message identifiers are bounded opaque tokens
(letters, digits, `_`, `.`, `:`, `-`; up to 128 characters), so numeric row
ids, UUIDs, and prefixed ids such as `msg_01H...` all work. The
`current_user` / `previous_user` fields hold user-message identifiers, not
account identities.

The metadata includes bounded continuity identity such as conversation, mode,
preset, history revision, user-message lineage, operation, generation, model,
and continuity epoch. Optional current-state and context-window values are
version/signature bindings only. The planner does not need raw prompt or message
bodies.

See the complete [thread-planning contract](thread-planning.md).

## Persisted host state

The host persists the last successfully completed `ThreadStateEntry`. The state
contains the validated binding identity and provider thread identifier, not the
provider thread contents.

After the host successfully executes a turn, it can create the next state with
`completed_state()`, binding the developer-instruction digest that the next
plan will compare against:

```python
from starsea_continuum import completed_state

next_state = completed_state(
    turn_metadata,
    thread_id=host_thread_id,
    updated=host_timestamp,
    developer_digest=current_developer_digest,
    previous=current_state,
)
host_store.save(next_state.to_dict())
```

The storage interface in this example is conceptual. Continuum does not provide
or require a database.

## Call order

1. Receive a user turn.
2. Build bounded continuity metadata.
3. Load the last completed continuity state, if any.
4. Call `plan_thread_turn()`.
5. Inspect `action` and `reason_codes`.
6. Perform the host's own provider and context operation.
7. Only after success, store the next completed state.

Do not mark a turn complete before host execution succeeds.

## Action meanings

| Action | Meaning |
|---|---|
| `ephemeral` | No persistent binding is established or reused for this turn. Other application data is unaffected. |
| `new` | The host should establish a fresh binding for the current continuity. This does not necessarily mean a new user conversation. |
| `resume` | The stored binding passed every earlier decisive validation condition and may be reused by the host. This is not a factual endorsement of its contents. |
| `catchup` | Reuse the returned binding and include the missing intervening history in this turn. |
| `rebuild` | The prior binding is unsafe to reuse as-is. The host chooses how to reconstruct and establish a fresh binding — see [What to carry into a fresh thread](fresh-thread-context.md). |

When continuity validity is uncertain, the planner prefers reconstruction over
silent reuse. `rebuild` is a continuity decision, not automatically an
application error.

## Next steps

- Read the [integration guide](integration-guide.md) for a production host
  boundary and migration strategy.
- Use the [capability boundary](capability-boundary.md) to resolve scope
  questions.
- Review [failure semantics](failure-semantics.md) before mapping actions to
  user-visible behavior.
- Browse the [executable examples](../examples/README.md).
