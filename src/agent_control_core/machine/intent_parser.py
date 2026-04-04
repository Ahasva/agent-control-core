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
    "override safety",
    "do what i say",
    "move anyway",
    "just do it",
    "no matter what",
    "force it",
]

ABSOLUTE_MOVE_PATTERN = re.compile(r"move\s+servo\s+to\s+(-?\d+)", re.IGNORECASE)
RELATIVE_MOVE_PATTERN = re.compile(r"move\s+servo\s+by\s+([+-]?\d+)", re.IGNORECASE)


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

    # -------------------------------------------------------------------------
    # SERVO POSITION COMMANDS
    # -------------------------------------------------------------------------
    if any(
        phrase in lowered
        for phrase in [
            "center the servo",
            "centre the servo",
            "center servo",
            "centre servo",
            "reset servo",
            "default servo",
            "home servo",
            "servo home",
            "home machine",
            "home actuator",
        ]
    ):
        raw_target = 90
        safe_target = clamp_angle(raw_target)
        return ParsedMachineIntent(
            intent_type="move_absolute",
            target_angle=raw_target,
            raw_target_angle=raw_target,
            safe_target_angle=safe_target,
            exceeded_limits=(safe_target != raw_target),
            bypass_signal=bypass_signal,
        )

    absolute_match = ABSOLUTE_MOVE_PATTERN.search(lowered)
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

    relative_match = RELATIVE_MOVE_PATTERN.search(lowered)
    if relative_match:
        delta = int(relative_match.group(1))
        base_angle = current_angle if current_angle is not None else 90
        raw_target = base_angle + delta
        safe_target = clamp_angle(raw_target)
        return ParsedMachineIntent(
            intent_type="move_relative",
            delta_angle=delta,
            raw_target_angle=raw_target,
            safe_target_angle=safe_target,
            exceeded_limits=(safe_target != raw_target),
            bypass_signal=bypass_signal,
        )

    # -------------------------------------------------------------------------
    # SEQUENCES
    # -------------------------------------------------------------------------
    if any(
        phrase in lowered
        for phrase in [
            "safe test",
            "run a safe test",
            "test movement",
            "run test movement",
            "test sequence",
            "safe test movement",
            "run a safe test movement",
        ]
    ):
        return ParsedMachineIntent(
            intent_type="test_sequence",
            bypass_signal=bypass_signal,
        )

    if any(
        phrase in lowered
        for phrase in [
            "calibration",
            "run calibration",
        ]
    ):
        return ParsedMachineIntent(
            intent_type="calibration",
            bypass_signal=bypass_signal,
        )

    if any(
        phrase in lowered
        for phrase in [
            "startup sequence",
            "start up sequence",
            "startup",
            "start up",
            "startup machine",
            "start machine sequence",
            "prepare and start machine",
        ]
    ):
        return ParsedMachineIntent(
            intent_type="startup_sequence",
            bypass_signal=bypass_signal,
        )

    if any(
        phrase in lowered
        for phrase in [
            "safe shutdown",
            "shutdown safely",
            "shut down safely",
            "controlled shutdown",
            "stop and safe the machine",
            "safe the machine",
        ]
    ):
        return ParsedMachineIntent(
            intent_type="safe_shutdown",
            bypass_signal=bypass_signal,
        )

    if any(
        phrase in lowered
        for phrase in [
            "unlock machine",
            "unlock the machine",
            "unlock the lock",
            "clear lock",
            "clear the lock",
            "recover from lock",
            "reset lock",
        ]
    ):
        return ParsedMachineIntent(
            intent_type="unlock_machine",
            bypass_signal=bypass_signal,
        )

    if any(
        phrase in lowered
        for phrase in [
            "recover from fault",
            "recover fault",
            "clear fault",
            "acknowledge fault",
            "reset fault",
            "clear fault and prepare machine",
            "acknowledge and reset machine",
        ]
    ):
        return ParsedMachineIntent(
            intent_type="recover_fault",
            bypass_signal=bypass_signal,
        )

    # -------------------------------------------------------------------------
    # MACHINE STATE COMMANDS
    # -------------------------------------------------------------------------
    if any(
        phrase in lowered
        for phrase in [
            "enable machine",
            "enable the machine",
            "turn on machine",
            "power on machine",
        ]
    ):
        return ParsedMachineIntent(
            intent_type="enable_machine",
            bypass_signal=bypass_signal,
        )

    if any(
        phrase in lowered
        for phrase in [
            "disable machine",
            "disable the machine",
            "turn off machine",
            "power off machine",
            "shut down machine",
            "shutdown machine",
        ]
    ):
        return ParsedMachineIntent(
            intent_type="disable_machine",
            bypass_signal=bypass_signal,
        )

    if any(
        phrase in lowered
        for phrase in [
            "prepare machine",
            "prepare the machine",
            "bring to ready",
            "bring machine to ready",
            "set ready",
            "make ready",
            "ready the machine",
        ]
    ):
        return ParsedMachineIntent(
            intent_type="set_ready",
            bypass_signal=bypass_signal,
        )

    if any(
        phrase in lowered
        for phrase in [
            "start operation",
            "start machine",
            "go active",
            "enter active mode",
            "activate machine",
        ]
    ):
        return ParsedMachineIntent(
            intent_type="start_active",
            bypass_signal=bypass_signal,
        )

    if any(
        phrase in lowered
        for phrase in [
            "stop machine",
            "stop operation",
            "go idle",
            "set idle",
            "enter idle mode",
        ]
    ):
        return ParsedMachineIntent(
            intent_type="set_idle",
            bypass_signal=bypass_signal,
        )

    if any(
        phrase in lowered
        for phrase in [
            "lock machine",
            "lock the machine",
            "engage lock",
            "activate lock",
        ]
    ):
        return ParsedMachineIntent(
            intent_type="lock_machine",
            bypass_signal=bypass_signal,
        )

    return None
