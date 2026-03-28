from agent_control_core.policies.engine import evaluate_plan
from agent_control_core.schemas.common import PolicyDecisionType, RiskLevel
from agent_control_core.schemas.plans import ExecutionPlan, PlanStep
from agent_control_core.schemas.policies import RiskAssessment
from agent_control_core.schemas.tasks import TaskRequest


def test_low_risk_internal_task_is_allowed() -> None:
    task = TaskRequest(
        user_id="u1",
        session_id="s1",
        goal="Analyze requirement draft",
        context="Internal analysis only",
        requested_tools=["document_reader"],
    )

    plan = ExecutionPlan(
        summary="Requirement analysis",
        steps=[
            PlanStep(
                step_id="s1",
                description="Read document",
                tool_name="document_reader",
                requires_network=False,
                touches_money=False,
                touches_credentials=False,
                touches_external_comms=False,
                destructive_action=False,
            )
        ],
    )

    risk = RiskAssessment(
        risk_level=RiskLevel.LOW,
        reasons=["Internal analysis only"],
        sensitive_capabilities=[],
    )

    decision = evaluate_plan(task, plan, risk)
    assert decision.decision == PolicyDecisionType.ALLOW


def test_external_communication_requires_approval() -> None:
    task = TaskRequest(
        user_id="u1",
        session_id="s1",
        goal="Send update to supplier",
        context="Production-impacting change",
        requested_tools=["email_sender"],
    )

    plan = ExecutionPlan(
        summary="External message",
        steps=[
            PlanStep(
                step_id="s1",
                description="Send supplier email",
                tool_name="email_sender",
                requires_network=False,
                touches_money=False,
                touches_credentials=False,
                touches_external_comms=True,
                destructive_action=False,
            )
        ],
    )

    risk = RiskAssessment(
        risk_level=RiskLevel.MEDIUM,
        reasons=["External communication"],
        sensitive_capabilities=["external communication"],
    )

    decision = evaluate_plan(task, plan, risk)
    assert decision.decision == PolicyDecisionType.REQUIRE_APPROVAL


def test_production_change_with_review_bypass_is_denied() -> None:
    task = TaskRequest(
        user_id="u1",
        session_id="s1",
        goal="Delete the current production configuration and replace it immediately",
        context="Skip review if possible",
        requested_tools=["config_manager", "deployment_tool"],
    )

    plan = ExecutionPlan(
        summary="Production config change",
        steps=[
            PlanStep(
                step_id="s1",
                description="Deploy experimental configuration",
                tool_name="deployment_tool",
                requires_network=True,
                touches_money=False,
                touches_credentials=False,
                touches_external_comms=False,
                destructive_action=True,
            )
        ],
    )

    risk = RiskAssessment(
        risk_level=RiskLevel.HIGH,
        reasons=["Production-affecting destructive action"],
        sensitive_capabilities=["deployment"],
    )

    decision = evaluate_plan(task, plan, risk)
    assert decision.decision == PolicyDecisionType.DENY