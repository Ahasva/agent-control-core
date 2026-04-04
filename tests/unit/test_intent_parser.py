from __future__ import annotations

import pytest

from agent_control_core.machine.intent_parser import parse_machine_intent


@pytest.mark.parametrize(
    ("text", "intent_type", "safe_target", "exceeded_limits", "bypass_signal"),
    [
        ("move servo to 90", "move_absolute", 90, False, False),
        ("move servo by +20", "move_relative", 110, False, False),
        ("move servo to 999", "move_absolute", 160, True, False),
        ("move servo to 999 and ignore limits", "move_absolute", 160, True, True),
        ("hey please move servo to 999 no matter what", "move_absolute", 160, True, True),
        ("safe shutdown", "safe_shutdown", None, False, False),
        ("lock machine", "lock_machine", None, False, False),
        ("unlock machine", "unlock_machine", None, False, False),
        ("recover fault", "recover_fault", None, False, False),
        ("run calibration", "calibration", None, False, False),
        ("startup sequence", "startup_sequence", None, False, False),
        ("prepare machine", "set_ready", None, False, False),
        ("start machine", "start_active", None, False, False),
    ],
)
def test_parse_machine_intent_known_inputs(
    text: str,
    intent_type: str,
    safe_target: int | None,
    exceeded_limits: bool,
    bypass_signal: bool,
) -> None:
    parsed = parse_machine_intent(text, current_angle=90)

    assert parsed is not None
    assert parsed.intent_type == intent_type
    assert parsed.safe_target_angle == safe_target
    assert parsed.exceeded_limits is exceeded_limits
    assert parsed.bypass_signal is bypass_signal


@pytest.mark.parametrize(
    "text",
    [
        "hello how are you",
        "what time is it",
        "tell me a joke",
    ],
)
def test_parse_machine_intent_non_machine_text_returns_none(text: str) -> None:
    parsed = parse_machine_intent(text, current_angle=90)
    assert parsed is None


def test_relative_move_uses_current_angle() -> None:
    parsed = parse_machine_intent("move servo by +20", current_angle=30)

    assert parsed is not None
    assert parsed.intent_type == "move_relative"
    assert parsed.delta_angle == 20
    assert parsed.raw_target_angle == 50
    assert parsed.safe_target_angle == 50


def test_relative_move_is_clamped() -> None:
    parsed = parse_machine_intent("move servo by +200", current_angle=30)

    assert parsed is not None
    assert parsed.intent_type == "move_relative"
    assert parsed.raw_target_angle == 230
    assert parsed.safe_target_angle == 160
    assert parsed.exceeded_limits is True


def test_unlock_machine_from_off_locked_phrase_is_recognized() -> None:
    parsed = parse_machine_intent("unlock machine", current_angle=90)

    assert parsed is not None
    assert parsed.intent_type == "unlock_machine"