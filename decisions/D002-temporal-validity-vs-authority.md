# D002 — Temporal Validity vs Durable Authority

- Status: ACCEPTED
- Scope: Temporal continuity and durable-authority interfaces

## Context

A context reference can be temporally valid without possessing authority to
establish or revise a durable judgment.

## Decision

Continuum owns epoch, generation, checkpoint, active-head, and recoverable
context validity. A separate authority store owns durable judgment admission,
revision, revocation, and currentness.

## Why

Combining the roles would allow retrieval or repetition to promote text into
durable authority.

## Consequences

Authority-store contributions are re-resolved before use. Stale authority-bound
material is removed while ordinary safe context may continue.

## Rejected alternatives

- Let a Continuum summary establish a judgment.
- Treat an admitted judgment as valid across all generations without recheck.
- Merge project ownership because a bridge exists.

## Invariants protected

Continuum != authority store; Summary != Authority; authority fails closed.
