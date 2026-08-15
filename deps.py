from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Authorization: Bearer <JWT> 로부터 현재 로그인 유저를 조회한다."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다.",
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다.",
        )
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """토큰이 없거나 유효하지 않으면 None (게스트 취급, 에러 없이)."""
    if credentials is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None
    return db.get(User, user_id)


# 역할 체계
#   member    일반 부원 — 신청만
#   executive 임원진   — 정기수영 열기·마감, 공지 작성, 부원 관리
#   admin     관리자   — 임원진 권한 전부 + 역할 변경(임원진 임명·해제)
# 소속 체계 (role과 다른 축)
#   student 재학생 부원 — 정기수영 신청 가능, 임원진·관리자가 될 수 있음
#   alumni  졸업생     — 명단 조회만. 신청 불가(대관 명단에 전화번호가 필요)
#   guest   외부인     — 정기수영 존재는 볼 수 있으나 명단은 마스킹, 신청 불가
MEMBERSHIP_STUDENT = "student"
MEMBERSHIP_ALUMNI = "alumni"
MEMBERSHIP_GUEST = "guest"
VALID_MEMBERSHIPS = (MEMBERSHIP_STUDENT, MEMBERSHIP_ALUMNI, MEMBERSHIP_GUEST)
# 명단의 실명을 볼 수 있는 소속 (외부인·비로그인은 마스킹)
ROSTER_VISIBLE_MEMBERSHIPS = (MEMBERSHIP_STUDENT, MEMBERSHIP_ALUMNI)

# 가입 승인 상태 (role·membership과 또 다른 축)
APPROVAL_PENDING = "pending"
APPROVAL_APPROVED = "approved"
APPROVAL_REJECTED = "rejected"
VALID_APPROVALS = (APPROVAL_PENDING, APPROVAL_APPROVED, APPROVAL_REJECTED)
# 가입 신청을 받는 소속 — 외부인(guest)은 가입 경로에서 제외했다.
SIGNUP_MEMBERSHIPS = (MEMBERSHIP_STUDENT, MEMBERSHIP_ALUMNI)


def get_current_approved(current: User = Depends(get_current_user)) -> User:
    """임원진 승인을 받은 회원만 통과. 대기·거절은 403.

    승인 전에도 로그인과 둘러보기는 되어야 한다(막으면 승인을 기다릴 방법이 없다).
    막는 것은 정기수영 신청처럼 '부원임을 전제로 하는' 기능뿐이다."""
    if current.approval_status != APPROVAL_APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="임원진 승인 후 이용할 수 있습니다.",
        )
    return current


ROLE_MEMBER = "member"
ROLE_EXECUTIVE = "executive"
ROLE_ADMIN = "admin"
VALID_ROLES = (ROLE_MEMBER, ROLE_EXECUTIVE, ROLE_ADMIN)
STAFF_ROLES = (ROLE_EXECUTIVE, ROLE_ADMIN)


def get_current_staff(current: User = Depends(get_current_user)) -> User:
    """임원진 이상(executive · admin)만 통과. 아니면 403.

    동아리 운영 업무(정기수영 개설·마감, 공지 작성, 부원 조회)의 기준선."""
    if current.role not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="임원진만 접근할 수 있습니다.",
        )
    return current


def get_current_admin(current: User = Depends(get_current_user)) -> User:
    """관리자(role == "admin")만 통과. 아니면 403.

    역할 변경처럼 권한 자체를 건드리는 작업에만 쓴다 —
    임원진이 스스로를 승격하거나 관리자를 강등시키지 못하게 하기 위함."""
    if current.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자만 접근할 수 있습니다.",
        )
    return current
