from agent_control_core.machine.transitions import can_transition, require_transition
from agent_control_core.schemas.state import MachineMode


def test_can_transition_off_to_idle() -> None:
    assert can_transition(MachineMode.OFF, MachineMode.IDLE) is True


def test_can_transition_ready_to_active() -> None:
    assert can_transition(MachineMode.READY, MachineMode.ACTIVE) is True


def test_cannot_transition_off_to_active() -> None:
    assert can_transition(MachineMode.OFF, MachineMode.ACTIVE) is False


def test_require_transition_raises_for_invalid_transition() -> None:
    try:
        require_transition(MachineMode.OFF, MachineMode.ACTIVE)
        assert False, "Expected ValueError for invalid transition"
    except ValueError as exc:
        assert "Invalid machine state transition" in str(exc)