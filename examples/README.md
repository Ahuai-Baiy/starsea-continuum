# Executable examples

These examples demonstrate how a host consumes planner decisions. They are
fully synthetic and use only the Python standard library plus the public
`starsea-continuum` package.

They do not:

- connect to a model or provider;
- use network, filesystem, environment variables, or credentials;
- persist conversations;
- contain private data.

## Minimal host

[`minimal_host.py`](minimal_host.py) constructs one valid stored binding and a
directly continuing turn. It prints the deterministic `resume /
direct_continuation` decision.

```bash
python examples/minimal_host.py
```

Expected output:

```text
action: resume
reason: direct_continuation
include_history: false
```

## Synthetic companion host

[`companion_host.py`](companion_host.py) provides a tiny in-memory fake host and
provider adapter. It demonstrates:

1. first turn → `new`;
2. direct continuation → `resume`;
3. continuity epoch change → `rebuild`.

```bash
python examples/companion_host.py
```

The planner returns decisions but performs no provider or persistence work. The
example host maps each action to its own fake execution method.

[`timeline_demo.py`](timeline_demo.py) walks through a deterministic synthetic
timeline with catchup, edit, idle, turn-limit, and capacity decisions.

Continue with [Getting Started](../docs/getting-started.md) and the
[Integration Guide](../docs/integration-guide.md).
