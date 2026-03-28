from pydantic import BaseModel, Field, ConfigDict
from typing import List


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(..., description="Stable identifier for the plan step")
    description: str = Field(..., description="Short human-readable description of the step")
    tool_name: str | None = Field(..., description="Suggested tool for the step, or null if no tool is needed")
    requires_network: bool = Field(..., description="Whether the step requires network access")
    touches_money: bool = Field(..., description="Whether the step involves payment or financial action")
    touches_credentials: bool = Field(..., description="Whether the step handles secrets or credentials")
    touches_external_comms: bool = Field(..., description="Whether the step sends or drafts external communications")
    destructive_action: bool = Field(..., description="Whether the step changes or removes system state in a risky way")


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(..., description="High-level summary of the proposed execution plan")
    steps: List[PlanStep] = Field(..., description="Ordered list of proposed plan steps")