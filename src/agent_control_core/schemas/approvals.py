from pydantic import BaseModel, Field
from typing import List, Optional


class ApprovalRequest(BaseModel):
    approval_id: str
    session_id: str
    reason: str
    proposed_actions: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    user_message: str


class ApprovalResponse(BaseModel):
    approval_id: str
    approved: bool
    approver_id: str
    comment: Optional[str] = None