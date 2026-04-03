from __future__ import annotations

from agent_control_core.machine.intent_parser import parse_machine_intent
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
        print(
            "DEBUG BEFORE ACTION:",
            working_state.machine_mode,
            working_state.machine_enabled,
            working_state.fault_active,
            working_state.lock_active,
            action,
        )
        actions.append(action)
        working_state = apply_action_to_state(working_state, action)
        print(
            "DEBUG AFTER ACTION:",
            working_state.machine_mode,
            working_state.machine_enabled,
            working_state.fault_active,
            working_state.lock_active,
        )

    def ensure_machine_ready_for_motion() -> None:
        nonlocal working_state

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

    parsed = parse_machine_intent(text, current_angle=working_state.servo_angle)

    # -------------------------------------------------------------------------
    # 1) MACHINE CONTROL COMMANDS
    # -------------------------------------------------------------------------
    if parsed is not None:
        if parsed.intent_type == "enable_machine":
            if not working_state.machine_enabled:
                append_action(
                    MachineAction(
                        action_type=MachineActionType.ENABLE_MACHINE,
                        target_value=None,
                        reason="Operator requested machine enable.",
                    )
                )
            return ExecutionBundle(actions=actions)

        if parsed.intent_type == "disable_machine":
            append_action(
                MachineAction(
                    action_type=MachineActionType.DISABLE_MACHINE,
                    target_value=None,
                    reason="Operator requested machine shutdown.",
                )
            )
            return ExecutionBundle(actions=actions)

        if parsed.intent_type == "set_ready":
            ensure_machine_ready_for_motion()
            return ExecutionBundle(actions=actions)

        if parsed.intent_type == "start_active":
            ensure_machine_ready_for_motion()

            if working_state.machine_mode != MachineMode.ACTIVE:
                append_action(
                    MachineAction(
                        action_type=MachineActionType.START_ACTIVE,
                        target_value=None,
                        reason="Operator requested active mode.",
                    )
                )
            return ExecutionBundle(actions=actions)

        if parsed.intent_type == "set_idle":
            if working_state.machine_mode != MachineMode.IDLE:
                append_action(
                    MachineAction(
                        action_type=MachineActionType.SET_IDLE,
                        target_value=None,
                        reason="Operator requested idle state.",
                    )
                )
            return ExecutionBundle(actions=actions)

        if parsed.intent_type == "test_sequence":
            ensure_machine_ready_for_motion()

            if working_state.machine_mode != MachineMode.ACTIVE:
                append_action(
                    MachineAction(
                        action_type=MachineActionType.START_ACTIVE,
                        target_value=None,
                        reason="Start safe test sequence.",
                    )
                )

            append_action(
                MachineAction(
                    action_type=MachineActionType.MOVE_SERVO,
                    target_value=60,
                    reason="Test position 1.",
                )
            )
            append_action(
                MachineAction(
                    action_type=MachineActionType.MOVE_SERVO,
                    target_value=120,
                    reason="Test position 2.",
                )
            )
            append_action(
                MachineAction(
                    action_type=MachineActionType.MOVE_SERVO,
                    target_value=90,
                    reason="Return to neutral position.",
                )
            )

            return ExecutionBundle(actions=actions)

    # -------------------------------------------------------------------------
    # 2) DIRECT SERVO COMMANDS
    # -------------------------------------------------------------------------
    if (
        "move servo to" in text
        or "move servo by" in text
        or "center the servo" in text
        or "centre the servo" in text
        or "reset servo" in text
        or "default servo" in text
        or "home servo" in text
    ):
        target_angle = parsed.safe_target_angle if parsed is not None else None

        if target_angle is not None:
            ensure_machine_ready_for_motion()

            if working_state.machine_mode != MachineMode.ACTIVE:
                append_action(
                    MachineAction(
                        action_type=MachineActionType.START_ACTIVE,
                        target_value=None,
                        reason="Start bounded active motion procedure.",
                    )
                )

            append_action(
                MachineAction(
                    action_type=MachineActionType.MOVE_SERVO,
                    target_value=target_angle,
                    reason=f"Move servo to safely bounded target angle {target_angle}.",
                )
            )

            return ExecutionBundle(actions=actions)

    # -------------------------------------------------------------------------
    # 3) CALIBRATION PROCEDURE
    # -------------------------------------------------------------------------
    if "calibration" in text:
        ensure_machine_ready_for_motion()

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

    # -------------------------------------------------------------------------
    # 4) GENERIC MOVEMENT SCENARIOS
    # -------------------------------------------------------------------------
    movement_relevant = (
        "test movement" in text
        or "safe test" in text
        or "movement" in text
        or "move" in text
        or any(step.destructive_action for step in plan.steps)
    )

    if movement_relevant and working_state.requested_angle is not None:
        ensure_machine_ready_for_motion()

        if working_state.machine_mode != MachineMode.ACTIVE:
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