"""Metadata-only observation helpers for deterministic thread plans."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .thread_planning import (
    PLAN_ACTIONS,
    StateValidationError,
    ThreadPlan,
    _SAFE_LABEL_RE,
    _safe_identifier,
    _safe_timestamp,
)


PLAN_EVENT_SCHEMA = "starsea.continuum.plan-event.v1"
PLAN_EVENT_METRICS = frozenset({
    "history_messages",
    "context_tokens",
    "context_window",
    "latency_ms",
    "thread_turns",
})
_MAX_METRIC = 2**31 - 1


def plan_event(
    plan: ThreadPlan,
    *,
    event_id: str,
    recorded_at: float,
    metrics: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return one bounded plan event without thread or message content."""
    if not isinstance(plan, ThreadPlan):
        raise StateValidationError("plan event requires a thread plan")
    if metrics is not None and not isinstance(metrics, Mapping):
        raise StateValidationError("plan event metrics must be a mapping")

    safe_metrics: dict[str, int] = {}
    for key, value in (metrics or {}).items():
        if (
            key in PLAN_EVENT_METRICS
            and not isinstance(value, bool)
            and isinstance(value, int)
        ):
            safe_metrics[key] = min(max(value, 0), _MAX_METRIC)

    return {
        "schema": PLAN_EVENT_SCHEMA,
        "event_id": _safe_identifier(event_id),
        "recorded_at": _safe_timestamp(recorded_at, "recorded_at"),
        "action": plan.action,
        "reason": plan.reason_codes[0],
        "include_history": plan.include_history,
        "metrics": safe_metrics,
    }


def summarize(
    events: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Aggregate valid plan events into deterministic action and reason counts."""
    actions: dict[str, int] = {}
    reasons: dict[str, int] = {}
    event_count = 0

    for event in events:
        if not isinstance(event, Mapping):
            continue
        action = event.get("action")
        reason = event.get("reason")
        if (
            event.get("schema") != PLAN_EVENT_SCHEMA
            or not isinstance(action, str)
            or action not in PLAN_ACTIONS
            or not isinstance(reason, str)
            or not _SAFE_LABEL_RE.fullmatch(reason)
        ):
            continue
        event_count += 1
        actions[action] = actions.get(action, 0) + 1
        reasons[reason] = reasons.get(reason, 0) + 1

    denominator = event_count - actions.get("ephemeral", 0)
    reusable = actions.get("resume", 0) + actions.get("catchup", 0)
    return {
        "events": event_count,
        "actions": dict(sorted(actions.items())),
        "reasons": dict(sorted(reasons.items())),
        "resume_rate": reusable / denominator if denominator else 0.0,
    }
