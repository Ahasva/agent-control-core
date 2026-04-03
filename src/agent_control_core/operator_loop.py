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
from agent_control_core.machine.procedures import build_machine_execution_bundle
from agent_control_core.machine_demo import (
    merge_hardware_status_into_state,
    mock_machine_assess_risk,
    mock_machine_generate_plan,
    request_fresh_status,
)
from agent_control_core.machine.intent_parser import clamp_angle, parse_machine_intent
from agent_control_core.policies.engine import evaluate_plan
from agent_control_core.settings import Settings
from agent_control_core.schemas.common import PolicyDecisionType, RiskLevel
from agent_control_core.schemas.plans import ExecutionPlan, PlanStep
from agent_control_core.schemas.policies import PolicyDecision, RiskAssessment
from agent_control_core.schemas.state import SystemState
from agent_control_core.schemas.tasks import TaskRequest


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


def build_direct_motion_plan(user_text: str, state: SystemState) -> ExecutionPlan | None:
    parsed = parse_machine_intent(user_text, current_angle=state.servo_angle)
    if parsed is None or parsed.safe_target_angle is None:
        return None

    if parsed.intent_type == "move_absolute":
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

    if parsed.intent_type == "move_relative":
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

    return None


def build_direct_motion_risk(user_text: str, state: SystemState) -> RiskAssessment | None:
    parsed = parse_machine_intent(user_text, current_angle=state.servo_angle)
    if parsed is None:
        return None

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
        reasons.append(
            f"The requested motion is bounded to the safe servo range of 20 to 160 degrees."
        )

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

        direct_plan = build_direct_motion_plan(user_text, state)

        if direct_plan is not None:
            plan = direct_plan
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

        direct_risk = build_direct_motion_risk(user_text, state)

        if direct_risk is not None:
            risk = direct_risk
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
            print_section("STATE AFTER EXECUTION", state_after_execution.model_dump())

            emit_audit_event(
                session_id=task.session_id,
                event_type="execution_bundle_applied",
                action_summary="Approved machine execution bundle applied.",
                decision="allow",
                rationale=f"Executed {len(execution_bundle.actions)} machine action(s).",
            )

        elif policy_decision.decision == PolicyDecisionType.REQUIRE_APPROVAL:
            print("Approval required. No execution performed.")

        else:
            print("Execution denied by policy.")

        if serial_link is not None:
            final_status = request_fresh_status(serial_link)
            print_section("ARDUINO STATUS AFTER", {"status": final_status})

    finally:
        if serial_link is not None:
            serial_link.close()


def main() -> None:
    settings = Settings()

    print(f"Using mock LLM mode: {settings.use_mock_llm}")
    print("Interactive operator loop started.")
    print("Type a command, or 'exit' to quit.")

    while True:
        user_text = input("\noperator> ").strip()

        if not user_text:
            continue

        if user_text.lower() in {"exit", "quit"}:
            print("Exiting operator loop.")
            break

        run_operator_once(user_text, settings)


if __name__ == "__main__":
    main()