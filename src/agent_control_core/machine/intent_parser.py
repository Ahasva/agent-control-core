from __future__ import annotations

import re
from dataclasses import dataclass

from agent_control_core.machine.state_logic import (
    SAFE_SERVO_MAX_ANGLE,
    SAFE_SERVO_MIN_ANGLE,
)


@dataclass(frozen=True)
class ParsedMachineIntent:
    intent_type: str
    target_angle: int | None = None
    delta_angle: int | None = None


def parse_machine_intent(text: str) -> ParsedMachineIntent | None:
    lowered = text.strip().lower()

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
        return ParsedMachineIntent(
            intent_type="move_absolute",
            target_angle=90,
        )

    absolute_match = re.search(r"move\s+servo\s+to\s+(-?\d+)", lowered)
    if absolute_match:
        return ParsedMachineIntent(
            intent_type="move_absolute",
            target_angle=int(absolute_match.group(1)),
        )

    delta_match = re.search(r"move\s+servo\s+by\s+([+-]?\d+)", lowered)
    if delta_match:
        return ParsedMachineIntent(
            intent_type="move_relative",
            delta_angle=int(delta_match.group(1)),
        )

    return None


def clamp_angle(angle: int) -> int:
    return max(SAFE_SERVO_MIN_ANGLE, min(SAFE_SERVO_MAX_ANGLE, angle))