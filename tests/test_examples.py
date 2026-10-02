import contextlib
import io
import socket
import unittest
from unittest import mock

from examples import companion_host, minimal_host, timeline_demo


class MinimalHostExampleTests(unittest.TestCase):
    def test_plan_is_resume_direct_continuation(self):
        plan = minimal_host.build_plan()
        self.assertEqual(plan.action, "resume")
        self.assertEqual(plan.reason_codes, ("direct_continuation",))
        self.assertFalse(plan.include_history)

    def test_output_is_deterministic_and_offline(self):
        expected = (
            "action: resume\n"
            "reason: direct_continuation\n"
            "include_history: false\n"
        )
        for _ in range(2):
            output = io.StringIO()
            with mock.patch.object(
                socket,
                "socket",
                side_effect=AssertionError("network access is not allowed"),
            ), contextlib.redirect_stdout(output):
                minimal_host.main()
            self.assertEqual(output.getvalue(), expected)


class CompanionHostExampleTests(unittest.TestCase):
    def test_expected_action_sequence(self):
        self.assertEqual(
            companion_host.run_demo(),
            (
                "turn 1: new / first_persistent_turn -> thread-demo-01",
                "turn 2: resume / direct_continuation -> thread-demo-01",
                "turn 3: rebuild / continuity_epoch_changed -> thread-demo-02",
            ),
        )

    def test_output_is_deterministic_and_offline(self):
        expected = "\n".join(companion_host.run_demo()) + "\n"
        output = io.StringIO()
        with mock.patch.object(
            socket,
            "socket",
            side_effect=AssertionError("network access is not allowed"),
        ), contextlib.redirect_stdout(output):
            companion_host.main()
        self.assertEqual(output.getvalue(), expected)


class TimelineDemoTests(unittest.TestCase):
    def test_output_is_complete_deterministic_and_offline(self):
        expected = (
            "turn 1: new / first_persistent_turn\n"
            "turn 2: resume / direct_continuation\n"
            "turn 3: catchup / foreign_backend_intervening_turn\n"
            "turn 4: resume / direct_continuation\n"
            "turn 5: catchup / intervening_turns\n"
            "turn 6: rebuild / operation_edit\n"
            "turn 7: resume / direct_continuation\n"
            "turn 8: rebuild / persistent_thread_idle\n"
            "turn 9: rebuild / turn_limit_reached\n"
            "turn 10: rebuild / context_capacity_reached\n"
            "resume_rate: 0.50\n"
            "actions: catchup=2, new=1, rebuild=4, resume=3\n"
        )
        for _ in range(2):
            output = io.StringIO()
            with mock.patch.object(
                socket,
                "socket",
                side_effect=AssertionError("network access is not allowed"),
            ), contextlib.redirect_stdout(output):
                timeline_demo.main()
            self.assertEqual(output.getvalue(), expected)


if __name__ == "__main__":
    unittest.main()
