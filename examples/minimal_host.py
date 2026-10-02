"""Minimal offline host example for a valid persistent-thread continuation."""

from starsea_continuum import ThreadStateEntry, TurnMetadata, plan_thread_turn


DEVELOPER_DIGEST = "d" * 64
BACKEND = "backend-demo"


def build_plan():
    """Return one deterministic resume plan from synthetic bounded metadata."""
    stored = ThreadStateEntry(
        conversation="101",
        mode="chat",
        preset_id="7",
        history_revision="b" * 64,
        head_message_id="11",
        current_user="11",
        previous_user="10",
        previous_backend=BACKEND,
        operation_source="send",
        generation_id="b" * 32,
        model="model-demo",
        completed=True,
        updated=100.0,
        thread_id="thread-demo-01",
        developer_digest=DEVELOPER_DIGEST,
        continuity_epoch=7,
    )
    turn = TurnMetadata(
        conversation="101",
        mode="chat",
        preset_id="7",
        history_revision="a" * 64,
        head_message_id="12",
        current_user="12",
        previous_user="11",
        previous_backend=BACKEND,
        operation_source="send",
        generation_id="a" * 32,
        model="model-demo",
        continuity_epoch=7,
    )
    return plan_thread_turn(
        enabled=True,
        metadata=turn,
        state=stored,
        now=101.0,
        developer_digest=DEVELOPER_DIGEST,
        accepted_backend=BACKEND,
    )


def format_plan(plan) -> str:
    return "\n".join(
        (
            f"action: {plan.action}",
            f"reason: {plan.reason_codes[0]}",
            f"include_history: {str(plan.include_history).lower()}",
        )
    )


def main() -> None:
    print(format_plan(build_plan()))


if __name__ == "__main__":
    main()
