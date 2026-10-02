import unittest

from starsea_continuum import (
    PLAN_EVENT_SCHEMA,
    StateValidationError,
    ThreadPlan,
    plan_event,
    summarize,
)


def plan(action="resume", reason="direct_continuation"):
    return ThreadPlan(
        action=action,
        include_history=action != "resume",
        ephemeral=action == "ephemeral",
        thread_id="thread-demo-01" if action in {"resume", "catchup"} else None,
        reason_codes=(reason,),
    )


class PlanEventTests(unittest.TestCase):
    def test_event_shape_is_fixed_and_cannot_carry_thread_identity(self):
        event = plan_event(
            plan(),
            event_id="event-demo-01",
            recorded_at=123.5,
            metrics={
                "history_messages": 12,
                "context_tokens": -3,
                "context_window": 2**40,
                "latency_ms": True,
                "message_body": 99,
            },
        )
        self.assertEqual(
            set(event),
            {
                "schema",
                "event_id",
                "recorded_at",
                "action",
                "reason",
                "include_history",
                "metrics",
            },
        )
        self.assertNotIn("thread_id", event)
        self.assertEqual(
            event["metrics"],
            {
                "history_messages": 12,
                "context_tokens": 0,
                "context_window": 2**31 - 1,
            },
        )

    def test_invalid_plan_identity_time_and_metrics_shape_are_rejected(self):
        cases = (
            {"plan": object()},
            {"event_id": "bad id"},
            {"recorded_at": float("nan")},
            {"metrics": []},
        )
        for changes in cases:
            inputs = {
                "plan": plan(),
                "event_id": "event-demo-01",
                "recorded_at": 1.0,
            }
            inputs.update(changes)
            with self.subTest(changes=changes):
                with self.assertRaises(StateValidationError):
                    plan_event(**inputs)


class SummarizeTests(unittest.TestCase):
    def event(self, action, reason, number):
        return plan_event(
            plan(action, reason),
            event_id=f"event-demo-{number}",
            recorded_at=float(number),
        )

    def test_counts_are_sorted_and_resume_rate_includes_catchup(self):
        events = [
            self.event("resume", "direct_continuation", 1),
            self.event("catchup", "intervening_turns", 2),
            self.event("rebuild", "operation_edit", 3),
            self.event("ephemeral", "persistent_threads_disabled", 4),
            {"schema": "wrong", "action": "resume", "reason": "ignored"},
            {"schema": PLAN_EVENT_SCHEMA, "action": "unknown", "reason": "ignored"},
        ]
        summary = summarize(events)
        self.assertEqual(summary["events"], 4)
        self.assertEqual(
            summary["actions"],
            {"catchup": 1, "ephemeral": 1, "rebuild": 1, "resume": 1},
        )
        self.assertEqual(list(summary["reasons"]), sorted(summary["reasons"]))
        self.assertEqual(summary["resume_rate"], 2 / 3)

    def test_events_with_free_text_reasons_are_skipped(self):
        good = self.event("resume", "direct_continuation", 1)
        forged = {**good, "reason": "user said: some private message"}
        summary = summarize([good, forged])
        self.assertEqual(summary["events"], 1)
        self.assertEqual(list(summary["reasons"]), ["direct_continuation"])

    def test_zero_non_ephemeral_denominator_returns_zero(self):
        summary = summarize(
            [self.event("ephemeral", "persistent_threads_disabled", 1)]
        )
        self.assertEqual(summary["resume_rate"], 0.0)
