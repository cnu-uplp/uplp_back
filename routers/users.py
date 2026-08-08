from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_admin, get_current_user
from models import User
from schemas import DeprioritizedUpdate, ProfileUpdateRequest, UserInfo

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserInfo)
def read_me(current: User = Depends(get_current_user)):
    return UserInfo.model_validate(current)


@router.patch("/me", response_model=UserInfo)
def update_me(
    payload: ProfileUpdateRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current.phone_number = payload.phoneNumber
    if payload.college is not None:
        current.college = payload.college
    if payload.department is not None:
        current.department = payload.department
    db.commit()
    db.refresh(current)
    return UserInfo.model_validate(current)


@router.patch("/{user_id}/deprioritized", response_model=UserInfo)
def set_deprioritized(
    user_id: int,
    payload: DeprioritizedUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """후순위 상태 지정/해제 — 관리자 전용.
    후순위인 회원은 (후순위 제도 적용된) 정기수영 신청 시 후순위 대기열로 들어간다."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "사용자를 찾을 수 없습니다.")
    target.is_deprioritized = payload.value
    db.commit()
    db.refresh(target)
    return UserInfo.model_validate(target)
