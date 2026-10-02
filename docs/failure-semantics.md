# Failure semantics

> When continuity validity is uncertain, Continuum prefers reconstruction over
> silent reuse.

This fail-closed posture applies specifically to persistent-binding reuse. It
does not convert every validation result into an application failure.

## Action outcomes

| Condition | Action | Meaning |
|---|---|---|
| Persistence disabled or usable metadata unavailable | `ephemeral` | Do not establish or reuse the persistent binding for this turn. |
| First valid persistent turn or continuity identity mismatch | `new` | Establish a fresh binding for the current continuity. |
| Existing binding passes all decisive checks | `resume` | The host may reuse the returned thread identifier. |
| Existing binding missed known intervening turns | `catchup` | Reuse the returned thread and supply the missing history. |
| Existing binding is stale, changed, invalid, or incompatible | `rebuild` | Do not reuse it as-is; reconstruct according to host policy. |

## Rebuild is not data destruction

`rebuild` means the prior persistent binding should not be reused as-is. It does
not automatically mean:

- model failure;
- conversation corruption;
- data loss or database corruption;
- a user-visible error;
- deletion of conversation history;
- erasure of memory or reset of a user.

The host chooses the reconstruction strategy. It may rebuild context from
available application state and establish a fresh provider or local binding.
[What to carry into a fresh thread](fresh-thread-context.md) describes a
layered approach that keeps the switch invisible to the person.

## Ephemeral is turn-scoped

`ephemeral` is a planning action for the current turn. It does not say that all
application data is ephemeral. It says the planner is not establishing or
reusing the persistent-thread binding for that turn.

## New is binding-scoped

`new` does not necessarily mean a new user conversation. It means the host
should establish a fresh persistent binding for the current continuity.

## Resume is validated reuse

`resume` is the strongest reuse result. It means the stored binding passed all
earlier decisive continuity checks. It is not proof that every statement inside
the provider thread is factually correct or currently authoritative.

## Catchup is reuse with history

`catchup` returns the validated existing binding but requires full history for
the current turn, allowing the host to supply known intervening turns.

## Reason codes

Each plan contains one reason code for the first decisive condition. Reason
codes are useful for logging, observability, debugging, and integration tests.
Use only documented meanings; see the
[35-branch decision matrix](thread-planning.md#synthetic-decision-matrix).

Log bounded identifiers and host correlation IDs when useful. Avoid raw
prompts, conversation bodies, credentials, or sensitive memory content.

Next: [integrate the action mapping](integration-guide.md#action-mapping).
