"""Synthetic in-memory host showing new, resume, and rebuild decisions."""

from starsea_continuum import (
    ThreadStateEntry,
    TurnMetadata,
    completed_state,
    plan_thread_turn,
)


DEVELOPER_DIGEST = "d" * 64
BACKEND = "backend-demo"


class DemoProvider:
    """A deterministic fake provider; it makes no model or network call."""

    def __init__(self) -> None:
        self._counter = 0
        self._threads: set[str] = set()

    def create_thread(self) -> str:
        self._counter += 1
        thread_id = f"thread-demo-{self._counter:02d}"
        self._threads.add(thread_id)
        return thread_id

    def resume_thread(self, thread_id: str) -> str:
        if thread_id not in self._threads:
            raise ValueError("unknown demo thread")
        return thread_id

    def run_ephemeral(self) -> None:
        return None


class DemoHost:
    """Maps pure planner actions to fake provider behavior and in-memory state."""

    def __init__(self) -> None:
        self.provider = DemoProvider()
        self.state: ThreadStateEntry | None = None

    def handle(self, turn: TurnMetadata, *, now: float):
        plan = plan_thread_turn(
            enabled=True,
            metadata=turn,
            state=self.state,
            now=now,
            developer_digest=DEVELOPER_DIGEST,
            accepted_backend=BACKEND,
        )

        if plan.action in {"resume", "catchup"}:
            thread_id = self.provider.resume_thread(plan.thread_id)
        elif plan.action in {"new", "rebuild"}:
            # The host owns reconstruction and provider thread creation.
            thread_id = self.provider.create_thread()
        else:
            self.provider.run_ephemeral()
            return plan, None

        # Commit completed continuity state only after host execution succeeds.
        self.state = completed_state(
            turn,
            thread_id=thread_id,
            updated=now,
            developer_digest=DEVELOPER_DIGEST,
            previous=self.state,
        )
        return plan, thread_id


def synthetic_turn(
    *,
    current_user: str,
    previous_user: str | None,
    history_marker: str,
    continuity_epoch: int,
) -> TurnMetadata:
    return TurnMetadata(
        conversation="101",
        mode="chat",
        preset_id="7",
        history_revision=history_marker * 64,
        head_message_id=current_user,
        current_user=current_user,
        previous_user=previous_user,
        previous_backend=BACKEND if previous_user is not None else None,
        operation_source="send",
        generation_id=history_marker * 32,
        model="model-demo",
        continuity_epoch=continuity_epoch,
    )


def run_demo() -> tuple[str, ...]:
    host = DemoHost()
    turns = (
        synthetic_turn(
            current_user="1",
            previous_user=None,
            history_marker="a",
            continuity_epoch=1,
        ),
        synthetic_turn(
            current_user="2",
            previous_user="1",
            history_marker="b",
            continuity_epoch=1,
        ),
        synthetic_turn(
            current_user="3",
            previous_user="2",
            history_marker="c",
            continuity_epoch=2,
        ),
    )

    lines = []
    for number, turn in enumerate(turns, start=1):
        plan, thread_id = host.handle(turn, now=100.0 + number)
        lines.append(
            f"turn {number}: {plan.action} / {plan.reason_codes[0]}"
            f" -> {thread_id or 'none'}"
        )
    return tuple(lines)


def main() -> None:
    print("\n".join(run_demo()))


if __name__ == "__main__":
    main()
