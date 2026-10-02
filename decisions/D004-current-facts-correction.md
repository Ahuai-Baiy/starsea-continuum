# D004 — Current facts correction

- Status: ACCEPTED
- Scope: Current facts correction design

## Context

Historical material must remain faithful to the time in which it occurred, but
selected history must not imply that a superseded state is still current.

## Decision

Preserve the historical statement unchanged. When an actually selected input
participates in a valid subject-and-scope state chain, attach a bounded, marked
current-state correction to model input. Store only bounded state-key digests in
persistent-thread metadata and invalidate the binding when the digest changes.

## Why

Overwriting history destroys provenance; ignoring supersession creates temporal
regression. Separate correction preserves both.

## Consequences

Resolution may fail closed when the selected-input chain cannot establish a
current state. The mechanism is not a global “latest wins” pass.

## Rejected alternatives

- Rewrite old records.
- Delete superseded history.
- Add a correction from unrelated, unselected context.

## Invariants protected

Historical Truth != current facts; source attribution; bounded refresh.
