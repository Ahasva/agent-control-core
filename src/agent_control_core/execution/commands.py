from __future__ import annotations

from agent_control_core.schemas.actions import MachineAction, MachineActionType


def action_to_command(action: MachineAction) -> str:
    action_type = action.action_type

    if action_type == MachineActionType.ENABLE_MACHINE:
        return "ENABLE_MACHINE"

    if action_type == MachineActionType.DISABLE_MACHINE:
        return "DISABLE_MACHINE"

    if action_type == MachineActionType.SET_IDLE:
        return "SET_STATE IDLE"

    if action_type == MachineActionType.SET_READY:
        return "SET_STATE READY"

    if action_type == MachineActionType.START_CALIBRATION:
        return "SET_STATE CALIBRATION"

    if action_type == MachineActionType.START_ACTIVE:
        return "SET_STATE ACTIVE"

    if action_type == MachineActionType.MOVE_SERVO:
        if action.target_value is None:
            raise ValueError("MOVE_SERVO action requires target_value")
        return f"MOVE_SERVO {action.target_value}"

    if action_type == MachineActionType.REQUEST_APPROVAL:
        return "SET_STATE APPROVAL_PENDING"

    if action_type == MachineActionType.GRANT_APPROVAL:
        return "SET_STATE APPROVAL_GRANTED"

    if action_type == MachineActionType.RAISE_FAULT:
        return "SET_STATE FAULT"

    if action_type == MachineActionType.CLEAR_FAULT:
        return "CLEAR_FAULT"

    if action_type == MachineActionType.LOCK_MACHINE:
        return "SET_STATE LOCKED"

    if action_type == MachineActionType.UNLOCK_MACHINE:
        return "UNLOCK_MACHINE"

    if action_type == MachineActionType.SOUND_ALARM:
        return "BUZZER ALERT"

    if action_type == MachineActionType.ACKNOWLEDGE:
        return "ACKNOWLEDGE"

    raise ValueError(f"Unsupported action type for command conversion: {action_type}")