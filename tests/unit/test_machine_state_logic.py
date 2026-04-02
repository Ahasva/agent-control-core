from agent_control_core.machine.state_logic import (
    SAFE_SERVO_MAX_ANGLE,
    SAFE_SERVO_MIN_ANGLE,
    apply_action_to_state,
    can_enter_active,
    can_move_servo,
    compute_requested_angle_from_potentiometer,
    requested_angle_is_safe,
    state_allows_motion,
    state_requires_approval,
    update_potentiometer,
)
from agent_control_core.schemas.actions import MachineAction, MachineActionType
from agent_control_core.schemas.state import MachineMode, SystemState


def test_initial_state_factory() -> None:
    state = SystemState.initial()
    assert state.machine_mode == MachineMode.OFF
    assert state.machine_enabled is False
    assert state.servo_angle == 90
    assert state.last_event == "initial_state_created"


def test_compute_requested_angle_from_potentiometer() -> None:
    assert compute_requested_angle_from_potentiometer(0) == 0
    assert compute_requested_angle_from_potentiometer(1023) == 180


def test_requested_angle_is_safe() -> None:
    assert requested_angle_is_safe(SAFE_SERVO_MIN_ANGLE) is True
    assert requested_angle_is_safe(SAFE_SERVO_MAX_ANGLE) is True
    assert requested_angle_is_safe(SAFE_SERVO_MIN_ANGLE - 1) is False
    assert requested_angle_is_safe(SAFE_SERVO_MAX_ANGLE + 1) is False


def test_update_potentiometer_updates_state() -> None:
    state = SystemState.initial()
    updated = update_potentiometer(state, 512)

    assert updated.potentiometer_raw == 512
    assert 0 <= updated.potentiometer_angle <= 180
    assert updated.requested_angle == updated.potentiometer_angle
    assert updated.last_event == "potentiometer_updated"


def test_state_allows_motion_only_when_ready_and_enabled() -> None:
    state = SystemState.initial().model_copy(
        update={
            "machine_enabled": True,
            "machine_mode": MachineMode.READY,
            "fault_active": False,
            "lock_active": False,
        }
    )
    assert state_allows_motion(state) is True


def test_state_requires_approval() -> None:
    state = SystemState.initial().model_copy(
        update={"approval_pending": True, "approval_granted": False}
    )
    assert state_requires_approval(state) is True


def test_can_enter_active_requires_ready_enabled_and_approval() -> None:
    state = SystemState.initial().model_copy(
        update={
            "machine_enabled": True,
            "machine_mode": MachineMode.READY,
            "fault_active": False,
            "lock_active": False,
            "approval_granted": True,
        }
    )
    assert can_enter_active(state) is True


def test_can_move_servo_true_when_ready_and_safe_angle() -> None:
    state = SystemState.initial().model_copy(
        update={
            "machine_enabled": True,
            "machine_mode": MachineMode.READY,
            "fault_active": False,
            "lock_active": False,
        }
    )
    assert can_move_servo(state, 90) is True


def test_apply_enable_machine_action() -> None:
    state = SystemState.initial()
    action = MachineAction(
        action_type=MachineActionType.ENABLE_MACHINE,
        target_value=None,
        reason="test",
    )

    updated = apply_action_to_state(state, action)

    assert updated.machine_enabled is True
    assert updated.machine_mode == MachineMode.IDLE
    assert updated.last_event == "machine_enabled"


def test_apply_request_and_grant_approval_actions() -> None:
    state = SystemState.initial()

    requested = apply_action_to_state(
        state,
        MachineAction(
            action_type=MachineActionType.REQUEST_APPROVAL,
            target_value=None,
            reason="approval needed",
        ),
    )
    assert requested.approval_pending is True
    assert requested.approval_granted is False

    granted = apply_action_to_state(
        requested,
        MachineAction(
            action_type=MachineActionType.GRANT_APPROVAL,
            target_value=None,
            reason="approved",
        ),
    )
    assert granted.approval_pending is False
    assert granted.approval_granted is True


def test_apply_move_servo_action() -> None:
    state = SystemState.initial().model_copy(
        update={
            "machine_enabled": True,
            "machine_mode": MachineMode.READY,
            "fault_active": False,
            "lock_active": False,
        }
    )

    updated = apply_action_to_state(
        state,
        MachineAction(
            action_type=MachineActionType.MOVE_SERVO,
            target_value=90,
            reason="safe move",
        ),
    )

    assert updated.servo_angle == 90
    assert updated.last_event == "servo_moved_to_90"


def test_apply_move_servo_raises_when_not_allowed() -> None:
    state = SystemState.initial()

    try:
        apply_action_to_state(
            state,
            MachineAction(
                action_type=MachineActionType.MOVE_SERVO,
                target_value=90,
                reason="unsafe move",
            ),
        )
        assert False, "Expected ValueError when servo move is not allowed"
    except ValueError as exc:
        assert "Servo move not allowed" in str(exc)


def test_apply_raise_fault_action() -> None:
    state = SystemState.initial()

    updated = apply_action_to_state(
        state,
        MachineAction(
            action_type=MachineActionType.RAISE_FAULT,
            target_value=None,
            reason="test fault",
        ),
    )

    assert updated.fault_active is True
    assert updated.machine_mode == MachineMode.FAULT
    assert updated.last_error == "test fault"


def test_apply_lock_and_unlock_actions() -> None:
    state = SystemState.initial().model_copy(
        update={
            "machine_enabled": True,
            "machine_mode": MachineMode.IDLE,
        }
    )

    locked = apply_action_to_state(
        state,
        MachineAction(
            action_type=MachineActionType.LOCK_MACHINE,
            target_value=None,
            reason="lock for test",
        ),
    )
    assert locked.lock_active is True
    assert locked.machine_mode == MachineMode.LOCKED

    unlocked = apply_action_to_state(
        locked,
        MachineAction(
            action_type=MachineActionType.UNLOCK_MACHINE,
            target_value=None,
            reason="unlock for test",
        ),
    )
    assert unlocked.lock_active is False
    assert unlocked.machine_mode == MachineMode.IDLE

def test_can_move_servo_in_calibration_mode() -> None:
    state = SystemState.initial().model_copy(
        update={
            "machine_enabled": True,
            "machine_mode": MachineMode.CALIBRATION,
            "fault_active": False,
            "lock_active": False,
        }
    )
    assert can_move_servo(state, 90) is True