from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from deps import (
    APPROVAL_APPROVED,
    APPROVAL_PENDING,
    APPROVAL_REJECTED,
    MEMBERSHIP_STUDENT,
    SIGNUP_MEMBERSHIPS,
    VALID_APPROVALS,
    ROLE_ADMIN,
    ROLE_MEMBER,
    VALID_MEMBERSHIPS,
    VALID_ROLES,
    get_current_admin,
    get_current_staff,
    get_current_user,
)
from models import User
from schemas import (
    ApprovalUpdate,
    DeprioritizedUpdate,
    MembershipUpdate,
    PositionUpdate,
    ProfileUpdateRequest,
    RoleUpdate,
    UserInfo,
)

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
    # 가입은 재학생·졸업생만. 외부인(guest)은 가입 경로를 열어두지 않는다.
    if payload.membership not in SIGNUP_MEMBERSHIPS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "가입은 재학생 또는 졸업생만 가능합니다.",
        )
    # 학번은 동명이인을 가르는 핵심 값이라 두 소속 모두 필수.
    year = (payload.admissionYear or "").strip()
    if not year.isdigit() or len(year) != 2:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "학번은 두 자리 숫자로 입력해주세요. (예: 21)"
        )
    current.admission_year = year
    # 학생만 전화번호가 필수 (대관 명단에 들어가므로).
    # 졸업생·외부인은 신청을 못 하니 연락처를 받지 않는다 — 개인정보 최소 수집.
    if payload.membership == MEMBERSHIP_STUDENT:
        if not (payload.phoneNumber or "").strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "재학생은 휴대폰 번호가 필요합니다."
            )
        current.phone_number = payload.phoneNumber
    else:
        # 소속을 학생 → 졸업생/외부인으로 바꾸면 더 이상 쓰지 않는 연락처를 지운다.
        current.phone_number = None

    # 학생이 아니게 되면 임원진·관리자 자격도 잃는다 (아래 set_role과 같은 규칙).
    if payload.membership != MEMBERSHIP_STUDENT and current.role != ROLE_MEMBER:
        current.role = ROLE_MEMBER

    current.membership = payload.membership
    # 가입 정보를 (다시) 제출하면 승인 대기로 돌아간다.
    # 이미 승인된 회원이 학과만 고쳤다고 다시 대기시키면 안 되므로 거절 상태만 되살린다.
    if current.approval_status not in (APPROVAL_APPROVED, APPROVAL_PENDING):
        current.approval_status = APPROVAL_PENDING
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


@router.get("/pending-count")
def pending_count(
    staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """승인 대기 인원 수 — 임원진 상단바 배지에 쓴다.

    배지가 없으면 임원진이 대기자가 있는지 모른 채 며칠씩 방치되는 사고가 난다."""
    n = db.query(User).filter(User.approval_status == APPROVAL_PENDING).count()
    return {"count": n}


@router.patch("/{user_id}/approval", response_model=UserInfo)
def set_approval(
    user_id: int,
    payload: ApprovalUpdate,
    staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """가입 승인·거절 — 임원진 이상.

    거절하면 수집한 개인정보(연락처·학과·학번)를 지운다.
    '최소한만 보관한다'는 방침상, 부원이 아닌 사람의 정보를 남길 이유가 없다.
    계정 자체는 남겨 재신청이 가능하게 둔다(카카오로 다시 로그인하면 어차피 같은 계정)."""
    if payload.approval not in VALID_APPROVALS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"승인 상태는 {', '.join(VALID_APPROVALS)} 중 하나여야 합니다.",
        )
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "사용자를 찾을 수 없습니다.")

    if target.id == staff.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "자기 자신의 승인 상태는 바꿀 수 없습니다."
        )

    target.approval_status = payload.approval
    if payload.approval == APPROVAL_REJECTED:
        target.phone_number = None
        target.college = None
        target.department = None
        target.admission_year = None
        target.role = ROLE_MEMBER
    db.commit()
    db.refresh(target)
    return UserInfo.model_validate(target)


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

    # 임원진·관리자는 재학생만 가능하다.
    # 졸업생 모임의 '회장' 같은 직위는 시스템 권한이 아니라 표시용이므로 role로 주지 않는다.
    if payload.role != ROLE_MEMBER and target.membership != MEMBERSHIP_STUDENT:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "임원진·관리자는 재학생만 지정할 수 있습니다.",
        )

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


@router.patch("/{user_id}/membership", response_model=UserInfo)
def set_membership(
    user_id: int,
    payload: MembershipUpdate,
    staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """소속 변경(재학생 → 졸업생 등) — 임원진 이상.

    졸업하면 임원진 자격이 사라지므로 role도 함께 내린다.
    (여기는 임원진이 기존 회원을 옮기는 경로라 guest도 허용한다 — 가입 경로와 다르다.)"""
    if payload.membership not in VALID_MEMBERSHIPS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"소속은 {', '.join(VALID_MEMBERSHIPS)} 중 하나여야 합니다.",
        )
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "사용자를 찾을 수 없습니다.")

    if payload.membership != MEMBERSHIP_STUDENT and target.role == ROLE_ADMIN:
        # 마지막 관리자가 졸업 처리되면 아무도 역할을 바꿀 수 없게 된다.
        admin_count = db.query(User).filter(User.role == ROLE_ADMIN).count()
        if admin_count <= 1:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "마지막 관리자는 소속을 바꿀 수 없습니다. 먼저 다른 관리자를 지정하세요.",
            )

    target.membership = payload.membership
    if payload.membership != MEMBERSHIP_STUDENT:
        target.role = ROLE_MEMBER          # 학생이 아니면 임원진 자격 없음
        target.phone_number = None         # 신청을 못 하므로 연락처를 보관하지 않는다
    db.commit()
    db.refresh(target)
    return UserInfo.model_validate(target)


@router.patch("/{user_id}/position", response_model=UserInfo)
def set_position(
    user_id: int,
    payload: PositionUpdate,
    staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """직위 지정·해제 — 임원진 이상. 표시 전용이라 권한에 영향을 주지 않는다.

    소속을 가리지 않는다 — 졸업생 '동문회장'처럼 role은 member여도 직위는 가질 수 있다.
    빈 문자열을 보내면 직위를 지운다."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "사용자를 찾을 수 없습니다.")

    value = payload.position.strip()
    if len(value) > 20:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "직위는 20자 이내로 입력해주세요.")
    target.position = value or None
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
