from datetime import datetime, timedelta, timezone

from jose import jwt

from config import settings

# 비밀번호는 다루지 않는다. 로그인은 카카오 하나뿐이라 해싱·검증 함수가 필요 없고,
# 안 쓰는 인증 경로를 남겨두면 공격 표면만 된다. (2026-08-16 아이디/비밀번호 로그인 제거)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
