"""
Starting point of everything, i.e. the system's pipeline:
TaskRequest → ExecutionPlan → RiskAssessment → PolicyDecision

TaskRequest represents what the user wants = untrusted intent.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class TaskRequest(BaseModel):
    """
    Fields explained:
    `user_id`: who is asking? (important for permission, auditing, accountability)
    `session_id`: tracks a full workflow run (all audit logs use this)
    `goal`: raw user intent, untrusted, potentially dangerous
    `context`: extra info (often where danger hides, due to malicious intend etc.)
    `request_tools`: tools the user wants to use (not enforced)
    """
    user_id: str = Field(description="Unique user identifier")
    session_id: str = Field(description="Unique workflow session identifier")
    goal: str = Field(description="User's requested outcome")
    context: Optional[str] = Field(default=None, description="Additional user-provided context")
    requested_tools: List[str] = Field(default_factory=list)