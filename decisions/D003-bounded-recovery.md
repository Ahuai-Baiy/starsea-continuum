# D003 — Bounded Recovery

- Status: ACCEPTED
- Scope: Bounded representation and consumption

## Context

Unbounded recovery is difficult to audit and can hide missing regions,
fabricated checkpoints, uncontrolled recursion, or partial coverage claims.

## Decision

Recovery remains bounded by explicit lineage, gap and tail semantics, declared
size limits, and fail-closed correction. No silent truncation, fabricated
checkpoint, partial deterministic credit or implicit recursive extension is
accepted.

## Why

An explicit bound makes both completeness claims and failures testable.

## Consequences

Some histories remain denied rather than receiving an approximate package.
Representation and consumption remain separate stages.

## Rejected alternatives

- Silent truncation.
- Arbitrary recursive summaries.
- Giving partial credit to an invalid deterministic representation.

## Invariants protected

Bounded deterministic representation; provenance; fail-closed consumption.
