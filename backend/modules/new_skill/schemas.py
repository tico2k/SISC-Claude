
# backend/modules/new_skill/schemas.py
from pydantic import BaseModel

class NewSkillCreate(BaseModel):
    name: str

class NewSkillResponse(NewSkillCreate):
    id: int
    
    class Config:
        from_attributes = True # ORM 모델을 Pydantic 객체로 자동 변환 (v2에서는 ConfigDict 사용 권장)
