
# backend/modules/new_skill/schemas.py
from pydantic import BaseModel, ConfigDict

class NewSkillCreate(BaseModel):
    name: str

class NewSkillResponse(NewSkillCreate):
    id: int
    
    model_config = ConfigDict(from_attributes=True)
