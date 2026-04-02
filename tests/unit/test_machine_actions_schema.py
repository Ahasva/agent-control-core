from agent_control_core.schemas.actions import (
    ExecutionBundle,
    MachineAction,
    MachineActionType,
)


def test_machine_action_creation() -> None:
    action = MachineAction(
        action_type=MachineActionType.ENABLE_MACHINE,
        target_value=None,
        reason="start machine",
    )

    assert action.action_type == MachineActionType.ENABLE_MACHINE
    assert action.reason == "start machine"


def test_execution_bundle_creation() -> None:
    bundle = ExecutionBundle(
        actions=[
            MachineAction(
                action_type=MachineActionType.ENABLE_MACHINE,
                target_value=None,
                reason="enable",
            ),
            MachineAction(
                action_type=MachineActionType.SET_READY,
                target_value=None,
                reason="ready",
            ),
        ]
    )

    assert len(bundle.actions) == 2
    assert bundle.actions[0].action_type == MachineActionType.ENABLE_MACHINE
    assert bundle.actions[1].action_type == MachineActionType.SET_READY