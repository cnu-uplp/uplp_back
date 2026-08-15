from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

# pool_size/max_overflow — 기본값(5+10=15)은 동시 신청이 몰릴 때 모자란다.
#   동기 엔드포인트라 요청이 스레드풀(최대 40)에서 도는데, 그 스레드가 전부
#   커넥션을 기다리면 정각 티케팅에서 대기가 생긴다.
# pool_pre_ping — 상시 구동 서버라 유휴 커넥션이 DB 쪽에서 먼저 끊겨 있을 수 있다.
#   끊긴 줄 모르고 쓰다 나는 오류를 막는다.
engine = create_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
