from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional
from enum import Enum


class SessionStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"  # Could be used for explicit logout
    EXPIRED = "expired"


class ResearchSession(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    user_id: Optional[str] = None  # Link to user model when available
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None # Absolute expiration time
    status: SessionStatus = SessionStatus.ACTIVE
    data: dict = Field(default_factory=dict) # For storing arbitrary session data

    class Config:
        # Allows using enum values directly
        use_enum_values = True 