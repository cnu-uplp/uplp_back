from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import Base, engine
from routers import auth, notices, swim, upalupa, users

# DB가 없어도(예: 우피 채팅만 데모하는 배포 환경) 앱은 기동되도록 감싼다.
try:
    Base.metadata.create_all(bind=engine)
except Exception as exc:  # noqa: BLE001
    print(f"[warn] DB 초기화 건너뜀: {exc}")

# create_all은 이미 존재하는 테이블에 새 컬럼을 추가하지 않는다.
# 기배포 DB(users 테이블이 이미 있는 경우)에 신규 컬럼을 idempotent하게 보강한다.
try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS college VARCHAR"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR"))
        conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR NOT NULL DEFAULT 'member'")
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_deprioritized BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE swim_applications ADD COLUMN IF NOT EXISTS merged BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
except Exception as exc:  # noqa: BLE001
    print(f"[warn] 컬럼 보강 건너뜀: {exc}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://uplp-front.vercel.app",  # 프로덕션 프론트
    ],
    # Vercel 배포/프리뷰 도메인 허용 (데모용). 프론트는 Vercel에 있으므로 여기가 핵심.
    allow_origin_regex=r"https://.*\.vercel\.app",
    # (참고) 백엔드를 어디에 올리든 CORS는 '프론트 도메인' 기준입니다.
    # 프론트가 커스텀 도메인이면 그 도메인을 allow_origins에 추가하세요.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(upalupa.router)
app.include_router(users.router)
app.include_router(swim.router)
app.include_router(notices.router)


@app.get("/")
def read_root():
    return {"message": "Hello World"}