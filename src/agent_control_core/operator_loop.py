from __future__ import annotations

import time
import uuid

from agent_control_core.demo import (
    emit_audit_event,
    live_assess_risk,
    live_generate_plan,
    maybe_connect_serial_link,
    print_section,
)
from agent_control_core.execution.executor import MachineExecutor
from agent_control_core.machine.intent_parser import parse_machine_intent
from agent_control_core.machine.procedures import build_machine_execution_bundle

from agent_control_core.machine_demo import (
    merge_hardware_status_into_state,
    mock_machine_assess_risk,
    mock_machine_generate_plan,
    request_fresh_status,
    wait_for_hardware_approval
)
from agent_control_core.policies.engine import evaluate_plan
from agent_control_core.schemas.approvals import ApprovalRequest
from agent_control_core.schemas.common import PolicyDecisionType, RiskLevel
from agent_control_core.schemas.plans import ExecutionPlan, PlanStep
from agent_control_core.schemas.policies import PolicyDecision, RiskAssessment
from agent_control_core.schemas.state import SystemState
from agent_control_core.schemas.tasks import TaskRequest
from agent_control_core.settings import Settings
from agent_control_core.workflows.checkpoints import build_approval_request


def build_interactive_task(user_text: str) -> TaskRequest:
    return TaskRequest(
        user_id="interactive_user",
        session_id=str(uuid.uuid4()),
        goal=user_text.strip(),
        context="Interactive operator loop request.",
        requested_tools=["machine_controller", "state_reader"],
    )


def read_live_state(serial_link) -> SystemState:
    state = SystemState.initial()

    status_line = request_fresh_status(serial_link)
    print_section("ARDUINO STATUS", {"status": status_line})

    state = merge_hardware_status_into_state(state, status_line)
    return state


def build_machine_intent_plan(user_text: str, state: SystemState) -> ExecutionPlan | None:
    parsed = parse_machine_intent(user_text, current_angle=state.servo_angle)
    if parsed is None:
        return None

    if parsed.intent_type == "move_absolute" and parsed.safe_target_angle is not None:
        return ExecutionPlan(
            summary=f"Move servo to safely bounded target angle {parsed.safe_target_angle}.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect current machine state and current servo angle.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description=f"Move servo to bounded target angle {parsed.safe_target_angle}.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
            ],
        )

    if parsed.intent_type == "move_relative" and parsed.safe_target_angle is not None:
        return ExecutionPlan(
            summary=(
                f"Move servo from current angle {state.servo_angle} by requested delta {parsed.delta_angle}, "
                f"resulting in bounded target angle {parsed.safe_target_angle}."
            ),
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect current machine state and current servo angle.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description=(
                        f"Move servo by requested delta {parsed.delta_angle}, "
                        f"clamped to safe target angle {parsed.safe_target_angle}."
                    ),
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
            ],
        )

    if parsed.intent_type == "enable_machine":
        return ExecutionPlan(
            summary="Enable the machine.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Enable the machine.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                )
            ],
        )

    if parsed.intent_type == "disable_machine":
        return ExecutionPlan(
            summary="Disable the machine.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Disable the machine and return to a safe off state.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                )
            ],
        )

    if parsed.intent_type == "set_ready":
        return ExecutionPlan(
            summary="Prepare the machine and bring it to READY state.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect current machine state.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Enable the machine if needed and bring it to READY state.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
            ],
        )

    if parsed.intent_type == "start_active":
        return ExecutionPlan(
            summary="Prepare the machine and enter ACTIVE mode.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect current machine state.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Bring the machine to READY if needed and start active mode.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
            ],
        )

    if parsed.intent_type == "set_idle":
        return ExecutionPlan(
            summary="Stop the current operation and return the machine to IDLE state.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Transition the machine to IDLE state.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                )
            ],
        )

    if parsed.intent_type == "test_sequence":
        return ExecutionPlan(
            summary="Run a safe bounded test sequence.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect current machine state.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Prepare the machine and run a bounded test sequence.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
            ],
        )

    if parsed.intent_type == "calibration":
        return ExecutionPlan(
            summary="Run a bounded calibration procedure.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect current machine state.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Prepare the machine and execute bounded calibration.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
            ],
        )

    if parsed.intent_type == "startup_sequence":
        return ExecutionPlan(
            summary="Run a guarded startup sequence to bring the machine from OFF/IDLE to ACTIVE.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect current machine state.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Enable the machine and bring it to READY state if needed.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-3",
                    description="Start ACTIVE mode under bounded machine rules.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
            ],
        )

    if parsed.intent_type == "safe_shutdown":
        return ExecutionPlan(
            summary="Run a safe shutdown sequence and return the machine to OFF.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect current machine state.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Move to a safe neutral position if needed and disable the machine.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
            ],
        )

    if parsed.intent_type == "recover_fault":
        return ExecutionPlan(
            summary="Recover the machine from FAULT and return it to a safe baseline state.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect current machine state.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Clear the fault and return the machine to a safe baseline state.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
            ],
        )

    if parsed.intent_type == "unlock_machine":
        return ExecutionPlan(
            summary="Recover the machine from LOCKED and return it to a safe baseline state.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect current machine state.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Clear the machine lock and return to a safe baseline state.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
            ],
        )

    if parsed.intent_type == "lock_machine":
        return ExecutionPlan(
            summary="Place the machine into LOCKED state.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect current machine state.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Transition the machine into LOCKED state.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
            ],
        )

    return None


def build_machine_intent_risk(user_text: str, state: SystemState) -> RiskAssessment | None:
    parsed = parse_machine_intent(user_text, current_angle=state.servo_angle)
    if parsed is None:
        return None

    if parsed.intent_type in {"enable_machine", "disable_machine", "set_ready", "set_idle"}:
        return RiskAssessment(
            risk_level=RiskLevel.LOW,
            reasons=["The request changes machine operating state but does not command hazardous motion."],
            sensitive_capabilities=["machine state control"],
        )

    if parsed.intent_type in {"start_active", "test_sequence"}:
        return RiskAssessment(
            risk_level=RiskLevel.MEDIUM,
            reasons=["The request prepares or starts bounded machine activity."],
            sensitive_capabilities=["machine activity control"],
        )
    
    if parsed.intent_type == "recover_fault":
        return RiskAssessment(
            risk_level=RiskLevel.MEDIUM,
            reasons=["Fault recovery changes safety-relevant machine state and must remain bounded."],
            sensitive_capabilities=["fault recovery", "machine state recovery"],
        )
    
    if parsed.intent_type == "calibration":
        return RiskAssessment(
            risk_level=RiskLevel.HIGH,
            reasons=["Calibration changes machine behavior and requires approval before execution."],
            sensitive_capabilities=["calibration motion", "approval-gated machine procedure"],
        )
    
    if parsed.intent_type == "unlock_machine":
        return RiskAssessment(
            risk_level=RiskLevel.MEDIUM,
            reasons=["Lock recovery changes safety-relevant machine state and must remain bounded."],
            sensitive_capabilities=["lock recovery", "machine state recovery"],
        )

    if parsed.intent_type == "lock_machine":
        return RiskAssessment(
            risk_level=RiskLevel.LOW,
            reasons=["The request places the machine into a more restrictive safety state."],
            sensitive_capabilities=["machine lock control"],
        )

    if parsed.intent_type == "safe_shutdown":
        return RiskAssessment(
            risk_level=RiskLevel.MEDIUM,
            reasons=["Safe shutdown changes machine activity state under bounded shutdown rules."],
            sensitive_capabilities=["machine shutdown control"],
        )

    if parsed.intent_type == "startup_sequence":
        return RiskAssessment(
            risk_level=RiskLevel.MEDIUM,
            reasons=["The request prepares or starts bounded machine activity."],
            sensitive_capabilities=["machine startup control"],
        )

    reasons = ["The request affects physical actuator motion."]
    sensitive_capabilities = ["servo motion", "state-aware bounded actuation"]
    risk_level = RiskLevel.MEDIUM

    if parsed.exceeded_limits:
        reasons.append(
            f"The original requested target {parsed.raw_target_angle} exceeded the safe servo range and was corrected to {parsed.safe_target_angle}."
        )
        sensitive_capabilities.append("boundary correction")
        risk_level = RiskLevel.HIGH
    else:
        reasons.append("The requested motion is bounded to the safe servo range of 20 to 160 degrees.")

    if parsed.bypass_signal:
        reasons.append("The task text includes pressure or bypass language intended to override limits.")
        sensitive_capabilities.append("safety bypass attempt")
        risk_level = RiskLevel.CRITICAL

    return RiskAssessment(
        risk_level=risk_level,
        reasons=reasons,
        sensitive_capabilities=sensitive_capabilities,
    )


def run_operator_once(user_text: str, settings: Settings) -> None:
    task = build_interactive_task(user_text)
    print_section("TASK REQUEST", task.model_dump())

    emit_audit_event(
        session_id=task.session_id,
        event_type="task_received",
        action_summary=task.goal,
    )

    serial_link = None
    try:
        serial_link = maybe_connect_serial_link(settings)
        if serial_link is not None:
            time.sleep(2.0)
            state = read_live_state(serial_link)
        else:
            state = SystemState.initial()

        print_section("SYSTEM STATE", state.model_dump())

        emit_audit_event(
            session_id=task.session_id,
            event_type="state_initialized",
            action_summary=f"Machine state initialized: {state.machine_mode.value}",
            rationale=f"enabled={state.machine_enabled}, approval_pending={state.approval_pending}, requested_angle={state.requested_angle}",
        )

        machine_plan = build_machine_intent_plan(user_text, state)

        if machine_plan is not None:
            plan = machine_plan
        elif settings.use_mock_llm:
            plan = mock_machine_generate_plan(task)
        else:
            plan = live_generate_plan(task, settings)

        print_section("EXECUTION PLAN", plan.model_dump())

        emit_audit_event(
            session_id=task.session_id,
            event_type="plan_generated",
            action_summary=plan.summary,
        )

        machine_risk = build_machine_intent_risk(user_text, state)

        if machine_risk is not None:
            risk = machine_risk
        elif settings.use_mock_llm:
            risk = mock_machine_assess_risk(task, plan)
        else:
            risk = live_assess_risk(task, plan, settings)

        print_section("RISK ASSESSMENT", risk.model_dump())

        emit_audit_event(
            session_id=task.session_id,
            event_type="risk_assessed",
            action_summary=f"Risk level: {risk.risk_level.value}",
            rationale="; ".join(risk.reasons),
        )

        policy_decision: PolicyDecision = evaluate_plan(task, plan, risk, state)
        print_section("POLICY DECISION", policy_decision.model_dump())

        emit_audit_event(
            session_id=task.session_id,
            event_type="policy_evaluated",
            action_summary="Policy decision completed.",
            decision=policy_decision.model_dump(mode="json")["decision"],
            rationale="; ".join(policy_decision.reasons),
        )

        if policy_decision.decision == PolicyDecisionType.ALLOW:
            execution_bundle = build_machine_execution_bundle(task, plan, policy_decision, state)
            print_section("EXECUTION BUNDLE", execution_bundle.model_dump())

            executor = MachineExecutor()
            state_after_execution = executor.execute_bundle(
                execution_bundle,
                state,
                serial_link=serial_link,
            )

            if serial_link is not None:
                final_status = request_fresh_status(serial_link)
                print_section("ARDUINO STATUS AFTER EXECUTION", {"status": final_status})
                state_after_execution = merge_hardware_status_into_state(
                    state_after_execution,
                    final_status,
                )

            print_section("STATE AFTER EXECUTION", state_after_execution.model_dump())

            emit_audit_event(
                session_id=task.session_id,
                event_type="execution_bundle_applied",
                action_summary="Approved machine execution bundle applied.",
                decision="allow",
                rationale=f"Executed {len(execution_bundle.actions)} machine action(s).",
            )

        elif policy_decision.decision == PolicyDecisionType.REQUIRE_APPROVAL:
            if serial_link is not None:
                serial_link.send_command("SET_STATE APPROVAL_PENDING")
                serial_link.send_command("BUZZER ALERT")

            approval_request: ApprovalRequest = build_approval_request(
                session_id=task.session_id,
                plan=plan,
                policy_decision=policy_decision,
            )
            print_section("APPROVAL REQUEST", approval_request.model_dump())

            emit_audit_event(
                session_id=task.session_id,
                event_type="approval_requested",
                action_summary="Approval request created.",
                decision="require_approval",
                rationale=approval_request.user_message,
            )

            if serial_link is not None:
                approved, approval_status = wait_for_hardware_approval(serial_link)
                print_section("APPROVAL RESULT", {"approved": approved, "status": approval_status})

                if approved:
                    state = merge_hardware_status_into_state(state, approval_status)
                    print_section("SYSTEM STATE AFTER APPROVAL", state.model_dump())

                    policy_decision_after_approval: PolicyDecision = evaluate_plan(task, plan, risk, state)
                    print_section("POLICY DECISION AFTER APPROVAL", policy_decision_after_approval.model_dump())

                    emit_audit_event(
                        session_id=task.session_id,
                        event_type="policy_re_evaluated",
                        action_summary="Policy decision re-evaluated after hardware approval.",
                        decision=policy_decision_after_approval.model_dump(mode="json")["decision"],
                        rationale="; ".join(policy_decision_after_approval.reasons),
                    )

                    if policy_decision_after_approval.decision == PolicyDecisionType.ALLOW:
                        execution_bundle = build_machine_execution_bundle(task, plan, policy_decision_after_approval, state)
                        print_section("EXECUTION BUNDLE", execution_bundle.model_dump())

                        executor = MachineExecutor()
                        state_after_execution = executor.execute_bundle(
                            execution_bundle,
                            state,
                            serial_link=serial_link,
                        )

                        if serial_link is not None:
                            final_status = request_fresh_status(serial_link)
                            print_section("ARDUINO STATUS AFTER EXECUTION", {"status": final_status})
                            state_after_execution = merge_hardware_status_into_state(
                                state_after_execution,
                                final_status,
                            )

                        print_section("STATE AFTER EXECUTION", state_after_execution.model_dump())

                        emit_audit_event(
                            session_id=task.session_id,
                            event_type="execution_bundle_applied",
                            action_summary="Approved machine execution bundle applied after hardware approval.",
                            decision="allow",
                            rationale=f"Executed {len(execution_bundle.actions)} machine action(s).",
                        )

                    else:
                        print("Approval was received, but policy still denied execution.")

                else:
                    if serial_link is not None:
                        serial_link.send_command("SET_STATE OFF")
                        serial_link.send_command("DISABLE_MACHINE")
                        final_status = request_fresh_status(serial_link)
                        print_section("APPROVAL TIMEOUT RESET", {"status": final_status})
                        state = merge_hardware_status_into_state(state, final_status)
                    print("Approval not received. No execution performed.")
            else:
                print("Approval required, but no hardware approval channel is available.")

        else:
            should_force_fault = (
                risk.risk_level == RiskLevel.CRITICAL
                or any(
                    "override or bypass safety constraints" in reason.lower()
                    for reason in policy_decision.reasons
                )
            )

            if serial_link is not None and should_force_fault:
                serial_link.send_command("SET_STATE FAULT")
                serial_link.send_command("BUZZER ALERT")

            emit_audit_event(
                session_id=task.session_id,
                event_type="execution_denied",
                action_summary="Execution denied by policy.",
                decision="deny",
                rationale="; ".join(policy_decision.reasons),
            )

            print("Execution denied by policy.")

        if serial_link is not None:
            final_status = request_fresh_status(serial_link)
            print_section("ARDUINO STATUS AFTER", {"status": final_status})

    finally:
        if serial_link is not None:
            serial_link.close()


def main() -> None:
    settings = Settings()

    print_section(
        "SERIAL CONFIG",
        {
            "enabled": settings.serial_enabled,
            "port": settings.serial_port,
            "baudrate": settings.serial_baudrate,
            "timeout": settings.serial_timeout,
        },
    )

    print(f"Using mock LLM mode: {settings.use_mock_llm}")
    print("Interactive operator loop started.")
    print("Type a command, or 'exit' to quit.")

    while True:
        print("\n" + "=" * 80)
        user_text = input("\033[1;36mOPERATOR COMMAND  >  \033[0m").strip()

        if not user_text:
            continue

        if user_text.lower() in {"exit", "quit"}:
            print("Exiting operator loop.")
            break

        run_operator_once(user_text, settings)


if __name__ == "__main__":
    main()
