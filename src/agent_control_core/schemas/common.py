from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyDecisionType(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class Confidence(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    rationale: Optional[str] = None