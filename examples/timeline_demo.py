"""Synthetic timeline covering continuation, catchup, and rollover plans."""

from starsea_continuum import (
    ThreadStateEntry,
    TurnMetadata,
    completed_state,
    plan_event,
    plan_thread_turn,
    summarize,
)


DEVELOPER_DIGEST = "d" * 64
BACKEND = "backend-demo"


class DemoProvider:
    """A deterministic in-memory provider with no external I/O."""

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


class DemoHost:
    """Execute plans in memory and retain only completed thread state."""

    def __init__(self) -> None:
        self.provider = DemoProvider()
        self.state: ThreadStateEntry | None = None

    def handle(self, turn: TurnMetadata, *, now: float, **rollover):
        plan = plan_thread_turn(
            enabled=True,
            metadata=turn,
            state=self.state,
            now=now,
            developer_digest=DEVELOPER_DIGEST,
            accepted_backend=BACKEND,
            **rollover,
        )
        if plan.action in {"resume", "catchup"}:
            thread_id = self.provider.resume_thread(plan.thread_id)
        else:
            thread_id = self.provider.create_thread()

        self.state = completed_state(
            turn,
            thread_id=thread_id,
            updated=now,
            developer_digest=DEVELOPER_DIGEST,
            previous=self.state,
        )
        return plan


def synthetic_turn(
    number: int,
    *,
    previous_user: str | None,
    previous_backend: str | None = BACKEND,
    lineage: tuple[str, ...] | None = None,
    operation_source: str = "send",
) -> TurnMetadata:
    marker = "abcdef1234"[number - 1]
    current_user = str(number)
    return TurnMetadata(
        conversation="conversation-demo",
        mode="chat",
        preset_id="preset-demo",
        history_revision=marker * 64,
        head_message_id=current_user,
        current_user=current_user,
        previous_user=previous_user,
        previous_backend=(
            previous_backend if previous_user is not None else None
        ),
        operation_source=operation_source,
        generation_id=marker * 32,
        model="model-demo",
        continuity_epoch=1,
        lineage=lineage,
    )


def run_demo() -> tuple[str, ...]:
    host = DemoHost()
    scenarios = (
        (synthetic_turn(1, previous_user=None), 101.0, {}),
        (synthetic_turn(2, previous_user="1"), 102.0, {}),
        (
            synthetic_turn(
                3, previous_user="2", previous_backend="backend-other"
            ),
            103.0,
            {},
        ),
        (synthetic_turn(4, previous_user="3"), 104.0, {}),
        (
            synthetic_turn(5, previous_user="missing-4", lineage=("4",)),
            105.0,
            {},
        ),
        (
            synthetic_turn(
                6, previous_user="5", operation_source="edit"
            ),
            106.0,
            {},
        ),
        (synthetic_turn(7, previous_user="6"), 107.0, {}),
        (synthetic_turn(8, previous_user="7"), 200.0, {"idle_sec": 10}),
        (synthetic_turn(9, previous_user="8"), 201.0, {"max_turns": 1}),
        (
            synthetic_turn(10, previous_user="9"),
            202.0,
            {
                "context_tokens": 80,
                "context_window": 100,
                "capacity_ratio": 0.8,
            },
        ),
    )

    lines = []
    events = []
    for number, (turn, now, rollover) in enumerate(scenarios, start=1):
        plan = host.handle(turn, now=now, **rollover)
        lines.append(
            f"turn {number}: {plan.action} / {plan.reason_codes[0]}"
        )
        events.append(
            plan_event(
                plan,
                event_id=f"event-demo-{number:02d}",
                recorded_at=now,
                metrics={"thread_turns": host.state.turns},
            )
        )

    summary = summarize(events)
    lines.append(f"resume_rate: {summary['resume_rate']:.2f}")
    lines.append(
        "actions: "
        + ", ".join(
            f"{action}={count}"
            for action, count in summary["actions"].items()
        )
    )
    return tuple(lines)


def main() -> None:
    print("\n".join(run_demo()))


if __name__ == "__main__":
    main()
