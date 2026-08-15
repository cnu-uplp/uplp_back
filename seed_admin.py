"""로컬 개발용 관리자 계정 시드.

    SEED_ADMIN_PASSWORD='...' python seed_admin.py

username/비밀번호를 환경변수로 받아 role=admin 계정을 만든다(있으면 갱신).

이 저장소는 공개되어 있으므로 비밀번호를 코드에 적지 않는다.
예전에는 admin/admin123 이 하드코딩돼 있었고 그대로 공개 저장소에 올라갔다.
그 계정이 배포 DB에 남아 있다면 즉시 지우거나 비밀번호를 바꿀 것.

운영 환경에서는 쓰지 말 것 — 운영 관리자는 ADMIN_KAKAO_IDS(카카오)로 지정한다.
"""

import os
import sys

from sqlalchemy import text

import models  # noqa: F401  (User를 Base.metadata에 등록)
from database import Base, SessionLocal, engine
from models import User
from security import hash_password

USERNAME = os.getenv("SEED_ADMIN_USERNAME", "admin")
PASSWORD = os.getenv("SEED_ADMIN_PASSWORD")

if not PASSWORD:
    sys.exit(
        "SEED_ADMIN_PASSWORD 환경변수가 필요합니다.\n"
        "  예)  SEED_ADMIN_PASSWORD='...' python seed_admin.py"
    )
if len(PASSWORD) < 12:
    sys.exit("SEED_ADMIN_PASSWORD 는 12자 이상으로 정해 주세요.")

# 테이블/컬럼 보강 (없으면 만들고, 기존 테이블엔 신규 컬럼만 추가)
Base.metadata.create_all(bind=engine)
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS college VARCHAR"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR"))
    conn.execute(
        text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR NOT NULL DEFAULT 'member'")
    )

db = SessionLocal()
try:
    admin = db.query(User).filter(User.username == USERNAME).first()
    if admin:
        admin.hashed_password = hash_password(PASSWORD)
        admin.role = "admin"
        if not admin.name:
            admin.name = "관리자"
        print(f"기존 '{USERNAME}' 계정 갱신 (role=admin)")
    else:
        db.add(
            User(
                username=USERNAME,
                name="관리자",
                hashed_password=hash_password(PASSWORD),
                role="admin",
            )
        )
        print(f"'{USERNAME}' 계정 생성 (role=admin)")
    db.commit()
finally:
    db.close()
