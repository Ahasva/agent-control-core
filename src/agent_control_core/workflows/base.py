from pydantic import BaseModel
from typing import Optional

from agent_control_core.schemas.tasks import TaskRequest
from agent_control_core.schemas.plans import ExecutionPlan
from agent_control_core.schemas.policies import RiskAssessment, PolicyDecision
from agent_control_core.schemas.approvals import ApprovalRequest


class WorkflowState(BaseModel):
    task: TaskRequest
    plan: Optional[ExecutionPlan] = None
    risk: Optional[RiskAssessment] = None
    policy_decision: Optional[PolicyDecision] = None
    approval_request: Optional[ApprovalRequest] = None