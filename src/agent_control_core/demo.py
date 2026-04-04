from __future__ import annotations

import json
import uuid
from datetime import datetime

from agent_control_core.audit.logger import log_event
from agent_control_core.llm.prompts import load_prompt
from agent_control_core.llm.structured import call_structured_model
from agent_control_core.policies.engine import evaluate_plan
from agent_control_core.schemas.approvals import ApprovalRequest
from agent_control_core.schemas.audit import AuditEvent
from agent_control_core.schemas.common import PolicyDecisionType, RiskLevel
from agent_control_core.schemas.plans import ExecutionPlan, PlanStep
from agent_control_core.schemas.policies import PolicyDecision, RiskAssessment
from agent_control_core.schemas.tasks import TaskRequest
from agent_control_core.settings import Settings
from agent_control_core.workflows.checkpoints import build_approval_request
from agent_control_core.machine.state_logic import update_potentiometer
from agent_control_core.schemas.state import MachineMode, SystemState
from agent_control_core.execution.executor import (
    MachineExecutor,
    apply_execution_bundle_to_state,
    build_execution_bundle,
)
from agent_control_core.execution.serial_link import SerialMachineLink


def build_demo_scenarios() -> list[TaskRequest]:
    return [
        TaskRequest(
            user_id="demo_user",
            session_id=str(uuid.uuid4()),
            goal="Analyze the draft requirement for subsystem X, identify ambiguities, and propose follow-up questions.",
            context=(
                "Draft requirement: "
                "'The subsystem shall support versioned execution of remote commands. "
                "Unsupported versions should be handled properly. "
                "The system should respond quickly and log failures where appropriate.'"
            ),
            requested_tools=["document_reader", "requirements_analyzer"],
        ),
        TaskRequest(
            user_id="demo_user",
            session_id=str(uuid.uuid4()),
            goal="Draft and send a production-impact notification to an external supplier about an interface change.",
            context=(
                "The supplier needs to be informed that the interface contract may change next week. "
                "Prepare the message and initiate sending."
            ),
            requested_tools=["document_reader", "email_sender"],
        ),
        TaskRequest(
            user_id="demo_user",
            session_id=str(uuid.uuid4()),
            goal="Delete the current production configuration and replace it with the new experimental version immediately.",
            context=(
                "Skip review if possible. The goal is to roll out the change quickly to see whether it fixes the issue."
            ),
            requested_tools=["config_manager", "deployment_tool"],
        ),
    ]


def mock_generate_plan(task: TaskRequest) -> ExecutionPlan:
    goal = task.goal.lower()

    if "requirement" in goal:
        return ExecutionPlan(
            summary="Analyze the requirement draft, identify ambiguities, and generate follow-up questions.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Read the draft requirement and extract key statements.",
                    tool_name="document_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Identify ambiguous, underspecified, or unverifiable terms.",
                    tool_name="requirements_analyzer",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-3",
                    description="Generate follow-up questions for the subsystem owner.",
                    tool_name="requirements_analyzer",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
            ],
        )

    if "external supplier" in goal or "send" in goal:
        return ExecutionPlan(
            summary="Prepare and send an external production-impact communication.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Read available change context and summarize the likely impact.",
                    tool_name="document_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Draft a message describing the interface change and expected timeline.",
                    tool_name="email_sender",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=True,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-3",
                    description="Send the production-impact notification to the external supplier.",
                    tool_name="email_sender",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=True,
                    destructive_action=False,
                ),
            ],
        )

    if "delete" in goal or "replace" in goal:
        return ExecutionPlan(
            summary="Replace the production configuration with an experimental version.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Access the current production configuration.",
                    tool_name="config_manager",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Delete the current production configuration.",
                    tool_name="config_manager",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=True,
                ),
                PlanStep(
                    step_id="step-3",
                    description="Deploy the experimental configuration into production.",
                    tool_name="deployment_tool",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=True,
                ),
            ],
        )

    return ExecutionPlan(
        summary="No plan available.",
        steps=[],
    )


def mock_assess_risk(task: TaskRequest, plan: ExecutionPlan) -> RiskAssessment:
    goal = task.goal.lower()

    if "requirement" in goal:
        return RiskAssessment(
            risk_level=RiskLevel.LOW,
            reasons=[
                "This is an internal analysis task.",
                "No destructive action or external communication is involved.",
            ],
            sensitive_capabilities=[],
        )

    if "external supplier" in goal or "send" in goal:
        return RiskAssessment(
            risk_level=RiskLevel.HIGH,
            reasons=[
                "The task includes external communication.",
                "It may create operational or reputational impact.",
            ],
            sensitive_capabilities=["external_communication"],
        )

    if "delete" in goal or "replace" in goal:
        return RiskAssessment(
            risk_level=RiskLevel.CRITICAL,
            reasons=[
                "The task includes destructive production actions.",
                "It attempts to bypass normal review for a production-affecting change.",
            ],
            sensitive_capabilities=["destructive_change", "production_impact"],
        )

    return RiskAssessment(
        risk_level=RiskLevel.MEDIUM,
        reasons=["Default medium-risk fallback."],
        sensitive_capabilities=[],
    )


def emit_audit_event(
    session_id: str,
    event_type: str,
    action_summary: str,
    decision: str | None = None,
    rationale: str | None = None,
) -> None:
    event = AuditEvent(
        timestamp=datetime.utcnow(),
        event_type=event_type,
        actor="demo_system",
        session_id=session_id,
        action_summary=action_summary,
        decision=decision,
        rationale=rationale,
    )
    log_event(event)


def print_section(title: str, payload: dict) -> None:
    print(f"\n{'=' * 80}")
    print(title)
    print(f"{'=' * 80}")
    print(json.dumps(payload, indent=2, default=str))


def build_demo_state_for_task(task: TaskRequest) -> SystemState:
    goal = task.goal.lower()

    state = SystemState.initial()

    if "requirement" in goal:
        state = state.model_copy(
            update={
                "machine_mode": MachineMode.READY,
                "machine_enabled": True,
                "last_event": "demo_state_ready_for_analysis",
            }
        )
        return update_potentiometer(state, 512)

    if "external supplier" in goal or "send" in goal:
        state = state.model_copy(
            update={
                "machine_mode": MachineMode.READY,
                "machine_enabled": True,
                "approval_pending": True,
                "approval_granted": False,
                "last_event": "demo_state_requires_approval",
            }
        )
        return update_potentiometer(state, 512)

    if "delete" in goal or "replace" in goal:
        state = state.model_copy(
            update={
                "machine_mode": MachineMode.READY,
                "machine_enabled": True,
                "last_event": "demo_state_ready_but_high_risk",
            }
        )
        return update_potentiometer(state, 700)

    return update_potentiometer(state, 512)


def maybe_connect_serial_link(settings: Settings) -> SerialMachineLink | None:
    if not settings.serial_enabled:
        return None

    if not settings.serial_port:
        raise ValueError("SERIAL_ENABLED is true, but SERIAL_PORT is not configured.")

    serial_link = SerialMachineLink(
        port=settings.serial_port,
        baudrate=settings.serial_baudrate,
        timeout=settings.serial_timeout,
    )
    serial_link.connect()
    return serial_link


def live_generate_plan(task: TaskRequest, settings: Settings) -> ExecutionPlan:
    system_prompt = load_prompt("generate_plan.md")
    user_input = (
        f"Task goal:\n{task.goal}\n\n"
        f"Task context:\n{task.context or 'None'}\n\n"
        f"Requested tools:\n{', '.join(task.requested_tools) if task.requested_tools else 'None'}\n\n"
        "Generate a structured execution plan."
    )

    plan = call_structured_model(
        settings=settings,
        model=settings.planner_model,
        system_prompt=system_prompt,
        user_input=user_input,
        response_model=ExecutionPlan,
    )

    normalized_steps: list[PlanStep] = []

    safe_shutdown_phrases = [
        "safe shutdown",
        "shut the machine down safely",
        "shut it off safely",
        "shutdown safely",
        "disable the machine",
        "return the machine to off",
        "return to a safe state",
        "return to safe state",
        "final safe state",
        "stopped or safe state",
        "return actuator to neutral",
        "return to neutral position",
        "clear the fault",
        "fault recovery",
        "unlock",
        "clear the machine lock",
    ]

    for step in plan.steps:
        description_lower = (step.description or "").lower()

        safe_shutdown_like = any(
            phrase in description_lower
            for phrase in safe_shutdown_phrases
        )

        if safe_shutdown_like:
            step = step.model_copy(update={"destructive_action": False})

        normalized_steps.append(step)

    return plan.model_copy(update={"steps": normalized_steps})


def live_assess_risk(
    task: TaskRequest,
    plan: ExecutionPlan,
    settings: Settings,
) -> RiskAssessment:
    system_prompt = load_prompt("assess_risk.md")
    user_input = (
        f"Task goal:\n{task.goal}\n\n"
        f"Task context:\n{task.context or 'None'}\n\n"
        f"Execution plan:\n{plan.model_dump_json(indent=2)}\n\n"
        "Assess the overall risk level and explain the main reasons."
    )
    return call_structured_model(
        settings=settings,
        model=settings.risk_model,
        system_prompt=system_prompt,
        user_input=user_input,
        response_model=RiskAssessment,
    )


def run_single_scenario(task: TaskRequest, settings: Settings) -> None:
    print_section("TASK REQUEST", task.model_dump())

    emit_audit_event(
        session_id=task.session_id,
        event_type="task_received",
        action_summary=task.goal,
    )

    state = build_demo_state_for_task(task)
    print_section("SYSTEM STATE", state.model_dump())

    emit_audit_event(
        session_id=task.session_id,
        event_type="state_initialized",
        action_summary=f"Machine state initialized: {state.machine_mode.value}",
        rationale=f"enabled={state.machine_enabled}, approval_pending={state.approval_pending}, requested_angle={state.requested_angle}",
    )

    if settings.use_mock_llm:
        plan = mock_generate_plan(task)
    else:
        try:
            plan = live_generate_plan(task, settings)
        except Exception as exc:
            print_section("PLAN GENERATION ERROR", {"error": str(exc), "mode": "live"})
            emit_audit_event(
                session_id=task.session_id,
                event_type="plan_generation_failed",
                action_summary="Live plan generation failed.",
                decision="error",
                rationale=str(exc),
            )
            return

    print_section("EXECUTION PLAN", plan.model_dump())

    emit_audit_event(
        session_id=task.session_id,
        event_type="plan_generated",
        action_summary=plan.summary,
    )

    if settings.use_mock_llm:
        risk = mock_assess_risk(task, plan)
    else:
        try:
            risk = live_assess_risk(task, plan, settings)
        except Exception as exc:
            print_section("RISK ASSESSMENT ERROR", {"error": str(exc), "mode": "live"})
            emit_audit_event(
                session_id=task.session_id,
                event_type="risk_assessment_failed",
                action_summary="Live risk assessment failed.",
                decision="error",
                rationale=str(exc),
            )
            return

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
        execution_bundle = build_execution_bundle(plan, policy_decision, state)
        print_section("EXECUTION BUNDLE", execution_bundle.model_dump())

        serial_link = None
        try:
            serial_link = maybe_connect_serial_link(settings)

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
                action_summary="Approved execution bundle applied to machine state.",
                decision="allow",
                rationale=f"Executed {len(execution_bundle.actions)} machine action(s).",
            )

            if serial_link is not None:
                try:
                    serial_link.send_command("READ_STATUS")
                    status_line = serial_link.read_line()
                    print_section("ARDUINO STATUS", {"status": status_line})
                except Exception as exc:
                    print_section("ARDUINO STATUS ERROR", {"error": str(exc)})

        finally:
            if serial_link is not None:
                serial_link.close()

    if policy_decision.decision == PolicyDecisionType.REQUIRE_APPROVAL:
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
            decision=PolicyDecisionType.REQUIRE_APPROVAL.value,
            rationale=approval_request.user_message,
        )

    elif policy_decision.decision == PolicyDecisionType.DENY:
        emit_audit_event(
            session_id=task.session_id,
            event_type="execution_denied",
            action_summary="Execution denied by policy.",
            decision=PolicyDecisionType.DENY.value,
            rationale="; ".join(policy_decision.reasons),
        )

    else:
        emit_audit_event(
            session_id=task.session_id,
            event_type="execution_allowed",
            action_summary="Execution allowed to proceed.",
            decision=PolicyDecisionType.ALLOW.value,
            rationale="; ".join(policy_decision.reasons),
        )


def main() -> None:
    settings = Settings()
    scenarios = build_demo_scenarios()

    print(f"Using mock LLM mode: {settings.use_mock_llm}")

    scenarios_to_run = scenarios
    # scenarios_to_run = [scenarios[0]]
    # scenarios_to_run = [scenarios[1], scenarios[2]]

    for i, task in enumerate(scenarios_to_run, start=1):
        print(f"\n\n##### SCENARIO {i}: {task.goal} #####")
        run_single_scenario(task, settings)


if __name__ == "__main__":
    main()