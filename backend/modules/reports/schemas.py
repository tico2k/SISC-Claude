# backend/modules/reports/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ReportBase(BaseModel):
    title: str
    summary: Optional[str] = None

class ReportCreate(ReportBase):
    pass

class ReportResponse(ReportBase):
    id: int
    created_at: datetime
    created_by_id: int
    
    class Config:
        from_attributes = True
