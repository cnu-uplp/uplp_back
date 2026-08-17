import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User
from schemas import AuthResponse, KakaoLoginRequest, UserInfo
from security import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USERME_URL = "https://kapi.kakao.com/v2/user/me"


# 로그인 경로는 카카오 하나뿐이다.
#   - 자체 회원가입(/join): 누구나 계정을 만들 수 있는 경로를 열어둘 이유가 없어 제거.
#   - 아이디/비밀번호 로그인(/login): 실제로 쓰지 않는데 시도 횟수 제한도 없어
#     무제한 대입 공격 표면만 남아 있었다. 2026-08-16 제거.
#     로컬 개발용 토큰이 필요하면 dev_login.py 를 쓴다.
# 개인정보를 최소한만 보관한다는 방침과도 맞는다 — 비밀번호를 아예 다루지 않는다.


@router.post("/kakao", response_model=AuthResponse)
def kakao_login(payload: KakaoLoginRequest, db: Session = Depends(get_db)):
    if not settings.kakao_rest_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카카오 로그인 설정(KAKAO_REST_API_KEY)이 필요합니다.",
        )

    token_data = {
        "grant_type": "authorization_code",
        "client_id": settings.kakao_rest_api_key,
        "redirect_uri": payload.redirectUri,  # 프론트/콘솔에 등록된 값과 동일해야 함
        "code": payload.code,
    }
    if settings.kakao_client_secret:
        token_data["client_secret"] = settings.kakao_client_secret

    with httpx.Client(timeout=10) as client:
        # ① 인가 코드 → 카카오 access token
        token_res = client.post(
            KAKAO_TOKEN_URL,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"카카오 토큰 교환에 실패했습니다: {token_res.text}",
            )
        kakao_token = token_res.json().get("access_token")

        # ② 사용자 정보 조회
        me_res = client.get(
            KAKAO_USERME_URL,
            headers={"Authorization": f"Bearer {kakao_token}"},
        )
        if me_res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"카카오 사용자 조회에 실패했습니다: {me_res.text}",
            )
        me = me_res.json()

    kakao_id = me.get("id")
    account = me.get("kakao_account", {})
    profile = account.get("profile", {})
    nickname = profile.get("nickname") or me.get("properties", {}).get("nickname")
    email = account.get("email")

    # ③ find-or-create (카카오 id 기준)
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    if user is None:
        user = User(kakao_id=kakao_id, nickname=nickname, email=email)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # 닉네임/이메일 최신화
        changed = False
        if nickname and user.nickname != nickname:
            user.nickname = nickname
            changed = True
        if email and user.email != email:
            user.email = email
            changed = True
        if changed:
            db.commit()
            db.refresh(user)

    # 관리자 부트스트랩: env(ADMIN_KAKAO_IDS)에 있는 카카오 id면 admin으로 승격
    admin_ids = {x.strip() for x in settings.admin_kakao_ids.split(",") if x.strip()}
    if str(kakao_id) in admin_ids and user.role != "admin":
        user.role = "admin"
        db.commit()
        db.refresh(user)

    # 승인제를 끈 운영(시범·데모)에서는 로그인하는 순간 대기 상태를 푼다.
    # 이렇게 해두면 승인제를 켜고 운영하다 끈 경우에도, 이미 대기 중이던 사람들이
    # 재로그인만으로 풀린다(관리자가 한 명씩 눌러줄 필요가 없다).
    if not settings.require_approval and user.approval_status == "pending":
        user.approval_status = "approved"
        db.commit()
        db.refresh(user)

    access_token = create_access_token(subject=str(user.id))
    return AuthResponse(accessToken=access_token, user=UserInfo.model_validate(user))
