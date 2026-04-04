"""
POLICY LOGIC (JUDGEMENT), hence, this module serves as the actual decision maker
(by calling and combining the helper functions from the rule-set)

The POLICY LOGIC uses the decision from the DECISION LOGIC (FACTS) and decides (JUDGEMENT):
"allow" or "require approval" or "deny".
"""

from agent_control_core.machine.intent_parser import parse_machine_intent
from agent_control_core.policies.rules import (
    plan_is_destructive,
    plan_touches_credentials,
    plan_touches_external_comms,
    plan_touches_money,
    requested_angle_from_state_is_safe,
    state_is_faulted,
    state_is_locked,
    state_is_ready,
    state_requires_approval,
    task_is_critical_by_intent,
    task_requests_immediate_motion,
    task_requests_review_bypass,
    task_requests_safety_bypass,
    task_targets_production_config,
)
from agent_control_core.schemas.common import PolicyDecisionType, RiskLevel
from agent_control_core.schemas.plans import ExecutionPlan
from agent_control_core.schemas.policies import PolicyDecision, RiskAssessment
from agent_control_core.schemas.state import SystemState
from agent_control_core.schemas.tasks import TaskRequest


def evaluate_plan(
    task: TaskRequest,
    plan: ExecutionPlan,
    risk: RiskAssessment,
    state: SystemState,
) -> PolicyDecision:
    """
    `evaluate_plan()` takes the original task (TaskRequest),
    the generated plan (ExecutionPlan), the risk (RiskAssessment),
    and the current system state (SystemState),
    and returns a PolicyDecision object.
    """
    reasons: list[str] = []
    required_approvals: list[str] = []

    touches_money = plan_touches_money(plan)
    touches_credentials = plan_touches_credentials(plan)
    touches_external_comms = plan_touches_external_comms(plan)
    is_destructive = plan_is_destructive(plan)

    parsed = parse_machine_intent(
        f"{task.goal} {task.context or ''}",
        current_angle=state.servo_angle,
    )
    intent_type = parsed.intent_type if parsed is not None else None

    fault_allowed_intents = {"recover_fault", "safe_shutdown"}

    # -------------------------------------------------------------------------
    # HARD DENY RULES
    # -------------------------------------------------------------------------

    if task_is_critical_by_intent(task):
        return PolicyDecision(
            decision=PolicyDecisionType.DENY,
            reasons=[
                "Task explicitly combines production-affecting configuration change with review bypass intent."
            ],
            required_approvals=[],
        )

    if task_requests_safety_bypass(task):
        return PolicyDecision(
            decision=PolicyDecisionType.DENY,
            reasons=[
                "Task text explicitly attempts to override or bypass safety constraints."
            ],
            required_approvals=[],
        )

    if state_is_faulted(state) and intent_type not in fault_allowed_intents:
        return PolicyDecision(
            decision=PolicyDecisionType.DENY,
            reasons=[
                "Machine is in fault state and cannot execute requested actions."
            ],
            required_approvals=[],
        )

    if state_is_locked(state):
        return PolicyDecision(
            decision=PolicyDecisionType.DENY,
            reasons=[
                "Machine is locked and requires reset or acknowledgement before proceeding."
            ],
            required_approvals=[],
        )

    if not requested_angle_from_state_is_safe(state):
        return PolicyDecision(
            decision=PolicyDecisionType.DENY,
            reasons=[
                "Requested angle from machine state is outside the allowed safe range."
            ],
            required_approvals=[],
        )

    if task_requests_immediate_motion(task) and not state_is_ready(state):
        return PolicyDecision(
            decision=PolicyDecisionType.DENY,
            reasons=[
                "Immediate motion was requested while the machine is not in READY state."
            ],
            required_approvals=[],
        )

    if risk.risk_level == RiskLevel.CRITICAL:
        return PolicyDecision(
            decision=PolicyDecisionType.DENY,
            reasons=[
                "Critical-risk actions are denied by default."
            ],
            required_approvals=[],
        )

    # -------------------------------------------------------------------------
    # FAULT-STATE RECOVERY / SHUTDOWN CARVE-OUT
    # -------------------------------------------------------------------------

    if state_is_faulted(state) and intent_type in fault_allowed_intents:
        return PolicyDecision(
            decision=PolicyDecisionType.ALLOW,
            reasons=[
                "Fault-state recovery or safe shutdown is explicitly permitted."
            ],
            required_approvals=[],
        )

    # -------------------------------------------------------------------------
    # APPROVAL-REQUIRED RULES
    # -------------------------------------------------------------------------

    if touches_money:
        reasons.append("Plan includes money-related actions.")
        required_approvals.append("financial_action")

    if touches_credentials:
        reasons.append("Plan includes credential-sensitive actions.")
        required_approvals.append("credential_sensitive_action")

    if touches_external_comms:
        reasons.append("Plan includes external communication.")
        required_approvals.append("external_communication")

    if is_destructive:
        reasons.append("Plan includes destructive or irreversible actions.")
        required_approvals.append("destructive_action")

    if risk.risk_level == RiskLevel.HIGH:
        if state.approval_granted:
            reasons.append("High-risk action was approved by an operator through the machine approval channel.")
        else:
            reasons.append("Risk level assessed as high.")
            required_approvals.append("high_risk_review")

    if task_requests_review_bypass(task):
        reasons.append("Task text indicates review bypass intent.")
        required_approvals.append("review_bypass_signal")

    if task_targets_production_config(task) and not task_is_critical_by_intent(task):
        reasons.append("Task targets production-affecting configuration change.")
        required_approvals.append("production_change_review")

    if state_requires_approval(state):
        reasons.append("Machine state indicates that approval is currently required.")
        required_approvals.append("machine_state_approval")

    if required_approvals:
        return PolicyDecision(
            decision=PolicyDecisionType.REQUIRE_APPROVAL,
            reasons=sorted(set(reasons)),
            required_approvals=sorted(set(required_approvals)),
        )

    # -------------------------------------------------------------------------
    # DEFAULT ALLOW
    # -------------------------------------------------------------------------

    return PolicyDecision(
        decision=PolicyDecisionType.ALLOW,
        reasons=["No policy rule blocked execution."],
        required_approvals=[],
    )
