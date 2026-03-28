"""
Module contains:
1) RiskAssessment, i.e. the LLM opinion about danger
2) PolicyDecision, i.e. the output that controls execution, everything before is just input

RiskAssessment and PolicyDecision are the third and fourth step of system's pipeline:
TaskRequest (untrusted input)
    → ExecutionPlan (structured proposal)
        → RiskAssessment (LLM judgement)
            → PolicyDecision (enforced outcome)
"""

from pydantic import BaseModel, Field, ConfigDict
from .common import RiskLevel, PolicyDecisionType


class RiskAssessment(BaseModel):
    """
    Interpretation layer that functions as an advisor (is not authorative), 
    hence, system does not blindly trust this
    (LLM could underestimate risk, be tricked or ignores intent)

    produced by LLM (live) or mock logic
    """
    model_config = ConfigDict(extra="forbid")

    """
    Fields explained:
    `risk_level`: LOW / MEDIUM / HIGH / CRITICAL
    `reasons`: why this risk was assigned
    `sensitive_capabilities`: e.g. ext communication, deployment
    """
    risk_level: RiskLevel = Field(...)
    reasons: list[str] = Field(..., description="Reasons explaining the assigned risk level")
    sensitive_capabilities: list[str] = Field(..., description="Sensitive capabilities implicated by the task or plan")


class PolicyDecision(BaseModel):
    """
    Final authority, which is produced by `evaluate_plan()`, i.e. deterministic code
    => What the system allows!
    """
    model_config = ConfigDict(extra="forbid")

    """
    Fields explained:
    `decision`: either "allow" or "require_approval" or "deny"
    `reasons`: why this decision happened
    `required_approvals`: e.g. ext communication, high_risk_review
    """
    decision: PolicyDecisionType = Field(...)
    reasons: list[str] = Field(..., description="Reasons behind the policy decision")
    required_approvals: list[str] = Field(..., description="Approval categories required before proceeding")