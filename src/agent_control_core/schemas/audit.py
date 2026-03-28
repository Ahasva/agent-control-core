from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AuditEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str
    actor: str
    session_id: str
    action_summary: str
    decision: Optional[str] = None
    rationale: Optional[str] = None