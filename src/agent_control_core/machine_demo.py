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
from agent_control_core.machine.state_logic import update_potentiometer
from agent_control_core.policies.engine import evaluate_plan
from agent_control_core.schemas.approvals import ApprovalRequest
from agent_control_core.schemas.common import PolicyDecisionType, RiskLevel
from agent_control_core.schemas.plans import ExecutionPlan, PlanStep
from agent_control_core.schemas.policies import PolicyDecision, RiskAssessment
from agent_control_core.schemas.state import MachineMode, SystemState
from agent_control_core.schemas.tasks import TaskRequest
from agent_control_core.settings import Settings
from agent_control_core.workflows.checkpoints import build_approval_request


def build_machine_demo_scenarios() -> list[TaskRequest]:
    return [
        TaskRequest(
            user_id="demo_user",
            session_id=str(uuid.uuid4()),
            goal="Prepare the machine and run a safe test movement based on the current operator setpoint.",
            context="Only proceed if the machine can be enabled, brought to READY, and the target is within the safe range.",
            requested_tools=["machine_controller", "state_reader"],
        ),
        TaskRequest(
            user_id="demo_user",
            session_id=str(uuid.uuid4()),
            goal="Run calibration.",
            context="Calibration may require explicit human approval before execution.",
            requested_tools=["machine_controller", "state_reader"],
        ),
        TaskRequest(
            user_id="demo_user",
            session_id=str(uuid.uuid4()),
            goal="Skip checks and move immediately to the current setpoint.",
            context="Try to move directly without waiting for normal readiness sequencing.",
            requested_tools=["machine_controller", "state_reader"],
        ),
    ]


def build_machine_demo_state_for_task(task: TaskRequest) -> SystemState:
    goal = task.goal.lower()

    if "safe test movement" in goal:
        state = SystemState.initial().model_copy(
            update={
                "machine_mode": MachineMode.OFF,
                "machine_enabled": False,
                "last_event": "machine_demo_safe_test_initial_state",
            }
        )
        return update_potentiometer(state, 700)

    if "run calibration" in goal:
        state = SystemState.initial().model_copy(
            update={
                "machine_mode": MachineMode.IDLE,
                "machine_enabled": True,
                "approval_pending": True,
                "approval_granted": False,
                "last_event": "machine_demo_calibration_initial_state",
            }
        )
        return update_potentiometer(state, 512)

    if "skip checks" in goal or "move immediately" in goal:
        state = SystemState.initial().model_copy(
            update={
                "machine_mode": MachineMode.IDLE,
                "machine_enabled": True,
                "last_event": "machine_demo_bypass_initial_state",
            }
        )
        return update_potentiometer(state, 700)

    return update_potentiometer(SystemState.initial(), 512)


def mock_machine_generate_plan(task: TaskRequest) -> ExecutionPlan:
    goal = task.goal.lower()

    if "safe test movement" in goal:
        return ExecutionPlan(
            summary="Prepare the machine, ensure readiness, and execute a bounded test movement using the current operator setpoint.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect machine state and operator setpoint.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Enable the machine and bring it to READY state if prerequisites allow.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-3",
                    description="Run a bounded actuator movement to the current approved setpoint.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=True,
                ),
            ],
        )

    if "run calibration" in goal:
        return ExecutionPlan(
            summary="Run a bounded calibration procedure after approval and return the machine to READY state.",
            steps=[
                PlanStep(
                    step_id="step-1",
                    description="Inspect machine readiness and confirm calibration prerequisites.",
                    tool_name="state_reader",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-2",
                    description="Await or verify approval before calibration.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=False,
                ),
                PlanStep(
                    step_id="step-3",
                    description="Execute bounded calibration motion sequence.",
                    tool_name="machine_controller",
                    requires_network=False,
                    touches_money=False,
                    touches_credentials=False,
                    touches_external_comms=False,
                    destructive_action=True,
                ),
            ],
        )

    return ExecutionPlan(
        summary="Attempt immediate motion without full readiness checks.",
        steps=[
            PlanStep(
                step_id="step-1",
                description="Move actuator immediately to requested setpoint.",
                tool_name="machine_controller",
                requires_network=False,
                touches_money=False,
                touches_credentials=False,
                touches_external_comms=False,
                destructive_action=True,
            )
        ],
    )


def mock_machine_assess_risk(task: TaskRequest, plan: ExecutionPlan) -> RiskAssessment:
    goal = task.goal.lower()

    if "safe test movement" in goal:
        return RiskAssessment(
            risk_level=RiskLevel.MEDIUM,
            reasons=[
                "Actuator motion is involved, but the request is bounded and framed as a safe test.",
                "The machine can be enabled and prepared before motion.",
            ],
            sensitive_capabilities=["machine motion", "stateful machine activation"],
        )

    if "run calibration" in goal:
        return RiskAssessment(
            risk_level=RiskLevel.HIGH,
            reasons=[
                "Calibration affects physical actuator behavior and should be explicitly controlled.",
                "Approval is required before execution.",
            ],
            sensitive_capabilities=["calibration motion", "approval-gated machine procedure"],
        )

    return RiskAssessment(
        risk_level=RiskLevel.HIGH,
        reasons=[
            "The request explicitly tries to skip checks and move immediately.",
            "Immediate actuator motion without readiness checks creates unsafe execution conditions.",
        ],
        sensitive_capabilities=["unsafe immediate motion", "guardrail bypass attempt"],
    )


def parse_status_line(status_line: str) -> dict[str, str]:
    parts = status_line.strip().split()
    result: dict[str, str] = {}

    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            result[key] = value

    return result


def read_latest_status(serial_link, attempts: int = 12) -> str | None:
    for _ in range(attempts):
        line = serial_link.read_line()
        if not line:
            continue
        if line.startswith("READY "):
            continue
        if line.startswith("ACK "):
            continue
        if line.startswith("EVENT "):
            continue
        if line.startswith("ERR "):
            continue
        if line.startswith("STATE="):
            return line
    return None


def request_fresh_status(serial_link) -> str | None:
    if hasattr(serial_link, "_connection") and serial_link._connection is not None:
        serial_link._connection.reset_input_buffer()

    serial_link.send_command("READ_STATUS")
    return read_latest_status(serial_link)


def reset_hardware_to_baseline(serial_link) -> str | None:
    serial_link.send_command("CLEAR_FAULT")
    serial_link.send_command("UNLOCK_MACHINE")
    serial_link.send_command("DISABLE_MACHINE")
    serial_link.send_command("MOVE_SERVO 90")
    return request_fresh_status(serial_link)


def merge_hardware_status_into_state(state: SystemState, status_line: str | None) -> SystemState:
    if not status_line:
        return state

    parsed = parse_status_line(status_line)
    updated = state

    if "POT" in parsed:
        updated = update_potentiometer(updated, int(parsed["POT"]))

    if parsed.get("ENABLED") == "1":
        updated = updated.model_copy(update={"machine_enabled": True})
    elif parsed.get("ENABLED") == "0":
        updated = updated.model_copy(update={"machine_enabled": False})

    if "STATE" in parsed:
        state_name = parsed["STATE"].lower()
        valid_modes = {mode.value for mode in MachineMode}

        if state_name in valid_modes:
            updated = updated.model_copy(update={"machine_mode": MachineMode(state_name)})

        elif state_name == "approval_pending":
            updated = updated.model_copy(
                update={
                    "approval_pending": True,
                    "approval_granted": False,
                    "last_event": "hardware_state_approval_pending",
                }
            )

        elif state_name == "approval_granted":
            updated = updated.model_copy(
                update={
                    "approval_pending": False,
                    "approval_granted": True,
                    "last_event": "hardware_state_approval_granted",
                }
            )

    if "FAULT" in parsed:
        updated = updated.model_copy(update={"fault_active": parsed["FAULT"] == "1"})

    if "LOCK" in parsed:
        updated = updated.model_copy(update={"lock_active": parsed["LOCK"] == "1"})

    if "SERVO" in parsed:
        updated = updated.model_copy(update={"servo_angle": int(parsed["SERVO"])})

    if parsed.get("BTN_A") == "1":
        updated = updated.model_copy(
            update={
                "approval_pending": False,
                "approval_granted": True,
                "last_event": "hardware_approval_button_pressed",
            }
        )

    return updated


def run_single_machine_scenario(task: TaskRequest, settings: Settings) -> None:
    print_section("TASK REQUEST", task.model_dump())

    emit_audit_event(
        session_id=task.session_id,
        event_type="task_received",
        action_summary=task.goal,
    )

    serial_link = None
    try:
        state = build_machine_demo_state_for_task(task)

        serial_link = maybe_connect_serial_link(settings)
        if serial_link is not None:
            time.sleep(2.0)
            baseline_status = reset_hardware_to_baseline(serial_link)
            print_section("ARDUINO BASELINE RESET", {"status": baseline_status})

            status_line = request_fresh_status(serial_link)
            print_section("ARDUINO STATUS BEFORE", {"status": status_line})
            state = merge_hardware_status_into_state(state, status_line)

        print_section("SYSTEM STATE", state.model_dump())

        emit_audit_event(
            session_id=task.session_id,
            event_type="state_initialized",
            action_summary=f"Machine state initialized: {state.machine_mode.value}",
            rationale=f"enabled={state.machine_enabled}, approval_pending={state.approval_pending}, requested_angle={state.requested_angle}",
        )

        if settings.use_mock_llm:
            plan = mock_machine_generate_plan(task)
        else:
            plan = live_generate_plan(task, settings)
        print_section("EXECUTION PLAN", plan.model_dump())

        emit_audit_event(
            session_id=task.session_id,
            event_type="plan_generated",
            action_summary=plan.summary,
        )

        if settings.use_mock_llm:
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

        else:
            if serial_link is not None:
                serial_link.send_command("SET_STATE FAULT")
                serial_link.send_command("BUZZER ALERT")

            emit_audit_event(
                session_id=task.session_id,
                event_type="execution_denied",
                action_summary="Execution denied by policy.",
                decision="deny",
                rationale="; ".join(policy_decision.reasons),
            )

        if serial_link is not None:
            status_line = request_fresh_status(serial_link)
            print_section("ARDUINO STATUS AFTER", {"status": status_line})

    finally:
        if serial_link is not None:
            serial_link.close()


def main() -> None:
    settings = Settings()
    scenarios = build_machine_demo_scenarios()

    print(f"Using mock LLM mode: {settings.use_mock_llm}")

    for i, task in enumerate(scenarios, start=1):
        print(f"\n\n##### MACHINE SCENARIO {i}: {task.goal} #####")
        run_single_machine_scenario(task, settings)


if __name__ == "__main__":
    main()