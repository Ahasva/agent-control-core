from agent_control_core.demo import (
    build_demo_scenarios,
    mock_assess_risk,
    mock_generate_plan,
)
from agent_control_core.policies.engine import evaluate_plan
from agent_control_core.schemas.common import PolicyDecisionType


def test_demo_scenario_1_mock() -> None:
    task = build_demo_scenarios()[0]
    plan = mock_generate_plan(task)
    risk = mock_assess_risk(task, plan)
    decision = evaluate_plan(task, plan, risk)

    assert decision.decision == PolicyDecisionType.ALLOW


def test_demo_scenario_2_mock() -> None:
    task = build_demo_scenarios()[1]
    plan = mock_generate_plan(task)
    risk = mock_assess_risk(task, plan)
    decision = evaluate_plan(task, plan, risk)

    assert decision.decision == PolicyDecisionType.REQUIRE_APPROVAL


def test_demo_scenario_3_mock() -> None:
    task = build_demo_scenarios()[2]
    plan = mock_generate_plan(task)
    risk = mock_assess_risk(task, plan)
    decision = evaluate_plan(task, plan, risk)

    assert decision.decision == PolicyDecisionType.DENY