from pydantic import BaseModel, Field
from typing import List, Optional


class TaskRequest(BaseModel):
    user_id: str = Field(description="Unique user identifier")
    session_id: str = Field(description="Unique workflow session identifier")
    goal: str = Field(description="User's requested outcome")
    context: Optional[str] = Field(default=None, description="Additional user-provided context")
    requested_tools: List[str] = Field(default_factory=list)