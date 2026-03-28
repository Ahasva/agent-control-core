import uuid

from agent_control_core.schemas.approvals import ApprovalRequest
from agent_control_core.schemas.plans import ExecutionPlan
from agent_control_core.schemas.policies import PolicyDecision


def build_approval_request(
    session_id: str,
    plan: ExecutionPlan,
    policy_decision: PolicyDecision,
) -> ApprovalRequest:
    actions = [step.description for step in plan.steps]
    return ApprovalRequest(
        approval_id=str(uuid.uuid4()),
        session_id=session_id,
        reason="Policy requires owner approval before execution.",
        proposed_actions=actions,
        risks=policy_decision.reasons,
        user_message="This task includes sensitive actions and needs your approval before it can continue.",
    )