from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import User
from schemas import PhoneUpdateRequest, UserInfo

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserInfo)
def read_me(current: User = Depends(get_current_user)):
    return UserInfo.model_validate(current)


@router.patch("/me", response_model=UserInfo)
def update_me(
    payload: PhoneUpdateRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current.phone_number = payload.phoneNumber
    db.commit()
    db.refresh(current)
    return UserInfo.model_validate(current)
