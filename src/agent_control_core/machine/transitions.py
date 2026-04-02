from __future__ import annotations

from agent_control_core.schemas.state import MachineMode


ALLOWED_TRANSITIONS: dict[MachineMode, set[MachineMode]] = {
    MachineMode.OFF: {MachineMode.IDLE},
    MachineMode.IDLE: {MachineMode.READY, MachineMode.FAULT, MachineMode.LOCKED, MachineMode.OFF},
    MachineMode.READY: {
        MachineMode.CALIBRATION,
        MachineMode.ACTIVE,
        MachineMode.FAULT,
        MachineMode.LOCKED,
        MachineMode.IDLE,
    },
    MachineMode.CALIBRATION: {MachineMode.READY, MachineMode.FAULT, MachineMode.LOCKED},
    MachineMode.ACTIVE: {MachineMode.READY, MachineMode.FAULT, MachineMode.LOCKED},
    MachineMode.FAULT: {MachineMode.LOCKED, MachineMode.IDLE},
    MachineMode.LOCKED: {MachineMode.IDLE},
}


def can_transition(current: MachineMode, target: MachineMode) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, set())


def require_transition(current: MachineMode, target: MachineMode) -> None:
    if not can_transition(current, target):
        raise ValueError(f"Invalid machine state transition: {current.value} -> {target.value}")