from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from config import settings
from database import Base, engine
from routers import auth, content, notices, swim, upalupa, users

# DB가 없어도(예: 우피 채팅만 데모하는 배포 환경) 앱은 기동되도록 감싼다.
try:
    Base.metadata.create_all(bind=engine)
except Exception as exc:  # noqa: BLE001
    print(f"[warn] DB 초기화 건너뜀: {exc}")

# create_all은 이미 존재하는 테이블에 새 컬럼을 추가하지 않는다.
# 기배포 DB(users 테이블이 이미 있는 경우)에 신규 컬럼을 idempotent하게 보강한다.
try:
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS membership VARCHAR "
                "NOT NULL DEFAULT 'student'"
            )
        )
        conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS admission_year VARCHAR")
        )
        # 승인 컬럼은 '새로 생겼을 때만' 기존 회원을 일괄 승인한다.
        # 매 기동마다 UPDATE를 돌리면 임원진이 거절해 둔 사람이 되살아난다.
        approval_existed = conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='users' AND column_name='approval_status'"
            )
        ).first()
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS approval_status VARCHAR "
                "NOT NULL DEFAULT 'pending'"
            )
        )
        if not approval_existed:
            # 승인제 도입 이전에 가입한 회원이 갑자기 전부 잠기면 정기수영을 못 연다.
            conn.execute(text("UPDATE users SET approval_status = 'approved'"))
            print("[migrate] 기존 회원 전원을 approved로 설정했습니다.")
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS position VARCHAR"))
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
        # content_sections는 create_all이 새로 만들지만, 이미 만들어진 뒤에
        # 추가된 컬럼은 create_all이 손대지 않으므로 여기서 보강한다.
        conn.execute(
            text(
                "ALTER TABLE content_sections ADD COLUMN IF NOT EXISTS width VARCHAR "
                "NOT NULL DEFAULT 'full'"
            )
        )
        conn.execute(
            text("ALTER TABLE notices ADD COLUMN IF NOT EXISTS image_url VARCHAR")
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
    # ⚠️ 여기에 와일드카드(allow_origin_regex=r"https://.*\.vercel\.app")를 두지 말 것.
    #    누구나 Vercel에 사이트를 배포해서 이 API를 호출할 수 있게 된다.
    # (참고) 백엔드를 어디에 올리든 CORS는 '프론트 도메인' 기준이다.
    #        백엔드 주소(api.*)는 여기 넣을 필요가 없고,
    #        프론트가 커스텀 도메인으로 바뀌면 그 도메인을 allow_origins에 추가한다.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(upalupa.router)
app.include_router(users.router)
app.include_router(swim.router)
app.include_router(notices.router)
app.include_router(content.router)

# 공지 첨부 이미지 정적 서빙.
# nginx가 모든 경로를 이 앱으로 넘기므로 여기서 처리하면 nginx 설정을 안 건드려도 된다.
# 폴더가 없으면 StaticFiles가 기동 시 예외를 내므로 먼저 만들어 둔다.
_uploads = Path(settings.upload_dir)
_uploads.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads), name="uploads")


@app.get("/")
def read_root():
    return {"message": "Hello World"}