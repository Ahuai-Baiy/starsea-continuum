# Persistent-thread planning kernel

## Responsibility

Given a bounded continuity envelope, the last completed thread state and
explicit planning inputs, the kernel returns one deterministic host action:
`ephemeral`, `new`, `resume`, `catchup` or `rebuild`. It validates metadata
before any reuse decision and preserves one specific reason code for the first
decisive condition.

## Non-responsibilities

The kernel does not persist state, read a clock, create or resume provider
threads, execute tools, read prompts/messages, access a database, resolve
current facts, select context window evidence, or exercise memory or authority-store
decisions.
The host remains responsible for executing the returned plan.

## Input model

- `ContinuityMetadata`: a strictly allowlisted parsed envelope (see below).
- `TurnMetadata`: the smallest normalized turn identity used by planning.
- `ThreadStateEntry`: bounded state supplied by a host adapter, including the
  completed turn count for the current binding.
- explicit `enabled`, `now`, idle/turn/capacity rollover limits,
  resume-failure flag, current developer-instruction digest and the host's
  accepted backend label.

`TurnMetadata.lineage` contains up to 64 ancestor user-message identifiers
from the current branch, before `previous_user`, with the nearest first. It is
an input to planning only and is not stored in `ThreadStateEntry`.

Identifiers are bounded opaque tokens (numeric row ids, UUIDs and prefixed ids
are all accepted). Revisions, generations and state versions are fixed-shape
digests. Current facts and context window values are treated only as binding
metadata; their underlying authority
and selection logic is not implemented here.

## Continuity envelope

`parse_continuity_metadata()` accepts one public schema,
`starsea.continuum.thread.v2` (`CONTINUITY_SCHEMA`).

Required fields: `schema`, `conversation_id`, `mode`, `preset_id`,
`history_revision`, `head_message_id`, `current_user_id`, `previous_user_id`,
`previous_backend`, `operation_source`, `generation_id`, `continuity_epoch`,
`channel`. `head_message_id`, `previous_user_id` and `previous_backend` may be
`null` but must be present.

Optional groups, each either complete or absent:

- call: `call_id`, required when `channel` is `voice_call` and forbidden
  when it is `text`; call operations (`call_start`, `speak`, `call_end`) are
  only valid on `voice_call`;
- fact version: `fact_versions`, `fact_signature`,
  `fact_status`;
- context window: `context_window_id` (nullable),
  `context_window_signature`, `context_window_force_rebuild`.
- lineage: `lineage_user_ids`, a bounded list of ancestor user-message
  identifiers; when present, the one-field group is parsed into a tuple.

Any other field, partial group, or other schema name is rejected.

## Output model

`ThreadPlan` contains:

- action;
- whether full history is required;
- whether the turn is ephemeral;
- the reusable thread identifier only for `resume` and `catchup`;
- one reason code.

It contains no execution callback or side effect.

## Time and fail-closed rules

`now` and completed-state `updated` are mandatory caller inputs. The module has
no hidden wall clock. Missing turn metadata (`continuity_metadata_missing`) and
malformed turn metadata (`continuity_metadata_invalid`) both become a
full-history ephemeral plan; malformed stored state rebuilds. Missing
baselines, changed binding metadata, stale history and incomplete turns cannot
become resumable.

## Synthetic decision matrix

| # | First decisive condition | Action | Reason | Synthetic test |
| 1 | persistence disabled | ephemeral | `persistent_threads_disabled` | `test_ephemeral_disabled_and_missing_or_malformed_metadata` |
| 2 | metadata absent | ephemeral | `continuity_metadata_missing` | same |
| 3 | metadata present but malformed or unsupported | ephemeral | `continuity_metadata_invalid` | same |
| 4 | no stored state | new | `first_persistent_turn` | `test_new_first_turn_and_conversation_mismatch` |
| 5 | stored state invalid | rebuild | `stored_state_invalid` | `test_invalid_stored_state_fails_closed` |
| 6 | conversation differs | new | `conversation_mismatch` | `test_new_first_turn_and_conversation_mismatch` |
| 7 | developer digest missing or changed | rebuild | `developer_instructions_changed` | `test_developer_digest_must_be_present_and_equal` |
| 8 | current facts baseline presence differs | rebuild | `fact_baseline_missing` | `test_fact_baseline_change_and_malformed_pair` |
| 9 | current facts versions/signature changed | rebuild | `facts_changed` | same |
| 10 | current facts signature/version pair incomplete | rebuild | `fact_metadata_missing` | same |
| 11 | context window explicitly invalidated | rebuild | `context_window_invalidated` | `test_context_window_baseline_invalidation_and_window_change` |
| 12 | context window baseline presence differs | rebuild | `context_window_baseline_missing` | same |
| 13 | context window changed | rebuild | `context_window_changed` | same |
| 14 | previous resume attempt failed | rebuild | `thread_resume_failed` | `test_resume_failure_and_all_mutation_operations_rebuild` |
| 15 | operation is not `send` or `speak` | rebuild | `operation_<operation>` | same |
| 16 | epoch missing or changed | rebuild | `continuity_epoch_changed` | `test_epoch_completion_mode_channel_and_call_fences` |
| 17 | prior turn incomplete | rebuild | `previous_turn_incomplete` | same |
| 18 | mode changed | rebuild | `mode_changed` | same |
| 19 | channel changed | rebuild | `channel_changed` | same |
| 20 | call identity changed | rebuild | `call_changed` | same |
| 21 | preset changed | rebuild | `preset_changed` | `test_preset_model_regeneration_parent_and_history_fences` |
| 22 | model changed | rebuild | `model_changed` | same |
| 23 | current user repeats stored current user | rebuild | `regenerated_user_turn` | `test_post_model_decision_order_covers_a_through_m` |
| 24 | parent identity missing | rebuild | `parent_metadata_missing` | same |
| 25 | head differs from current user | rebuild | `head_message_mismatch` | same |
| 26 | history revision did not advance | rebuild | `stale_history_revision` | same |
| 27 | accepted backend missing or invalid | rebuild | `accepted_backend_missing` | `test_accepted_backend_missing_is_distinct_from_foreign_backend` |
| 28 | rollover input malformed or capacity inputs partial | rebuild | `rollover_input_invalid` | `test_rollover_input_validation_fails_closed` |
| 29 | explicit idle limit exceeded | rebuild | `persistent_thread_idle` | `test_idle_boundary_is_strict_and_negative_limit_disables_expiry` |
| 30 | enabled turn limit reached | rebuild | `turn_limit_reached` | `test_turn_and_capacity_rollover_boundaries` |
| 31 | enabled context-capacity ratio reached | rebuild | `context_capacity_reached` | same |
| 32 | direct parent was produced by another backend | catchup | `foreign_backend_intervening_turn` | `test_accepted_backend_missing_is_distinct_from_foreign_backend` |
| 33 | direct parent matches stored current user | resume | `direct_continuation` | `test_direct_continuation_resumes_only_the_bound_thread` |
| 34 | stored current user appears in non-empty lineage | catchup | `intervening_turns` | `test_lineage_catchup_and_gap_are_distinguished` |
| 35 | no direct or lineage continuity can be established | rebuild | `branch_or_history_gap` | same |

The operation family preserves eight distinct reason codes:
`operation_regenerate`, `operation_edit`, `operation_delete`,
`operation_resend`, `operation_mode_change`, `operation_preset_change`,
`operation_call_start`, and `operation_call_end`. No reasons are collapsed.

`catchup` preserves the returned thread binding while setting
`include_history=True`, so the host can supply turns the binding did not
observe. A successful completed state advances `turns`; using a different
thread identifier resets the count to one. `max_turns=0` disables turn-count
rollover. Capacity rollover is enabled only when `context_tokens`,
`context_window`, and `capacity_ratio` are all supplied.

context window signature and current facts status changes alone are intentionally
not independent rebuild inputs; their accepted binding keys remain the window
identity and current facts versions/signature respectively.

## Adapter boundary

Filesystem paths, permissions, atomic replacement, TTL/LRU retention, bridge
execution and provider thread lifecycle remain host-side. A
future adapter may translate its persisted state into these value objects; this
kernel does not prescribe a host storage implementation.

## Public verification

The implementation is project-authored and is not copied from vendor,
generated SDK or third-party source. All fixtures are synthetic and built from
the behavior contract above.

```text
contract_tests: 33
planner_branches_covered: 35/35
operation_reasons_covered: 8/8
```

Planning time and completed-state time are always explicit caller inputs.
