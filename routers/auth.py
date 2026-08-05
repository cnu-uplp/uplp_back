import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User
from schemas import (
    AuthResponse,
    JoinRequest,
    KakaoLoginRequest,
    LoginRequest,
    UserInfo,
)
from security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USERME_URL = "https://kapi.kakao.com/v2/user/me"


@router.post("/join", response_model=AuthResponse)
def join(payload: JoinRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 아이디입니다.",
        )

    user = User(
        username=payload.username,
        name=payload.name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(subject=str(user.id))
    return AuthResponse(accessToken=access_token, user=UserInfo.model_validate(user))


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
                detail="카카오 토큰 교환에 실패했습니다.",
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
                detail="카카오 사용자 조회에 실패했습니다.",
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

    access_token = create_access_token(subject=str(user.id))
    return AuthResponse(accessToken=access_token, user=UserInfo.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 일치하지 않습니다.",
        )

    access_token = create_access_token(subject=str(user.id))
    return AuthResponse(accessToken=access_token, user=UserInfo.model_validate(user))
