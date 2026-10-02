import dataclasses
import inspect
import itertools
import unittest

from starsea_continuum import thread_planning as planning


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
GENERATION_A = "a" * 32
DEVELOPER_DIGEST = "d" * 64
BACKEND = "backend-demo"


def turn(**changes):
    values = {
        "conversation": "101",
        "mode": "chat",
        "preset_id": "7",
        "history_revision": DIGEST_A,
        "head_message_id": "12",
        "current_user": "12",
        "previous_user": "11",
        "previous_backend": BACKEND,
        "operation_source": "send",
        "generation_id": GENERATION_A,
        "model": "model-demo",
        "channel": "text",
        "call_id": None,
        "continuity_epoch": 7,
        "fact_versions": None,
        "fact_signature": None,
        "fact_status": None,
        "context_window_id": None,
        "context_window_signature": None,
        "context_window_force_rebuild": False,
        "lineage": None,
    }
    values.update(changes)
    return planning.TurnMetadata(**values)


def state(**changes):
    values = {
        "conversation": "101",
        "mode": "chat",
        "preset_id": "7",
        "history_revision": DIGEST_B,
        "head_message_id": "11",
        "current_user": "11",
        "previous_user": "10",
        "previous_backend": BACKEND,
        "operation_source": "send",
        "generation_id": "b" * 32,
        "model": "model-demo",
        "completed": True,
        "updated": 100.0,
        "thread_id": "thread-demo-01",
        "developer_digest": DEVELOPER_DIGEST,
        "channel": "text",
        "call_id": None,
        "continuity_epoch": 7,
        "fact_versions": None,
        "fact_signature": None,
        "fact_status": None,
        "context_window_id": None,
        "context_window_signature": None,
        "turns": 0,
    }
    values.update(changes)
    return planning.ThreadStateEntry(**values)


def plan(metadata=None, stored=None, **changes):
    values = {
        "enabled": True,
        "metadata": turn() if metadata is None else metadata,
        "state": state() if stored is None else stored,
        "now": 101.0,
        "developer_digest": DEVELOPER_DIGEST,
        "accepted_backend": BACKEND,
    }
    values.update(changes)
    return planning.plan_thread_turn(**values)


def envelope(*, call=False, memory=True, active=False, **changes):
    value = {
        "schema": planning.CONTINUITY_SCHEMA,
        "conversation_id": "101",
        "mode": "chat",
        "preset_id": "7",
        "history_revision": DIGEST_A,
        "head_message_id": "12",
        "current_user_id": "12",
        "previous_user_id": "11",
        "previous_backend": BACKEND,
        "operation_source": "send",
        "generation_id": GENERATION_A,
        "continuity_epoch": 7,
        "channel": "text",
    }
    if call:
        value.update(
            channel="voice_call",
            call_id="call-demo-01",
            operation_source="speak",
        )
    if memory:
        value.update(
            fact_versions={},
            fact_signature=DIGEST_B,
            fact_status="explicit-unbound",
        )
    if active:
        value.update(
            context_window_id="window-demo-01",
            context_window_signature=DIGEST_C,
            context_window_force_rebuild=False,
        )
    value.update(changes)
    return value


class MetadataContractTests(unittest.TestCase):
    def test_single_schema_parses_every_optional_group_combination(self):
        for call, memory, active in itertools.product((False, True), repeat=3):
            with self.subTest(call=call, memory=memory, active=active):
                parsed = planning.parse_continuity_metadata(
                    envelope(call=call, memory=memory, active=active),
                    actual_model="model-demo",
                )
                self.assertEqual(parsed.schema, planning.CONTINUITY_SCHEMA)
                self.assertEqual(
                    parsed.channel, "voice_call" if call else "text"
                )
                self.assertEqual(
                    parsed.fact_signature is not None, memory
                )
                self.assertEqual(
                    parsed.context_window_signature is not None, active
                )
                self.assertEqual(parsed.continuity_epoch, 7)

    def test_unknown_schema_and_incomplete_shapes_are_rejected(self):
        full = envelope(call=True, memory=True, active=True)
        cases = [
            {**envelope(), "schema": "starsea.thread-continuity.v5"},
            {**envelope(), "schema": None},
        ]
        for field in ("continuity_epoch", "channel", "head_message_id"):
            cases.append(
                {k: v for k, v in envelope().items() if k != field}
            )
        for field in (
            "fact_status",
            "context_window_force_rebuild",
            "call_id",
        ):
            cases.append({k: v for k, v in full.items() if k != field})
        for value in cases:
            with self.subTest(value=sorted(value)):
                with self.assertRaises(planning.StateValidationError):
                    planning.parse_continuity_metadata(
                        value, actual_model="model-demo"
                    )

    def test_extra_body_field_is_rejected(self):
        with self.assertRaises(planning.StateValidationError):
            planning.parse_continuity_metadata(
                {**envelope(), "message_body": "synthetic-body"},
                actual_model="model-demo",
            )

    def test_malformed_identifiers_digests_and_operations_are_rejected(self):
        cases = (
            {"conversation_id": "conversation demo"},
            {"conversation_id": "-101"},
            {"current_user_id": "x" * 129},
            {"history_revision": "not-a-digest"},
            {"generation_id": "generation-demo-02"},
            {"operation_source": "unknown"},
            {"operation_source": ["send"]},
            {"fact_signature": "not-a-digest"},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                with self.assertRaises(planning.StateValidationError):
                    planning.parse_continuity_metadata(
                        envelope(**changes), actual_model="model-demo"
                    )

    def test_call_contract_is_explicit(self):
        cases = (
            envelope(call=True, operation_source="send"),
            envelope(operation_source="speak"),
            envelope(call_id="call-demo-01"),
            envelope(channel="video"),
            envelope(call=True, call_id="Bad Call"),
        )
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(planning.StateValidationError):
                    planning.parse_continuity_metadata(
                        value, actual_model="model-demo"
                    )

    def test_memory_versions_are_bounded_and_sorted(self):
        versions = {
            "profile.beta": DIGEST_B,
            "profile.alpha": DIGEST_A,
        }
        parsed = planning.parse_continuity_metadata(
            envelope(fact_versions=versions),
            actual_model="model-demo",
        )
        self.assertEqual(
            list(parsed.fact_versions),
            ["profile.alpha", "profile.beta"],
        )
        too_many = {f"profile.key_{index}": DIGEST_A for index in range(9)}
        with self.assertRaises(planning.StateValidationError):
            planning.parse_continuity_metadata(
                envelope(fact_versions=too_many),
                actual_model="model-demo",
            )

    def test_lineage_envelope_is_optional_bounded_and_validated(self):
        parsed = planning.parse_continuity_metadata(
            envelope(lineage_user_ids=["10", "9"]),
            actual_model="model-demo",
        )
        self.assertEqual(parsed.lineage, ("10", "9"))
        for lineage in (
            "10",
            ["valid", "bad id"],
            [str(index) for index in range(65)],
        ):
            with self.subTest(lineage=lineage):
                with self.assertRaises(planning.StateValidationError):
                    planning.parse_continuity_metadata(
                        envelope(lineage_user_ids=lineage),
                        actual_model="model-demo",
                    )


class PlannerActionTests(unittest.TestCase):
    def assert_plan(self, got, action, reason):
        self.assertEqual(got.action, action)
        self.assertEqual(got.reason_codes, (reason,))
        self.assertEqual(got.ephemeral, action == "ephemeral")
        self.assertEqual(got.include_history, action != "resume")

    def test_ephemeral_disabled_and_missing_or_malformed_metadata(self):
        self.assert_plan(
            planning.plan_thread_turn(
                enabled=False, metadata=None, state=None, now=0
            ),
            "ephemeral",
            "persistent_threads_disabled",
        )
        cases = (
            (None, "continuity_metadata_missing"),
            (object(), "continuity_metadata_invalid"),
            (turn(conversation=None), "continuity_metadata_invalid"),
            (turn(conversation="bad id"), "continuity_metadata_invalid"),
            (turn(operation_source=["send"]), "continuity_metadata_invalid"),
        )
        for metadata, reason in cases:
            with self.subTest(metadata=metadata):
                self.assert_plan(
                    planning.plan_thread_turn(
                        enabled=True,
                        metadata=metadata,
                        state=state(),
                        now=101,
                        developer_digest=DEVELOPER_DIGEST,
                    ),
                    "ephemeral",
                    reason,
                )

    def test_new_first_turn_and_conversation_mismatch(self):
        self.assert_plan(
            planning.plan_thread_turn(
                enabled=True,
                metadata=turn(previous_user=None),
                state=None,
                now=101,
                developer_digest=DEVELOPER_DIGEST,
            ),
            "new",
            "first_persistent_turn",
        )
        self.assert_plan(
            plan(metadata=turn(conversation="202")),
            "new",
            "conversation_mismatch",
        )

    def test_invalid_stored_state_fails_closed(self):
        for invalid in (
            state(thread_id="invalid thread id"),
            state(operation_source={"send": True}),
        ):
            with self.subTest(invalid=invalid):
                self.assert_plan(
                    plan(stored=invalid), "rebuild", "stored_state_invalid"
                )

    def test_developer_digest_must_be_present_and_equal(self):
        cases = (
            (state(developer_digest=None), DEVELOPER_DIGEST),
            (state(developer_digest=DIGEST_A), DEVELOPER_DIGEST),
            (state(), None),
        )
        for stored, current in cases:
            with self.subTest(current=current):
                self.assert_plan(
                    plan(stored=stored, developer_digest=current),
                    "rebuild",
                    "developer_instructions_changed",
                )

    def test_fact_baseline_change_and_malformed_pair(self):
        versions_a = {"profile.preference": DIGEST_A}
        versions_b = {"profile.preference": DIGEST_B}
        self.assert_plan(
            plan(
                metadata=turn(
                    fact_versions=versions_a,
                    fact_signature=DIGEST_A,
                )
            ),
            "rebuild",
            "fact_baseline_missing",
        )
        self.assert_plan(
            plan(
                metadata=turn(
                    fact_versions=versions_b,
                    fact_signature=DIGEST_B,
                ),
                stored=state(
                    fact_versions=versions_a,
                    fact_signature=DIGEST_A,
                ),
            ),
            "rebuild",
            "facts_changed",
        )
        self.assert_plan(
            plan(
                metadata=turn(fact_versions=versions_a),
                stored=state(fact_versions=versions_a),
            ),
            "rebuild",
            "fact_metadata_missing",
        )

    def test_context_window_baseline_invalidation_and_window_change(self):
        self.assert_plan(
            plan(metadata=turn(context_window_id="window-demo-01")),
            "rebuild",
            "context_window_baseline_missing",
        )
        self.assert_plan(
            plan(
                metadata=turn(
                    context_window_id="window-demo-01",
                    context_window_force_rebuild=True,
                ),
                stored=state(context_window_id="window-demo-01"),
            ),
            "rebuild",
            "context_window_invalidated",
        )
        self.assert_plan(
            plan(
                metadata=turn(context_window_id="window-demo-02"),
                stored=state(context_window_id="window-demo-01"),
            ),
            "rebuild",
            "context_window_changed",
        )

    def test_resume_failure_and_all_mutation_operations_rebuild(self):
        self.assert_plan(
            plan(resume_failed=True), "rebuild", "thread_resume_failed"
        )
        operations = (
            "regenerate",
            "edit",
            "delete",
            "resend",
            "mode_change",
            "preset_change",
            "call_start",
            "call_end",
        )
        for operation in operations:
            with self.subTest(operation=operation):
                self.assert_plan(
                    plan(metadata=turn(operation_source=operation)),
                    "rebuild",
                    f"operation_{operation}",
                )

    def test_epoch_completion_mode_channel_and_call_fences(self):
        cases = (
            (turn(continuity_epoch=8), state(), "continuity_epoch_changed"),
            (turn(), state(completed=False), "previous_turn_incomplete"),
            (turn(mode="review"), state(), "mode_changed"),
            (
                turn(channel="voice_call", call_id="call-demo-01", operation_source="speak"),
                state(),
                "channel_changed",
            ),
            (
                turn(channel="voice_call", call_id="call-demo-02", operation_source="speak"),
                state(channel="voice_call", call_id="call-demo-01", operation_source="speak"),
                "call_changed",
            ),
        )
        for metadata, stored, reason in cases:
            with self.subTest(reason=reason):
                self.assert_plan(
                    plan(metadata=metadata, stored=stored),
                    "rebuild",
                    reason,
                )

    def test_preset_model_regeneration_parent_and_history_fences(self):
        cases = (
            (turn(preset_id="8"), "preset_changed"),
            (turn(model="model-demo-next"), "model_changed"),
            (
                turn(current_user="11", head_message_id="11"),
                "regenerated_user_turn",
            ),
            (turn(previous_user=None), "parent_metadata_missing"),
            (turn(head_message_id="13"), "head_message_mismatch"),
            (turn(history_revision=DIGEST_B), "stale_history_revision"),
        )
        for metadata, reason in cases:
            with self.subTest(reason=reason):
                self.assert_plan(
                    plan(metadata=metadata), "rebuild", reason
                )

    def test_accepted_backend_missing_is_distinct_from_foreign_backend(self):
        for accepted in (None, "", "Backend-Demo", 7):
            with self.subTest(accepted=accepted):
                self.assert_plan(
                    plan(accepted_backend=accepted),
                    "rebuild",
                    "accepted_backend_missing",
                )
        got = plan(metadata=turn(previous_backend="other"))
        self.assert_plan(
            got, "catchup", "foreign_backend_intervening_turn"
        )
        self.assertEqual(got.thread_id, "thread-demo-01")
        self.assert_plan(
            plan(
                metadata=turn(previous_backend="any-provider"),
                accepted_backend="any-provider",
            ),
            "resume",
            "direct_continuation",
        )

    def test_lineage_catchup_and_gap_are_distinguished(self):
        got = plan(
            metadata=turn(previous_user="99", lineage=("11", "10"))
        )
        self.assert_plan(got, "catchup", "intervening_turns")
        self.assertEqual(got.thread_id, "thread-demo-01")
        self.assertTrue(got.include_history)
        self.assert_plan(
            plan(metadata=turn(previous_user="99", lineage=("10",))),
            "rebuild",
            "branch_or_history_gap",
        )

    def test_invalid_lineage_fails_as_invalid_continuity_metadata(self):
        cases = (
            "11",
            tuple(str(index) for index in range(65)),
            ("10", "bad id"),
        )
        for lineage in cases:
            with self.subTest(lineage=lineage):
                self.assert_plan(
                    plan(metadata=turn(lineage=lineage)),
                    "ephemeral",
                    "continuity_metadata_invalid",
                )

    def test_opaque_string_identifiers_can_resume(self):
        ids = {
            "conversation": "conv_7f3a9c2e-1b4d-4e8a-9f60-2c1d5e7a8b90",
            "preset_id": "preset:companion.v2",
        }
        stored = state(
            **ids,
            head_message_id="msg_01HZX",
            current_user="msg_01HZX",
            previous_user="msg_01HZW",
        )
        metadata = turn(
            **ids,
            head_message_id="msg_01HZY",
            current_user="msg_01HZY",
            previous_user="msg_01HZX",
        )
        got = plan(metadata=metadata, stored=stored)
        self.assert_plan(got, "resume", "direct_continuation")
        parsed = planning.parse_continuity_metadata(
            envelope(conversation_id="6f1c2e9a-uuid-like"),
            actual_model="model-demo",
        )
        self.assertEqual(parsed.conversation_id, "6f1c2e9a-uuid-like")

    def test_idle_boundary_is_strict_and_negative_limit_disables_expiry(self):
        self.assert_plan(
            plan(now=430.0001, idle_sec=330),
            "rebuild",
            "persistent_thread_idle",
        )
        self.assert_plan(
            plan(now=430, idle_sec=330),
            "resume",
            "direct_continuation",
        )
        self.assertEqual(
            plan(now=999999, idle_sec=-1).action,
            "resume",
        )

    def test_rollover_input_validation_fails_closed(self):
        cases = (
            {"max_turns": True},
            {"max_turns": -1},
            {"context_tokens": True, "context_window": 10, "capacity_ratio": 0.5},
            {"context_tokens": -1, "context_window": 10, "capacity_ratio": 0.5},
            {"context_tokens": 1, "context_window": True, "capacity_ratio": 0.5},
            {"context_tokens": 1, "context_window": 0, "capacity_ratio": 0.5},
            {"context_tokens": 1, "context_window": 10, "capacity_ratio": True},
            {"context_tokens": 1, "context_window": 10, "capacity_ratio": float("nan")},
            {"context_tokens": 1, "context_window": 10, "capacity_ratio": float("inf")},
            {"context_tokens": 1, "context_window": 10, "capacity_ratio": 0},
            {"context_tokens": 1, "context_window": 10, "capacity_ratio": 1.1},
            {"context_tokens": 1},
            {"context_window": 10, "capacity_ratio": 0.5},
            {"idle_sec": float("nan")},
            {"idle_sec": float("inf")},
            {"idle_sec": True},
        )
        for inputs in cases:
            with self.subTest(inputs=inputs):
                self.assert_plan(
                    plan(**inputs), "rebuild", "rollover_input_invalid"
                )

    def test_turn_and_capacity_rollover_boundaries(self):
        self.assert_plan(
            plan(stored=state(turns=3), max_turns=3),
            "rebuild",
            "turn_limit_reached",
        )
        self.assert_plan(
            plan(stored=state(turns=3), max_turns=0),
            "resume",
            "direct_continuation",
        )
        self.assert_plan(
            plan(
                context_tokens=80,
                context_window=100,
                capacity_ratio=0.8,
            ),
            "rebuild",
            "context_capacity_reached",
        )

    def test_post_model_decision_order_covers_a_through_m(self):
        cases = (
            (turn(current_user="11", head_message_id="11"), {}, "regenerated_user_turn"),
            (turn(previous_user=None), {}, "parent_metadata_missing"),
            (turn(head_message_id="13"), {}, "head_message_mismatch"),
            (turn(history_revision=DIGEST_B), {}, "stale_history_revision"),
            (turn(), {"accepted_backend": None}, "accepted_backend_missing"),
            (turn(), {"max_turns": -1}, "rollover_input_invalid"),
            (turn(), {"now": 431.0, "idle_sec": 330}, "persistent_thread_idle"),
            (turn(), {"stored": state(turns=2), "max_turns": 2}, "turn_limit_reached"),
            (turn(), {"context_tokens": 1, "context_window": 2, "capacity_ratio": 0.5}, "context_capacity_reached"),
            (turn(previous_backend="other"), {}, "foreign_backend_intervening_turn"),
            (turn(), {}, "direct_continuation"),
            (turn(previous_user="99", lineage=("11",)), {}, "intervening_turns"),
            (turn(previous_user="99", lineage=("10",)), {}, "branch_or_history_gap"),
        )
        for metadata, inputs, reason in cases:
            with self.subTest(reason=reason):
                got = plan(metadata=metadata, **inputs)
                expected = (
                    "catchup"
                    if reason in {
                        "foreign_backend_intervening_turn",
                        "intervening_turns",
                    }
                    else "resume" if reason == "direct_continuation" else "rebuild"
                )
                self.assert_plan(got, expected, reason)

    def test_direct_continuation_resumes_only_the_bound_thread(self):
        got = plan()
        self.assert_plan(got, "resume", "direct_continuation")
        self.assertEqual(got.thread_id, "thread-demo-01")

    def test_status_and_active_signature_are_not_independent_rebuild_inputs(self):
        versions = {"profile.preference": DIGEST_A}
        stored = state(
            fact_versions=versions,
            fact_signature=DIGEST_A,
            fact_status="status-before",
            context_window_id="window-demo-01",
            context_window_signature=DIGEST_A,
        )
        metadata = turn(
            fact_versions=versions,
            fact_signature=DIGEST_A,
            fact_status="status-after",
            context_window_id="window-demo-01",
            context_window_signature=DIGEST_B,
        )
        self.assertEqual(
            plan(metadata=metadata, stored=stored).action,
            "resume",
        )


class CompletedStateTests(unittest.TestCase):
    def test_completed_state_requires_explicit_time_and_preserves_metadata(self):
        metadata = turn(
            fact_versions={"profile.preference": DIGEST_A},
            fact_signature=DIGEST_B,
            fact_status="current",
            context_window_id="window-demo-01",
            context_window_signature=DIGEST_C,
        )
        completed = planning.completed_state(
            metadata,
            thread_id="thread-demo-01",
            updated=123.5,
        )
        self.assertTrue(completed.completed)
        self.assertEqual(completed.updated, 123.5)
        self.assertEqual(completed.current_user, "12")
        self.assertEqual(completed.fact_signature, DIGEST_B)
        self.assertEqual(completed.context_window_id, "window-demo-01")
        self.assertIsNone(completed.developer_digest)
        self.assertEqual(completed.turns, 1)

    def test_completed_state_binds_developer_digest_for_resume(self):
        completed = planning.completed_state(
            turn(),
            thread_id="thread-demo-01",
            updated=100.0,
            developer_digest=DEVELOPER_DIGEST,
        )
        self.assertEqual(completed.developer_digest, DEVELOPER_DIGEST)
        next_turn = turn(
            history_revision=DIGEST_B,
            head_message_id="13",
            current_user="13",
            previous_user="12",
        )
        self.assert_plan_resume(plan(metadata=next_turn, stored=completed))
        with self.assertRaises(planning.StateValidationError):
            planning.completed_state(
                turn(),
                thread_id="thread-demo-01",
                updated=100.0,
                developer_digest="not-a-digest",
            )

    def assert_plan_resume(self, got):
        self.assertEqual(got.action, "resume")
        self.assertEqual(got.reason_codes, ("direct_continuation",))
        self.assertEqual(got.thread_id, "thread-demo-01")

    def test_completed_state_has_no_hidden_clock_default(self):
        parameter = inspect.signature(planning.completed_state).parameters[
            "updated"
        ]
        self.assertIs(parameter.default, inspect.Parameter.empty)

    def test_state_mapping_is_allowlisted_and_backward_readable(self):
        raw = state().to_dict()
        legacy = {
            key: value
            for key, value in raw.items()
            if key not in planning.STATE_OPTIONAL_FIELDS
        }
        parsed = planning.ThreadStateEntry.from_dict(legacy)
        self.assertIsNone(parsed.developer_digest)
        self.assertIsNone(parsed.continuity_epoch)
        self.assertEqual(parsed.turns, 0)
        with self.assertRaises(planning.StateValidationError):
            planning.ThreadStateEntry.from_dict(
                {**raw, "host_runtime_payload": "synthetic"}
            )

    def test_completed_state_turns_follow_thread_identity(self):
        previous = state(turns=7)
        continued = planning.completed_state(
            turn(),
            thread_id="thread-demo-01",
            updated=101.0,
            previous=previous,
        )
        reset = planning.completed_state(
            turn(),
            thread_id="thread-demo-02",
            updated=101.0,
            previous=previous,
        )
        self.assertEqual(continued.turns, 8)
        self.assertEqual(reset.turns, 1)
        with self.assertRaises(planning.StateValidationError):
            planning.completed_state(
                turn(),
                thread_id="thread-demo-01",
                updated=101.0,
                previous=object(),
            )

    def test_turn_count_validation_is_bounded(self):
        for turns in (True, -1, 2**31):
            with self.subTest(turns=turns):
                with self.assertRaises(planning.StateValidationError):
                    state(turns=turns).validated()

    def test_equal_inputs_are_referentially_deterministic(self):
        first = plan()
        second = plan()
        self.assertEqual(first, second)
        self.assertTrue(dataclasses.is_dataclass(first))


if __name__ == "__main__":
    unittest.main()
