"""Pure persistent-thread continuity metadata and planning.

The module validates bounded metadata and decides whether a host should avoid
persistence, create a thread, resume one, catch up missed history, or rebuild
it. It performs no I/O and does not execute any decision.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass


STATE_FIELDS = frozenset({
    "conversation",
    "mode",
    "preset_id",
    "history_revision",
    "head_message_id",
    "current_user",
    "previous_user",
    "previous_backend",
    "operation_source",
    "generation_id",
    "model",
    "completed",
    "updated",
    "thread_id",
})
STATE_OPTIONAL_FIELDS = frozenset({
    "developer_digest",
    "channel",
    "call_id",
    "continuity_epoch",
    "fact_versions",
    "fact_signature",
    "fact_status",
    "context_window_id",
    "context_window_signature",
    "turns",
})

CONTINUITY_SCHEMA = "starsea.continuum.thread.v2"

CONTINUITY_REQUIRED_FIELDS = frozenset({
    "schema",
    "conversation_id",
    "mode",
    "preset_id",
    "history_revision",
    "head_message_id",
    "current_user_id",
    "previous_user_id",
    "previous_backend",
    "operation_source",
    "generation_id",
    "continuity_epoch",
    "channel",
})
# Optional field groups: each group is either fully present or fully absent.
CALL_FIELDS = frozenset({"call_id"})
FACT_VERSION_FIELDS = frozenset({
    "fact_versions",
    "fact_signature",
    "fact_status",
})
CONTEXT_WINDOW_FIELDS = frozenset({
    "context_window_id",
    "context_window_signature",
    "context_window_force_rebuild",
})
LINEAGE_FIELDS = frozenset({"lineage_user_ids"})
_OPTIONAL_FIELD_GROUPS = (
    CALL_FIELDS,
    FACT_VERSION_FIELDS,
    CONTEXT_WINDOW_FIELDS,
    LINEAGE_FIELDS,
)

CONTINUITY_OPERATIONS = frozenset({
    "send",
    "regenerate",
    "edit",
    "delete",
    "resend",
    "mode_change",
    "preset_change",
    "call_start",
    "speak",
    "call_end",
})
CALL_OPERATIONS = frozenset({"call_start", "speak", "call_end"})
PLAN_ACTIONS = frozenset({
    "ephemeral", "new", "resume", "catchup", "rebuild"
})

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SAFE_LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9._:/+@-]{0,159}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_GENERATION_RE = re.compile(r"^[0-9a-f]{32}$")
_STATE_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_MAX_FACT_VERSION_KEYS = 8
_MAX_LINEAGE = 64
_MAX_COUNTER = 2**31 - 1


class StateValidationError(ValueError):
    """Raised when metadata is malformed, unbounded, or not allowlisted."""


def _raise_validation(message: str):
    raise StateValidationError(message)


def _safe_identifier(
    value: object, *, optional: bool = False
) -> str | None:
    if value is None and optional:
        return None
    if isinstance(value, bool):
        raise StateValidationError("boolean is not a valid metadata identifier")
    if isinstance(value, int):
        value = str(value)
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise StateValidationError(
            "identifiers must be bounded opaque tokens"
        )
    return value


def _safe_label(value: object, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not _SAFE_LABEL_RE.fullmatch(value):
        raise StateValidationError(
            "metadata label is not a bounded lowercase safe token"
        )
    return value


def _safe_epoch(value: object, *, optional: bool = False) -> int | None:
    if value is None and optional:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > 9_223_372_036_854_775_807
    ):
        raise StateValidationError(
            "continuity epoch must be a bounded non-negative integer"
        )
    return value


def _safe_timestamp(value: object, field_name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise StateValidationError(
            f"{field_name} must be a finite non-negative timestamp"
        )
    return float(value)


def _safe_lineage(
    value: object, *, optional: bool = True
) -> tuple[str, ...] | None:
    if value is None and optional:
        return None
    if not isinstance(value, (list, tuple)) or len(value) > _MAX_LINEAGE:
        raise StateValidationError(
            "lineage must be a bounded list or tuple of identifiers"
        )
    return tuple(_safe_identifier(item) for item in value)


def _safe_turns(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > _MAX_COUNTER
    ):
        raise StateValidationError(
            "thread turns must be a bounded non-negative integer"
        )
    return value


def _validate_rollover_inputs(
    *,
    idle_sec: object,
    max_turns: object,
    context_tokens: object,
    context_window: object,
    capacity_ratio: object,
) -> tuple[float, int | None, int | None, int | None, float | None]:
    if (
        isinstance(idle_sec, bool)
        or not isinstance(idle_sec, (int, float))
        or not math.isfinite(float(idle_sec))
    ):
        raise StateValidationError("idle limit must be a finite number")
    if max_turns is not None and (
        isinstance(max_turns, bool)
        or not isinstance(max_turns, int)
        or max_turns < 0
    ):
        raise StateValidationError(
            "maximum turns must be a non-negative integer"
        )

    capacity_values = (context_tokens, context_window, capacity_ratio)
    capacity_present = tuple(value is not None for value in capacity_values)
    if any(capacity_present) and not all(capacity_present):
        raise StateValidationError(
            "capacity rollover inputs must be provided together"
        )
    if all(capacity_present):
        if (
            isinstance(context_tokens, bool)
            or not isinstance(context_tokens, int)
            or context_tokens < 0
        ):
            raise StateValidationError(
                "context tokens must be a non-negative integer"
            )
        if (
            isinstance(context_window, bool)
            or not isinstance(context_window, int)
            or context_window <= 0
        ):
            raise StateValidationError(
                "context window must be a positive integer"
            )
        if (
            isinstance(capacity_ratio, bool)
            or not isinstance(capacity_ratio, (int, float))
            or not math.isfinite(float(capacity_ratio))
            or not 0 < float(capacity_ratio) <= 1
        ):
            raise StateValidationError(
                "capacity ratio must be finite and in the interval (0, 1]"
            )
        capacity_ratio = float(capacity_ratio)

    return (
        float(idle_sec),
        max_turns,
        context_tokens,
        context_window,
        capacity_ratio,
    )


def _safe_fact_versions(
    value: object, *, optional: bool = False
) -> dict[str, str] | None:
    if value is None and optional:
        return None
    if not isinstance(value, Mapping) or len(value) > _MAX_FACT_VERSION_KEYS:
        raise StateValidationError(
            "fact versions must be a bounded mapping"
        )
    result: dict[str, str] = {}
    for key, digest in value.items():
        if (
            not isinstance(key, str)
            or len(key) > 160
            or not _STATE_KEY_RE.fullmatch(key)
        ):
            raise StateValidationError("fact version state key is invalid")
        if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
            raise StateValidationError(
                "fact version must be a sha256 digest"
            )
        result[key] = digest
    return dict(sorted(result.items()))


@dataclass(frozen=True)
class ContinuityMetadata:
    schema: str
    conversation_id: str
    mode: str
    preset_id: str
    history_revision: str
    head_message_id: str | None
    current_user_id: str
    previous_user_id: str | None
    previous_backend: str | None
    operation_source: str
    generation_id: str
    actual_model: str
    channel: str = "text"
    call_id: str | None = None
    continuity_epoch: int | None = 0
    fact_versions: dict[str, str] | None = None
    fact_signature: str | None = None
    fact_status: str | None = None
    context_window_id: str | None = None
    context_window_signature: str | None = None
    context_window_force_rebuild: bool = False
    lineage: tuple[str, ...] | None = None


def _require_digest(value: object, message: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise StateValidationError(message)
    return value


def parse_continuity_metadata(
    value: Mapping[str, object], *, actual_model: str
) -> ContinuityMetadata:
    """Strictly parse an allowlisted metadata-only continuity envelope.

    The envelope uses the single public schema ``CONTINUITY_SCHEMA``. Required
    fields must all be present; each optional group (call, fact version,
    context window, lineage) must be either complete or absent. Unknown fields
    fail.
    """
    if not isinstance(value, Mapping):
        raise StateValidationError("continuity metadata must be a mapping")
    if value.get("schema") != CONTINUITY_SCHEMA:
        raise StateValidationError("unsupported continuity metadata schema")
    keys = set(value)
    if not CONTINUITY_REQUIRED_FIELDS <= keys:
        raise StateValidationError(
            "continuity metadata is missing required fields"
        )
    extra = keys - CONTINUITY_REQUIRED_FIELDS
    for group in _OPTIONAL_FIELD_GROUPS:
        present = extra & group
        if present and present != group:
            raise StateValidationError(
                "continuity metadata optional field group is incomplete"
            )
        extra -= group
    if extra:
        raise StateValidationError(
            "continuity metadata fields are not allowlisted"
        )

    operation = value["operation_source"]
    if (
        not isinstance(operation, str)
        or operation not in CONTINUITY_OPERATIONS
    ):
        raise StateValidationError("unknown continuity operation")
    revision = _require_digest(
        value["history_revision"], "history revision must be a sha256 digest"
    )
    generation = value["generation_id"]
    if not isinstance(generation, str) or not _GENERATION_RE.fullmatch(generation):
        raise StateValidationError("generation id must be a uuid4 hex token")

    channel = value["channel"]
    if channel == "voice_call":
        if "call_id" not in value:
            raise StateValidationError("voice_call continuity requires call_id")
        call_id = _safe_label(value["call_id"])
        if operation not in CALL_OPERATIONS:
            raise StateValidationError("call continuity operation is invalid")
    elif channel == "text":
        if "call_id" in value:
            raise StateValidationError(
                "text continuity must not carry call_id"
            )
        call_id = None
        if operation in CALL_OPERATIONS:
            raise StateValidationError(
                "call operation requires voice_call channel"
            )
    else:
        raise StateValidationError(
            "continuity channel must be text or voice_call"
        )

    memory_versions = memory_signature = memory_status = None
    if "fact_versions" in value:
        memory_versions = _safe_fact_versions(
            value["fact_versions"]
        )
        memory_signature = _require_digest(
            value["fact_signature"],
            "fact version signature must be a sha256 digest",
        )
        memory_status = _safe_label(value["fact_status"])

    active_window = active_signature = None
    active_force_rebuild = False
    if "context_window_signature" in value:
        active_window = _safe_label(
            value["context_window_id"], optional=True
        )
        active_signature = _require_digest(
            value["context_window_signature"],
            "context window signature must be a sha256 digest",
        )
        active_force_rebuild = value["context_window_force_rebuild"]
        if type(active_force_rebuild) is not bool:
            raise StateValidationError(
                "context window rebuild flag must be a boolean"
            )

    return ContinuityMetadata(
        schema=CONTINUITY_SCHEMA,
        conversation_id=_safe_identifier(value["conversation_id"]),
        mode=_safe_label(value["mode"]),
        preset_id=_safe_identifier(value["preset_id"]),
        history_revision=revision,
        head_message_id=_safe_identifier(
            value["head_message_id"], optional=True
        ),
        current_user_id=_safe_identifier(value["current_user_id"]),
        previous_user_id=_safe_identifier(
            value["previous_user_id"], optional=True
        ),
        previous_backend=_safe_label(value["previous_backend"], optional=True),
        operation_source=str(operation),
        generation_id=generation,
        actual_model=_safe_label(actual_model),
        channel=channel,
        call_id=call_id,
        continuity_epoch=_safe_epoch(value["continuity_epoch"]),
        fact_versions=memory_versions,
        fact_signature=memory_signature,
        fact_status=memory_status,
        context_window_id=active_window,
        context_window_signature=active_signature,
        context_window_force_rebuild=active_force_rebuild,
        lineage=_safe_lineage(
            value.get("lineage_user_ids"), optional=True
        ),
    )


@dataclass(frozen=True)
class TurnMetadata:
    conversation: str | int | None
    mode: str | None
    preset_id: str | int | None
    history_revision: str | None
    head_message_id: str | int | None
    current_user: str | int | None
    previous_user: str | int | None
    previous_backend: str | None
    operation_source: str | None
    generation_id: str | None
    model: str | None
    channel: str | None = "text"
    call_id: str | None = None
    continuity_epoch: int | None = 0
    fact_versions: dict[str, str] | None = None
    fact_signature: str | None = None
    fact_status: str | None = None
    context_window_id: str | None = None
    context_window_signature: str | None = None
    context_window_force_rebuild: bool = False
    lineage: tuple[str, ...] | None = None

    @classmethod
    def from_continuity(cls, value: ContinuityMetadata) -> "TurnMetadata":
        return cls(
            conversation=value.conversation_id,
            mode=value.mode,
            preset_id=value.preset_id,
            history_revision=value.history_revision,
            head_message_id=value.head_message_id,
            current_user=value.current_user_id,
            previous_user=value.previous_user_id,
            previous_backend=value.previous_backend,
            operation_source=value.operation_source,
            generation_id=value.generation_id,
            model=value.actual_model,
            channel=value.channel,
            call_id=value.call_id,
            continuity_epoch=value.continuity_epoch,
            fact_versions=value.fact_versions,
            fact_signature=value.fact_signature,
            fact_status=value.fact_status,
            context_window_id=value.context_window_id,
            context_window_signature=value.context_window_signature,
            context_window_force_rebuild=value.context_window_force_rebuild,
            lineage=value.lineage,
        )

    def normalized(self) -> "TurnMetadata":
        return TurnMetadata(
            conversation=_safe_identifier(self.conversation),
            mode=_safe_label(self.mode),
            preset_id=_safe_identifier(self.preset_id),
            history_revision=(
                self.history_revision
                if isinstance(self.history_revision, str)
                and _DIGEST_RE.fullmatch(self.history_revision)
                else _raise_validation(
                    "history revision must be a sha256 digest"
                )
            ),
            head_message_id=_safe_identifier(
                self.head_message_id, optional=True
            ),
            current_user=_safe_identifier(self.current_user),
            previous_user=_safe_identifier(self.previous_user, optional=True),
            previous_backend=_safe_label(
                self.previous_backend, optional=True
            ),
            operation_source=(
                self.operation_source
                if isinstance(self.operation_source, str)
                and self.operation_source in CONTINUITY_OPERATIONS
                else _raise_validation("unknown continuity operation")
            ),
            generation_id=(
                self.generation_id
                if isinstance(self.generation_id, str)
                and _GENERATION_RE.fullmatch(self.generation_id)
                else _raise_validation(
                    "generation id must be a uuid4 hex token"
                )
            ),
            model=_safe_label(self.model),
            channel=_safe_label(self.channel or "text"),
            call_id=_safe_label(self.call_id, optional=True),
            continuity_epoch=_safe_epoch(
                self.continuity_epoch, optional=True
            ),
            fact_versions=_safe_fact_versions(
                self.fact_versions, optional=True
            ),
            fact_signature=(
                self.fact_signature
                if self.fact_signature is None
                or (
                    isinstance(self.fact_signature, str)
                    and _DIGEST_RE.fullmatch(self.fact_signature)
                )
                else _raise_validation(
                    "fact version signature must be a sha256 digest"
                )
            ),
            fact_status=_safe_label(
                self.fact_status, optional=True
            ),
            context_window_id=_safe_label(
                self.context_window_id, optional=True
            ),
            context_window_signature=(
                self.context_window_signature
                if self.context_window_signature is None
                or (
                    isinstance(self.context_window_signature, str)
                    and _DIGEST_RE.fullmatch(self.context_window_signature)
                )
                else _raise_validation(
                    "context window signature must be a sha256 digest"
                )
            ),
            context_window_force_rebuild=(
                self.context_window_force_rebuild
                if type(self.context_window_force_rebuild) is bool
                else _raise_validation(
                    "context window rebuild flag must be a boolean"
                )
            ),
            lineage=_safe_lineage(self.lineage, optional=True),
        )


@dataclass(frozen=True)
class ThreadStateEntry:
    conversation: str
    mode: str
    preset_id: str
    history_revision: str
    head_message_id: str | None
    current_user: str
    previous_user: str | None
    previous_backend: str | None
    operation_source: str
    generation_id: str
    model: str
    completed: bool
    updated: float
    thread_id: str
    developer_digest: str | None = None
    channel: str = "text"
    call_id: str | None = None
    continuity_epoch: int | None = 0
    fact_versions: dict[str, str] | None = None
    fact_signature: str | None = None
    fact_status: str | None = None
    context_window_id: str | None = None
    context_window_signature: str | None = None
    turns: int = 0

    def validated(self) -> "ThreadStateEntry":
        if type(self.completed) is not bool:
            raise StateValidationError("completed must be a boolean")
        return ThreadStateEntry(
            conversation=_safe_identifier(self.conversation),
            mode=_safe_label(self.mode),
            preset_id=_safe_identifier(self.preset_id),
            history_revision=(
                self.history_revision
                if isinstance(self.history_revision, str)
                and _DIGEST_RE.fullmatch(self.history_revision)
                else _raise_validation(
                    "history revision must be a sha256 digest"
                )
            ),
            head_message_id=_safe_identifier(
                self.head_message_id, optional=True
            ),
            current_user=_safe_identifier(self.current_user),
            previous_user=_safe_identifier(self.previous_user, optional=True),
            previous_backend=_safe_label(
                self.previous_backend, optional=True
            ),
            operation_source=(
                self.operation_source
                if isinstance(self.operation_source, str)
                and self.operation_source in CONTINUITY_OPERATIONS
                else _raise_validation("unknown continuity operation")
            ),
            generation_id=(
                self.generation_id
                if isinstance(self.generation_id, str)
                and _GENERATION_RE.fullmatch(self.generation_id)
                else _raise_validation(
                    "generation id must be a uuid4 hex token"
                )
            ),
            model=_safe_label(self.model),
            completed=self.completed,
            updated=_safe_timestamp(self.updated, "updated"),
            thread_id=_safe_label(self.thread_id),
            developer_digest=(
                self.developer_digest
                if self.developer_digest is None
                or (
                    isinstance(self.developer_digest, str)
                    and _DIGEST_RE.fullmatch(self.developer_digest)
                )
                else _raise_validation(
                    "developer digest must be a sha256 digest"
                )
            ),
            channel=_safe_label(self.channel or "text"),
            call_id=_safe_label(self.call_id, optional=True),
            continuity_epoch=_safe_epoch(
                self.continuity_epoch, optional=True
            ),
            fact_versions=_safe_fact_versions(
                self.fact_versions, optional=True
            ),
            fact_signature=(
                self.fact_signature
                if self.fact_signature is None
                or (
                    isinstance(self.fact_signature, str)
                    and _DIGEST_RE.fullmatch(self.fact_signature)
                )
                else _raise_validation(
                    "fact version signature must be a sha256 digest"
                )
            ),
            fact_status=_safe_label(
                self.fact_status, optional=True
            ),
            context_window_id=_safe_label(
                self.context_window_id, optional=True
            ),
            context_window_signature=(
                self.context_window_signature
                if self.context_window_signature is None
                or (
                    isinstance(self.context_window_signature, str)
                    and _DIGEST_RE.fullmatch(self.context_window_signature)
                )
                else _raise_validation(
                    "context window signature must be a sha256 digest"
                )
            ),
            turns=_safe_turns(self.turns),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self.validated())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ThreadStateEntry":
        if not isinstance(value, Mapping):
            raise StateValidationError("thread state fields are not allowlisted")
        keys = set(value)
        if not STATE_FIELDS <= keys or not (
            keys - STATE_FIELDS
        ) <= STATE_OPTIONAL_FIELDS:
            raise StateValidationError("thread state fields are not allowlisted")
        normalized = dict(value)
        normalized.setdefault("continuity_epoch", None)
        normalized.setdefault("fact_versions", None)
        normalized.setdefault("fact_signature", None)
        normalized.setdefault("fact_status", None)
        normalized.setdefault("context_window_id", None)
        normalized.setdefault("context_window_signature", None)
        normalized.setdefault("turns", 0)
        return cls(**normalized).validated()


@dataclass(frozen=True)
class ThreadPlan:
    action: str
    include_history: bool
    ephemeral: bool
    thread_id: str | None
    reason_codes: tuple[str, ...]

    def __post_init__(self):
        if self.action not in PLAN_ACTIONS:
            raise ValueError("unknown thread plan action")


def _plan(
    action: str, reason: str, *, thread_id: str | None = None
) -> ThreadPlan:
    return ThreadPlan(
        action=action,
        include_history=action != "resume",
        ephemeral=action == "ephemeral",
        thread_id=(
            thread_id if action in {"resume", "catchup"} else None
        ),
        reason_codes=(reason,),
    )


def plan_thread_turn(
    *,
    enabled: bool = False,
    metadata: TurnMetadata | ContinuityMetadata | None,
    state: ThreadStateEntry | None,
    now: float,
    idle_sec: float = 3300,
    max_turns: int | None = None,
    context_tokens: int | None = None,
    context_window: int | None = None,
    capacity_ratio: float | None = None,
    resume_failed: bool = False,
    developer_digest: str | None = None,
    accepted_backend: str | None = None,
) -> ThreadPlan:
    """Return a deterministic plan without executing it or reading a clock.

    ``accepted_backend`` is the host's own backend label. A foreign direct
    parent can catch up on the bound thread, while a direct accepted parent can
    resume it. Rollover limits are explicit host inputs; malformed rollover
    inputs fail closed before any binding reuse.
    """
    if not enabled:
        return _plan("ephemeral", "persistent_threads_disabled")
    if metadata is None:
        return _plan("ephemeral", "continuity_metadata_missing")
    try:
        if isinstance(metadata, ContinuityMetadata):
            meta = TurnMetadata.from_continuity(metadata).normalized()
        elif isinstance(metadata, TurnMetadata):
            meta = metadata.normalized()
        else:
            raise StateValidationError("unsupported turn metadata type")
    except StateValidationError:
        return _plan("ephemeral", "continuity_metadata_invalid")

    if state is None:
        return _plan("new", "first_persistent_turn")
    try:
        if not isinstance(state, ThreadStateEntry):
            raise StateValidationError("unsupported thread state type")
        current = state.validated()
    except StateValidationError:
        return _plan("rebuild", "stored_state_invalid")

    if current.conversation != meta.conversation:
        return _plan("new", "conversation_mismatch")
    if (
        not isinstance(developer_digest, str)
        or not _DIGEST_RE.fullmatch(developer_digest)
        or current.developer_digest != developer_digest
    ):
        return _plan("rebuild", "developer_instructions_changed")
    if (
        (current.fact_signature is None)
        != (meta.fact_signature is None)
        or (current.fact_versions is None)
        != (meta.fact_versions is None)
    ):
        return _plan("rebuild", "fact_baseline_missing")
    if (
        current.fact_signature is not None
        and meta.fact_signature is not None
        and (
            current.fact_signature != meta.fact_signature
            or current.fact_versions != meta.fact_versions
        )
    ):
        return _plan("rebuild", "facts_changed")
    if (meta.fact_signature is None) != (
        meta.fact_versions is None
    ):
        return _plan("rebuild", "fact_metadata_missing")
    if meta.context_window_force_rebuild:
        return _plan("rebuild", "context_window_invalidated")
    if (current.context_window_id is None) != (
        meta.context_window_id is None
    ):
        return _plan("rebuild", "context_window_baseline_missing")
    if (
        current.context_window_id is not None
        and current.context_window_id != meta.context_window_id
    ):
        return _plan("rebuild", "context_window_changed")
    if resume_failed:
        return _plan("rebuild", "thread_resume_failed")
    if meta.operation_source not in {"send", "speak"}:
        return _plan("rebuild", f"operation_{meta.operation_source}")
    if (
        current.continuity_epoch is None
        or meta.continuity_epoch is None
        or current.continuity_epoch != meta.continuity_epoch
    ):
        return _plan("rebuild", "continuity_epoch_changed")
    if not current.completed:
        return _plan("rebuild", "previous_turn_incomplete")
    if current.mode != meta.mode:
        return _plan("rebuild", "mode_changed")
    if current.channel != meta.channel:
        return _plan("rebuild", "channel_changed")
    if current.call_id != meta.call_id:
        return _plan("rebuild", "call_changed")
    if current.preset_id != meta.preset_id:
        return _plan("rebuild", "preset_changed")
    if current.model != meta.model:
        return _plan("rebuild", "model_changed")
    if current.current_user == meta.current_user:
        return _plan("rebuild", "regenerated_user_turn")
    if meta.previous_user is None:
        return _plan("rebuild", "parent_metadata_missing")
    if meta.head_message_id != meta.current_user:
        return _plan("rebuild", "head_message_mismatch")
    if current.history_revision == meta.history_revision:
        return _plan("rebuild", "stale_history_revision")
    if (
        not isinstance(accepted_backend, str)
        or not _SAFE_LABEL_RE.fullmatch(accepted_backend)
    ):
        return _plan("rebuild", "accepted_backend_missing")

    try:
        (
            idle_limit,
            turn_limit,
            token_count,
            token_window,
            capacity_limit,
        ) = _validate_rollover_inputs(
            idle_sec=idle_sec,
            max_turns=max_turns,
            context_tokens=context_tokens,
            context_window=context_window,
            capacity_ratio=capacity_ratio,
        )
    except StateValidationError:
        return _plan("rebuild", "rollover_input_invalid")

    timestamp = _safe_timestamp(now, "now")
    if idle_limit >= 0 and timestamp - current.updated > idle_limit:
        return _plan("rebuild", "persistent_thread_idle")
    if turn_limit not in (None, 0) and current.turns >= turn_limit:
        return _plan("rebuild", "turn_limit_reached")
    if (
        capacity_limit is not None
        and token_count / token_window >= capacity_limit
    ):
        return _plan("rebuild", "context_capacity_reached")
    if (
        meta.previous_user == current.current_user
        and meta.previous_backend != accepted_backend
    ):
        return _plan(
            "catchup",
            "foreign_backend_intervening_turn",
            thread_id=current.thread_id,
        )
    if meta.previous_user == current.current_user:
        return _plan(
            "resume", "direct_continuation", thread_id=current.thread_id
        )
    if meta.lineage and current.current_user in meta.lineage:
        return _plan(
            "catchup", "intervening_turns", thread_id=current.thread_id
        )
    return _plan(
        "rebuild", "branch_or_history_gap"
    )


def completed_state(
    metadata: TurnMetadata | ContinuityMetadata,
    *,
    thread_id: str,
    updated: float,
    completed: bool = True,
    developer_digest: str | None = None,
    previous: ThreadStateEntry | None = None,
) -> ThreadStateEntry:
    """Build validated adapter state without reading a clock or performing I/O."""
    if isinstance(metadata, ContinuityMetadata):
        meta = TurnMetadata.from_continuity(metadata).normalized()
    elif isinstance(metadata, TurnMetadata):
        meta = metadata.normalized()
    else:
        raise StateValidationError("unsupported turn metadata type")
    if previous is not None and not isinstance(previous, ThreadStateEntry):
        raise StateValidationError("previous state must be a thread state")
    prior = previous.validated() if previous is not None else None
    turns = (
        prior.turns + 1
        if prior is not None and prior.thread_id == thread_id
        else 1
    )
    return ThreadStateEntry(
        conversation=meta.conversation,
        mode=meta.mode,
        preset_id=meta.preset_id,
        history_revision=meta.history_revision,
        head_message_id=meta.head_message_id,
        current_user=meta.current_user,
        previous_user=meta.previous_user,
        previous_backend=meta.previous_backend,
        operation_source=meta.operation_source,
        generation_id=meta.generation_id,
        model=meta.model,
        completed=completed,
        updated=updated,
        thread_id=thread_id,
        developer_digest=developer_digest,
        channel=meta.channel,
        call_id=meta.call_id,
        continuity_epoch=meta.continuity_epoch,
        fact_versions=meta.fact_versions,
        fact_signature=meta.fact_signature,
        fact_status=meta.fact_status,
        context_window_id=meta.context_window_id,
        context_window_signature=meta.context_window_signature,
        turns=turns,
    ).validated()
