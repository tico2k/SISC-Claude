# backend/modules/new_skill/models.py
from sqlalchemy import Column, Integer, String
from backend.core.database import Base

class NewSkillModel(Base):
    __tablename__ = "new_skill_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
