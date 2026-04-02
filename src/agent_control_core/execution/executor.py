from __future__ import annotations

import time

from agent_control_core.execution.commands import action_to_command
from agent_control_core.machine.state_logic import apply_action_to_state
from agent_control_core.schemas.actions import ExecutionBundle, MachineAction, MachineActionType
from agent_control_core.schemas.common import PolicyDecisionType
from agent_control_core.schemas.plans import ExecutionPlan
from agent_control_core.schemas.policies import PolicyDecision
from agent_control_core.schemas.state import MachineMode, SystemState


def build_execution_bundle(
    plan: ExecutionPlan,
    policy_decision: PolicyDecision,
    state: SystemState,
) -> ExecutionBundle:
    if policy_decision.decision != PolicyDecisionType.ALLOW:
        return ExecutionBundle(actions=[])

    actions: list[MachineAction] = []
    working_state = state

    if not working_state.machine_enabled:
        action = MachineAction(
            action_type=MachineActionType.ENABLE_MACHINE,
            target_value=None,
            reason="Machine must be enabled before execution.",
        )
        actions.append(action)
        working_state = apply_action_to_state(working_state, action)

    if working_state.machine_mode == MachineMode.IDLE:
        action = MachineAction(
            action_type=MachineActionType.SET_READY,
            target_value=None,
            reason="Machine must be brought into READY state before motion.",
        )
        actions.append(action)
        working_state = apply_action_to_state(working_state, action)

    if working_state.requested_angle is not None:
        actuator_relevant = any(step.destructive_action for step in plan.steps)
        if actuator_relevant:
            action = MachineAction(
                action_type=MachineActionType.START_ACTIVE,
                target_value=None,
                reason="Begin bounded active execution for approved machine action.",
            )
            actions.append(action)
            working_state = apply_action_to_state(working_state, action)

            action = MachineAction(
                action_type=MachineActionType.MOVE_SERVO,
                target_value=working_state.requested_angle,
                reason="Move servo to the approved requested angle.",
            )
            actions.append(action)
            working_state = apply_action_to_state(working_state, action)

    return ExecutionBundle(actions=actions)


def apply_execution_bundle_to_state(
    bundle: ExecutionBundle,
    state: SystemState,
) -> SystemState:
    current_state = state
    for action in bundle.actions:
        current_state = apply_action_to_state(current_state, action)
    return current_state


class MachineExecutor:
    def execute_bundle(
        self,
        bundle: ExecutionBundle,
        state: SystemState,
        serial_link=None,
    ) -> SystemState:
        current_state = state

        for action in bundle.actions:
            if serial_link is not None:
                command = action_to_command(action)
                serial_link.send_command(command)
                time.sleep(0.15)

            current_state = apply_action_to_state(current_state, action)

        return current_state