from agent_control_core.policies.rules import (
    plan_is_destructive,
    plan_touches_external_comms,
    task_is_critical_by_intent,
    task_requests_review_bypass,
    task_targets_production_config,
)
from agent_control_core.schemas.plans import ExecutionPlan, PlanStep
from agent_control_core.schemas.tasks import TaskRequest


def test_plan_touches_external_comms() -> None:
    plan = ExecutionPlan(
        summary="External communication plan",
        steps=[
            PlanStep(
                step_id="s1",
                description="Send an email",
                tool_name="email_sender",
                requires_network=False,
                touches_money=False,
                touches_credentials=False,
                touches_external_comms=True,
                destructive_action=False,
            )
        ],
    )
    assert plan_touches_external_comms(plan) is True


def test_plan_is_destructive() -> None:
    plan = ExecutionPlan(
        summary="Destructive plan",
        steps=[
            PlanStep(
                step_id="s1",
                description="Delete production config",
                tool_name="config_manager",
                requires_network=False,
                touches_money=False,
                touches_credentials=False,
                touches_external_comms=False,
                destructive_action=True,
            )
        ],
    )
    assert plan_is_destructive(plan) is True


def test_task_requests_review_bypass() -> None:
    task = TaskRequest(
        user_id="u1",
        session_id="s1",
        goal="Deploy this now",
        context="Skip review if possible",
        requested_tools=[],
    )
    assert task_requests_review_bypass(task) is True


def test_task_targets_production_config() -> None:
    task = TaskRequest(
        user_id="u1",
        session_id="s1",
        goal="Replace the current production configuration immediately",
        context=None,
        requested_tools=[],
    )
    assert task_targets_production_config(task) is True


def test_task_is_critical_by_intent() -> None:
    task = TaskRequest(
        user_id="u1",
        session_id="s1",
        goal="Delete the current production configuration and replace it immediately",
        context="Skip review if possible",
        requested_tools=[],
    )
    assert task_is_critical_by_intent(task) is True