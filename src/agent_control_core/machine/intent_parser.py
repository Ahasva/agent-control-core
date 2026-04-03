from __future__ import annotations

import re
from dataclasses import dataclass

from agent_control_core.machine.state_logic import (
    SAFE_SERVO_MAX_ANGLE,
    SAFE_SERVO_MIN_ANGLE,
)


BYPASS_SIGNALS = [
    "ignore the limit",
    "ignore limits",
    "ignore safety",
    "skip safety",
    "bypass safety",
    "do what i say",
    "move anyway",
    "just do it",
    "no matter what",
]


@dataclass(frozen=True)
class ParsedMachineIntent:
    intent_type: str
    target_angle: int | None = None
    delta_angle: int | None = None
    raw_target_angle: int | None = None
    safe_target_angle: int | None = None
    exceeded_limits: bool = False
    bypass_signal: bool = False


def clamp_angle(angle: int) -> int:
    return max(SAFE_SERVO_MIN_ANGLE, min(SAFE_SERVO_MAX_ANGLE, angle))


def contains_bypass_signal(text: str) -> bool:
    lowered = text.strip().lower()
    return any(signal in lowered for signal in BYPASS_SIGNALS)


def parse_machine_intent(text: str, current_angle: int | None = None) -> ParsedMachineIntent | None:
    lowered = text.strip().lower()
    bypass_signal = contains_bypass_signal(lowered)

    if any(
        phrase in lowered
        for phrase in [
            "center the servo",
            "centre the servo",
            "reset servo",
            "default servo",
            "home servo",
        ]
    ):
        safe_target = clamp_angle(90)
        return ParsedMachineIntent(
            intent_type="move_absolute",
            target_angle=90,
            raw_target_angle=90,
            safe_target_angle=safe_target,
            exceeded_limits=(safe_target != 90),
            bypass_signal=bypass_signal,
        )

    absolute_match = re.search(r"move\s+servo\s+to\s+(-?\d+)", lowered)
    if absolute_match:
        raw_target = int(absolute_match.group(1))
        safe_target = clamp_angle(raw_target)
        return ParsedMachineIntent(
            intent_type="move_absolute",
            target_angle=raw_target,
            raw_target_angle=raw_target,
            safe_target_angle=safe_target,
            exceeded_limits=(safe_target != raw_target),
            bypass_signal=bypass_signal,
        )

    delta_match = re.search(r"move\s+servo\s+by\s+([+-]?\d+)", lowered)
    if delta_match and current_angle is not None:
        delta = int(delta_match.group(1))
        raw_target = current_angle + delta
        safe_target = clamp_angle(raw_target)
        return ParsedMachineIntent(
            intent_type="move_relative",
            delta_angle=delta,
            raw_target_angle=raw_target,
            safe_target_angle=safe_target,
            exceeded_limits=(safe_target != raw_target),
            bypass_signal=bypass_signal,
        )

    # --- MACHINE CONTROL INTENTS ---

    if any(phrase in lowered for phrase in ["enable machine", "turn on machine", "power on machine"]):
        return ParsedMachineIntent(intent_type="enable_machine", bypass_signal=bypass_signal)

    if any(phrase in lowered for phrase in ["disable machine", "turn off machine", "power off machine"]):
        return ParsedMachineIntent(intent_type="disable_machine", bypass_signal=bypass_signal)

    if any(phrase in lowered for phrase in ["prepare machine", "bring to ready", "set ready"]):
        return ParsedMachineIntent(intent_type="set_ready", bypass_signal=bypass_signal)

    if any(phrase in lowered for phrase in ["start operation", "start machine", "go active"]):
        return ParsedMachineIntent(intent_type="start_active", bypass_signal=bypass_signal)

    if any(phrase in lowered for phrase in ["stop machine", "stop operation", "go idle"]):
        return ParsedMachineIntent(intent_type="set_idle", bypass_signal=bypass_signal)

    if "safe test" in lowered or "test movement" in lowered:
        return ParsedMachineIntent(intent_type="test_sequence", bypass_signal=bypass_signal)

    return None