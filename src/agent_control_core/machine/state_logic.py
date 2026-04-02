from __future__ import annotations

from agent_control_core.machine.transitions import require_transition
from agent_control_core.schemas.actions import MachineAction, MachineActionType
from agent_control_core.schemas.state import MachineMode, SystemState


SAFE_SERVO_MIN_ANGLE = 20
SAFE_SERVO_MAX_ANGLE = 160


def compute_requested_angle_from_potentiometer(raw: int) -> int:
    if raw < 0 or raw > 1023:
        raise ValueError(f"Potentiometer reading out of range: {raw}")
    return int(round((raw / 1023) * 180))


def requested_angle_is_safe(angle: int) -> bool:
    return SAFE_SERVO_MIN_ANGLE <= angle <= SAFE_SERVO_MAX_ANGLE


def state_allows_motion(state: SystemState) -> bool:
    return (
        state.machine_enabled
        and state.machine_mode in {MachineMode.READY, MachineMode.ACTIVE, MachineMode.CALIBRATION}
        and not state.fault_active
        and not state.lock_active
    )


def state_requires_approval(state: SystemState) -> bool:
    return state.approval_pending and not state.approval_granted


def can_enter_active(state: SystemState) -> bool:
    return (
        state.machine_enabled
        and state.machine_mode == MachineMode.READY
        and not state.fault_active
        and not state.lock_active
        and state.approval_granted
    )


def can_move_servo(state: SystemState, angle: int) -> bool:
    return state_allows_motion(state) and requested_angle_is_safe(angle)


def update_potentiometer(state: SystemState, raw_value: int) -> SystemState:
    angle = compute_requested_angle_from_potentiometer(raw_value)
    return state.model_copy(
        update={
            "potentiometer_raw": raw_value,
            "potentiometer_angle": angle,
            "requested_angle": angle,
            "last_event": "potentiometer_updated",
        }
    )


def apply_action_to_state(state: SystemState, action: MachineAction) -> SystemState:
    action_type = action.action_type

    if action_type == MachineActionType.ENABLE_MACHINE:
        require_transition(state.machine_mode, MachineMode.IDLE)
        return state.model_copy(
            update={
                "machine_enabled": True,
                "machine_mode": MachineMode.IDLE,
                "last_event": "machine_enabled",
            }
        )

    if action_type == MachineActionType.DISABLE_MACHINE:
        return state.model_copy(
            update={
                "machine_enabled": False,
                "machine_mode": MachineMode.OFF,
                "approval_pending": False,
                "approval_granted": False,
                "last_event": "machine_disabled",
            }
        )

    if action_type == MachineActionType.SET_READY:
        require_transition(state.machine_mode, MachineMode.READY)
        return state.model_copy(
            update={
                "machine_mode": MachineMode.READY,
                "last_event": "machine_ready",
            }
        )

    if action_type == MachineActionType.SET_IDLE:
        require_transition(state.machine_mode, MachineMode.IDLE)
        return state.model_copy(
            update={
                "machine_mode": MachineMode.IDLE,
                "last_event": "machine_idle",
            }
        )

    if action_type == MachineActionType.START_CALIBRATION:
        require_transition(state.machine_mode, MachineMode.CALIBRATION)
        return state.model_copy(
            update={
                "machine_mode": MachineMode.CALIBRATION,
                "approval_pending": False,
                "last_event": "calibration_started",
            }
        )

    if action_type == MachineActionType.START_ACTIVE:
        require_transition(state.machine_mode, MachineMode.ACTIVE)
        return state.model_copy(
            update={
                "machine_mode": MachineMode.ACTIVE,
                "approval_pending": False,
                "last_event": "active_mode_started",
            }
        )

    if action_type == MachineActionType.MOVE_SERVO:
        if action.target_value is None:
            raise ValueError("MOVE_SERVO requires target_value")
        if not can_move_servo(state, action.target_value):
            raise ValueError("Servo move not allowed in current state")
        return state.model_copy(
            update={
                "servo_angle": action.target_value,
                "last_event": f"servo_moved_to_{action.target_value}",
            }
        )

    if action_type == MachineActionType.REQUEST_APPROVAL:
        return state.model_copy(
            update={
                "approval_pending": True,
                "approval_granted": False,
                "last_event": "approval_requested",
            }
        )

    if action_type == MachineActionType.GRANT_APPROVAL:
        return state.model_copy(
            update={
                "approval_pending": False,
                "approval_granted": True,
                "last_event": "approval_granted",
            }
        )

    if action_type == MachineActionType.RAISE_FAULT:
        return state.model_copy(
            update={
                "fault_active": True,
                "machine_mode": MachineMode.FAULT,
                "last_error": action.reason or "fault_raised",
                "last_event": "fault_raised",
            }
        )

    if action_type == MachineActionType.CLEAR_FAULT:
        return state.model_copy(
            update={
                "fault_active": False,
                "last_error": None,
                "last_event": "fault_cleared",
            }
        )

    if action_type == MachineActionType.LOCK_MACHINE:
        return state.model_copy(
            update={
                "lock_active": True,
                "machine_mode": MachineMode.LOCKED,
                "last_event": "machine_locked",
            }
        )

    if action_type == MachineActionType.UNLOCK_MACHINE:
        require_transition(state.machine_mode, MachineMode.IDLE)
        return state.model_copy(
            update={
                "lock_active": False,
                "machine_mode": MachineMode.IDLE,
                "last_event": "machine_unlocked",
            }
        )

    if action_type == MachineActionType.SOUND_ALARM:
        return state.model_copy(
            update={
                "last_event": "alarm_sounded",
            }
        )

    if action_type == MachineActionType.ACKNOWLEDGE:
        return state.model_copy(
            update={
                "last_event": "acknowledged",
            }
        )

    raise ValueError(f"Unsupported action type: {action_type}")