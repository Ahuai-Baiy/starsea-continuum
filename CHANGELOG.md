# Changelog

## v0.4.0 — 2026-10-02

Breaking rename. Decision logic, order, and the 35 rules are unchanged.

### Changed

- Fields renamed to neutral terms: `fact_versions`, `fact_signature`,
  `fact_status`, `context_window_id`, `context_window_signature`,
  `context_window_force_rebuild`.
- Reason codes renamed: `fact_baseline_missing`, `facts_changed`,
  `fact_metadata_missing`, `context_window_invalidated`,
  `context_window_baseline_missing`, `context_window_changed`.
- Envelope schema is now `starsea.continuum.thread.v2`.
- Docs use "current facts" and "context window" throughout;
  `docs/current-facts.md`, `decisions/D004-current-facts-correction.md`, and
  `examples/current-fact-correction.json` replace the old file names.


### Docs

- New guide: [What to carry into a fresh thread](docs/fresh-thread-context.md)
  — fresh instructions, current facts, a dated timeline, checkpoint and gap,
  and the recent tail, each bound to branch and epoch; budgets, what never to
  carry, and per-reason guidance.
- README clarifies that rollover is a decision; the host carries the context.

## v0.3.0 — 2026-10-02

### Added

- **`catchup` decision.** Keep the bound thread but send the turns it missed,
  instead of rebuilding it. Returned when the previous turn came from another
  backend (`foreign_backend_intervening_turn`), or when the host's `lineage`
  shows the stored turn is an ancestor on the same branch
  (`intervening_turns`).
- **Lineage input.** `TurnMetadata.lineage` / envelope group
  `lineage_user_ids`: ancestor user-message ids before `previous_user`,
  nearest first, at most 64.
- **Rollover limits.** `plan_thread_turn()` accepts `max_turns` and the
  `context_tokens` / `context_window` / `capacity_ratio` trio. New reasons:
  `turn_limit_reached`, `context_capacity_reached`,
  `rollover_input_invalid`.
- **Turn counting.** `ThreadStateEntry.turns`; `completed_state(previous=...)`
  increments it on the same thread and resets it on a new one.
- **Observation.** `plan_event()` and `summarize()` produce metadata-only plan
  records and resume-rate summaries; they cannot carry message text or thread
  ids.
- `examples/timeline_demo.py`: ten synthetic turns covering every decision.

### Changed

- A missing or invalid `accepted_backend` now reports
  `accepted_backend_missing`; a foreign previous backend now leads to
  `catchup` instead of `rebuild`.
- `idle_sec` is validated: NaN, infinity or non-numbers fail closed.
- The decision matrix has 35 rules.

## v0.2.0 — 2026-10-02

Breaking changes to the public preview. The planner's decision order is
unchanged; inputs, envelope shape and some reason codes changed.

### Changed

- **Provider-agnostic backend check.** `plan_thread_turn()` takes an
  `accepted_backend` label supplied by the host. Previously only one
  hardcoded backend label could ever resume. Missing or invalid values fail
  closed to `rebuild`, with reason code `foreign_backend_intervening_turn`.
- **One public envelope schema.** `parse_continuity_metadata()` accepts only
  `starsea.continuum.thread.v1`. The eight `starsea.thread-continuity.v1`…`v8`
  schemas from v0.1.0 are no longer accepted. Call, fact-version and context-window
  fields are optional groups that must be complete or absent.
- **Opaque identifiers.** Conversation, preset and message identifiers accept
  bounded opaque tokens (UUIDs, `msg_...`, numeric ids), not only numeric row
  ids.
- **Missing vs. invalid metadata.** Malformed turn metadata now reports
  `continuity_metadata_invalid`; `continuity_metadata_missing` is reserved for
  absent metadata. The decision matrix has 30 branches.

### Fixed

- `completed_state()` accepts `developer_digest`, so state built through the
  documented path can resume without a `dataclasses.replace()` workaround.
- A non-string `operation_source` now fails closed with
  `StateValidationError` instead of raising `TypeError`.

## v0.1.0 — 2026-10-01

Initial public preview: deterministic persistent-thread continuity planning.
