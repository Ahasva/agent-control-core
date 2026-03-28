from pydantic import BaseModel, Field, ConfigDict
from .common import RiskLevel, PolicyDecisionType


class RiskAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_level: RiskLevel = Field(...)
    reasons: list[str] = Field(..., description="Reasons explaining the assigned risk level")
    sensitive_capabilities: list[str] = Field(..., description="Sensitive capabilities implicated by the task or plan")


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: PolicyDecisionType = Field(...)
    reasons: list[str] = Field(..., description="Reasons behind the policy decision")
    required_approvals: list[str] = Field(..., description="Approval categories required before proceeding")