from agent_control_core.execution.commands import action_to_command
from agent_control_core.execution.executor import (
    MachineExecutor,
    apply_execution_bundle_to_state,
    build_execution_bundle,
)
from agent_control_core.schemas.actions import ExecutionBundle, MachineAction, MachineActionType
from agent_control_core.schemas.common import PolicyDecisionType
from agent_control_core.schemas.plans import ExecutionPlan, PlanStep
from agent_control_core.schemas.policies import PolicyDecision
from agent_control_core.schemas.state import MachineMode, SystemState


def build_idle_state() -> SystemState:
    return SystemState.initial().model_copy(
        update={
            "machine_enabled": False,
            "machine_mode": MachineMode.OFF,
            "requested_angle": 90,
            "potentiometer_raw": 512,
            "potentiometer_angle": 90,
        }
    )


def test_action_to_command_enable_machine() -> None:
    action = MachineAction(
        action_type=MachineActionType.ENABLE_MACHINE,
        target_value=None,
        reason="enable",
    )
    assert action_to_command(action) == "ENABLE_MACHINE"


def test_action_to_command_move_servo() -> None:
    action = MachineAction(
        action_type=MachineActionType.MOVE_SERVO,
        target_value=90,
        reason="move",
    )
    assert action_to_command(action) == "MOVE_SERVO 90"


def test_build_execution_bundle_returns_empty_for_non_allow() -> None:
    plan = ExecutionPlan(summary="No-op", steps=[])
    decision = PolicyDecision(
        decision=PolicyDecisionType.DENY,
        reasons=["denied"],
        required_approvals=[],
    )
    state = build_idle_state()

    bundle = build_execution_bundle(plan, decision, state)
    assert bundle.actions == []


def test_build_execution_bundle_for_allow_includes_enable_ready_and_motion() -> None:
    plan = ExecutionPlan(
        summary="Move actuator",
        steps=[
            PlanStep(
                step_id="s1",
                description="Move actuator",
                tool_name="deployment_tool",
                requires_network=True,
                touches_money=False,
                touches_credentials=False,
                touches_external_comms=False,
                destructive_action=True,
            )
        ],
    )

    decision = PolicyDecision(
        decision=PolicyDecisionType.ALLOW,
        reasons=["allowed"],
        required_approvals=[],
    )
    state = build_idle_state()

    bundle = build_execution_bundle(plan, decision, state)

    assert len(bundle.actions) == 4
    assert bundle.actions[0].action_type == MachineActionType.ENABLE_MACHINE
    assert bundle.actions[1].action_type == MachineActionType.SET_READY
    assert bundle.actions[2].action_type == MachineActionType.START_ACTIVE
    assert bundle.actions[3].action_type == MachineActionType.MOVE_SERVO


def test_apply_execution_bundle_to_state() -> None:
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

    state = build_idle_state()
    updated = apply_execution_bundle_to_state(bundle, state)

    assert updated.machine_enabled is True
    assert updated.machine_mode == MachineMode.READY


def test_machine_executor_executes_bundle_without_serial() -> None:
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

    state = build_idle_state()
    executor = MachineExecutor()

    updated = executor.execute_bundle(bundle, state, serial_link=None)

    assert updated.machine_enabled is True
    assert updated.machine_mode == MachineMode.READY