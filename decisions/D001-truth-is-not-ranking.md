# D001 — Truth Is Not Ranking

- Status: ACCEPTED
- Scope: Current-state authority versus retrieval and attention

## Context

Similarity and ranking answer which material may be useful. They do not establish
whether a historical statement remains current after supersession.

## Decision

Current facts and durable authority are resolved independently of retrieval
score. Ranking may order eligible material only within an explicitly accepted
selection contract.

## Why

Otherwise a highly similar obsolete state can outrank a valid current state and
cause temporal regression.

## Consequences

Historical items keep their time attribution. Current-state correction and
authority-store checks occur on separate, evidence-bound paths.

## Rejected alternatives

- Treat newest item as universally current.
- Treat highest similarity as current authority.
- Give checkpoint depth or age a permanent ranking bonus.

## Invariants protected

Truth != Ranking; Historical Truth != current facts; Relevance != Authority.
