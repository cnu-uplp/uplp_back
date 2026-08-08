"""로컬 테스트용 관리자 계정 시드.

    python seed_admin.py

admin / admin123 (role=admin) 계정을 만든다(이미 있으면 비번·role 갱신).
운영 환경에서는 쓰지 말 것 — 운영 관리자는 ADMIN_KAKAO_IDS(카카오)로 지정한다.
"""

from sqlalchemy import text

import models  # noqa: F401  (User를 Base.metadata에 등록)
from database import Base, SessionLocal, engine
from models import User
from security import hash_password

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
    admin = db.query(User).filter(User.username == "admin").first()
    if admin:
        admin.hashed_password = hash_password("admin123")
        admin.role = "admin"
        if not admin.name:
            admin.name = "관리자"
        print("기존 admin 계정 갱신 (role=admin)")
    else:
        db.add(
            User(
                username="admin",
                name="관리자",
                hashed_password=hash_password("admin123"),
                role="admin",
            )
        )
        print("admin 계정 생성 (admin / admin123, role=admin)")
    db.commit()
finally:
    db.close()
