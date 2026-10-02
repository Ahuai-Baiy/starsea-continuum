# Current facts

> **DESIGN DOCUMENT — implementation not included in public v0.4**

Historical truth and current facts are different dimensions. A statement may
accurately describe an earlier state and still be wrong as a current
instruction, preference, or decision. Similarity cannot settle that
distinction.

**Preserve historical truth without restoring superseded authority.**

Continuum validates continuity; it does not manufacture truth. The design does
not determine whether arbitrary statements are objectively correct.

## Design behavior

When selected historical material participates in a valid subject-and-scope
state chain, a consumer may attach a bounded, separately marked correction for
the resolved current state. The original historical statement remains intact.

Persistent-thread bindings need only bounded version/signature metadata, not
the private content that produced it. When that binding changes, the old thread
must not silently remain resumable.

## Synthetic example

```text
T1  delivery mode = manual
T2  delivery mode changes from manual to automatic
T3  a historical incident refers to the manual process
T4  retrieval selects the T3 incident
```

T3 remains legitimate historical truth. It is neither edited nor deleted. But
the current context must not imply that manual delivery is still current. If the
selected input connects to a valid state chain, it receives a separately marked
correction stating that the current delivery mode is automatic.

This is not a global “latest wins” rule. A correction requires the selected
input's valid subject-and-scope chain and fails closed when that binding cannot
be established.

## Limits

- It does not globally search for every possible correction.
- It does not make retrieved text authoritative.
- It does not rewrite historical records.
- It does not grant durable authority.

See [D004 — Current facts correction](../decisions/D004-current-facts-correction.md)
and the [synthetic correction example](../examples/current-fact-correction.json).
For integration scope, see the
[capability boundary](capability-boundary.md) and
[authority boundaries](authority-boundaries.md).
