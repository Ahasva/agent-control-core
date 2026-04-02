from __future__ import annotations

from agent_control_core.machine.state_logic import apply_action_to_state
from agent_control_core.schemas.actions import ExecutionBundle, MachineAction, MachineActionType
from agent_control_core.schemas.common import PolicyDecisionType
from agent_control_core.schemas.plans import ExecutionPlan
from agent_control_core.schemas.policies import PolicyDecision
from agent_control_core.schemas.state import MachineMode, SystemState
from agent_control_core.schemas.tasks import TaskRequest


def build_machine_execution_bundle(
    task: TaskRequest,
    plan: ExecutionPlan,
    policy_decision: PolicyDecision,
    state: SystemState,
) -> ExecutionBundle:
    if policy_decision.decision != PolicyDecisionType.ALLOW:
        return ExecutionBundle(actions=[])

    text = f"{task.goal} {task.context or ''}".lower()
    actions: list[MachineAction] = []
    working_state = state

    def append_action(action: MachineAction) -> None:
        nonlocal working_state
        actions.append(action)
        working_state = apply_action_to_state(working_state, action)

    if not working_state.machine_enabled:
        append_action(
            MachineAction(
                action_type=MachineActionType.ENABLE_MACHINE,
                target_value=None,
                reason="Machine must be enabled before executing the requested procedure.",
            )
        )

    if working_state.machine_mode == MachineMode.OFF:
        append_action(
            MachineAction(
                action_type=MachineActionType.SET_IDLE,
                target_value=None,
                reason="Bring machine from OFF into IDLE before proceeding.",
            )
        )

    if working_state.machine_mode == MachineMode.IDLE:
        append_action(
            MachineAction(
                action_type=MachineActionType.SET_READY,
                target_value=None,
                reason="Bring machine into READY state before bounded action execution.",
            )
        )

    if "calibration" in text:
        append_action(
            MachineAction(
                action_type=MachineActionType.START_CALIBRATION,
                target_value=None,
                reason="Start bounded calibration procedure.",
            )
        )
        append_action(
            MachineAction(
                action_type=MachineActionType.MOVE_SERVO,
                target_value=30,
                reason="Calibration point 1.",
            )
        )
        append_action(
            MachineAction(
                action_type=MachineActionType.MOVE_SERVO,
                target_value=150,
                reason="Calibration point 2.",
            )
        )
        append_action(
            MachineAction(
                action_type=MachineActionType.MOVE_SERVO,
                target_value=90,
                reason="Return actuator to neutral calibration position.",
            )
        )
        append_action(
            MachineAction(
                action_type=MachineActionType.SET_READY,
                target_value=None,
                reason="Return machine to READY after calibration.",
            )
        )
        return ExecutionBundle(actions=actions)

    movement_relevant = (
        "test movement" in text
        or "safe test" in text
        or "movement" in text
        or "move" in text
        or any(step.destructive_action for step in plan.steps)
    )

    if movement_relevant and working_state.requested_angle is not None:
        append_action(
            MachineAction(
                action_type=MachineActionType.START_ACTIVE,
                target_value=None,
                reason="Start bounded active test procedure.",
            )
        )
        append_action(
            MachineAction(
                action_type=MachineActionType.MOVE_SERVO,
                target_value=working_state.requested_angle,
                reason="Move actuator to approved requested angle.",
            )
        )

    return ExecutionBundle(actions=actions)