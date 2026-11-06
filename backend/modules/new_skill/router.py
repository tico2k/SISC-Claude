# backend/modules/new_skill/router.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.core.dependencies import get_current_user
from backend import models as core_models # UserRoles 등 필요 시
from . import models, schemas

router = APIRouter(
    prefix="/new-skill",
    tags=["New Skill"]
)

@router.post("/", response_model=schemas.NewSkillResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    item: schemas.NewSkillCreate, 
    current_user: core_models.User = Depends(get_current_user), # 권한 연동
    db: Session = Depends(get_db)
):
    new_item = models.NewSkillModel(name=item.name)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item
