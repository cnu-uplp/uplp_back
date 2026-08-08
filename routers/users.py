from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from deps import (
    ROLE_ADMIN,
    VALID_ROLES,
    get_current_admin,
    get_current_staff,
    get_current_user,
)
from models import User
from schemas import DeprioritizedUpdate, ProfileUpdateRequest, RoleUpdate, UserInfo

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
    if payload.name is not None:
        current.name = payload.name
    if payload.college is not None:
        current.college = payload.college
    if payload.department is not None:
        current.department = payload.department
    db.commit()
    db.refresh(current)
    return UserInfo.model_validate(current)


@router.get("", response_model=list[UserInfo])
def list_users(
    staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """가입한 부원 전체 조회 — 임원진 이상 전용.

    연락처·학과가 함께 나가므로 절대 공개하지 않는다
    (레인대관 명단 작성에 필요해서 임원진에게만 연다)."""
    users = db.query(User).order_by(User.id.desc()).all()
    return [UserInfo.model_validate(u) for u in users]


@router.patch("/{user_id}/role", response_model=UserInfo)
def set_role(
    user_id: int,
    payload: RoleUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """역할 변경(임원진 임명·해제) — 관리자 전용.

    임원진(executive)에게는 열지 않는다. 열면 임원진이 스스로를 admin으로
    올리거나 관리자를 강등시킬 수 있어 권한 체계가 무너진다."""
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"역할은 {', '.join(VALID_ROLES)} 중 하나여야 합니다.",
        )

    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "사용자를 찾을 수 없습니다.")

    # 자기 자신 강등 금지 — 실수로 관리자 권한을 잃고 잠기는 것을 막는다.
    if target.id == admin.id and payload.role != ROLE_ADMIN:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "자기 자신의 역할은 변경할 수 없습니다. 다른 관리자에게 요청하세요.",
        )

    # 마지막 관리자 강등 금지 — 아무도 역할을 바꿀 수 없는 상태가 되어버린다.
    if target.role == ROLE_ADMIN and payload.role != ROLE_ADMIN:
        admin_count = db.query(User).filter(User.role == ROLE_ADMIN).count()
        if admin_count <= 1:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "마지막 관리자는 강등할 수 없습니다. 먼저 다른 관리자를 지정하세요.",
            )

    target.role = payload.role
    db.commit()
    db.refresh(target)
    return UserInfo.model_validate(target)


@router.patch("/{user_id}/deprioritized", response_model=UserInfo)
def set_deprioritized(
    user_id: int,
    payload: DeprioritizedUpdate,
    staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """후순위 상태 지정/해제 — 임원진 이상.
    후순위인 회원은 (후순위 제도 적용된) 정기수영 신청 시 후순위 대기열로 들어간다."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "사용자를 찾을 수 없습니다.")
    target.is_deprioritized = payload.value
    db.commit()
    db.refresh(target)
    return UserInfo.model_validate(target)
