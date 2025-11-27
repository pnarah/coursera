from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SessionCreate(BaseModel):
    device_info: str
    ip_address: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    device_info: str
    ip_address: Optional[str]
    created_at: datetime
    last_active: datetime
    is_current: bool = False


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]
    total_count: int
