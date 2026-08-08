from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # 카카오 로그인
    kakao_id = Column(BigInteger, unique=True, index=True, nullable=True)
    nickname = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    college = Column(String, nullable=True)      # 단과대
    department = Column(String, nullable=True)    # 학과
    # 권한: "member"(일반 부원) / "executive"(임원진) / "admin"(관리자)
    #   executive — 정기수영 열기·마감, 공지 작성, 부원 관리
    #   admin     — executive 권한 전부 + 역할 변경(임원진 임명·해제)
    role = Column(String, nullable=False, default="member", server_default="member")
    # 후순위 상태: True면 정기수영 신청 시 후순위 대기열로 들어간다 (관리자가 지정)
    is_deprioritized = Column(Boolean, nullable=False, default=False, server_default="false")

    # 레거시 아이디/비밀번호 로그인 (카카오 유저는 값이 없음)
    username = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now())


class Notice(Base):
    """공지사항 / 일정. 관리자가 작성·수정·삭제하고 모두가 읽는다."""

    __tablename__ = "notices"

    id = Column(Integer, primary_key=True, index=True)
    # "notice"(공지사항) | "schedule"(일정)
    category = Column(String, nullable=False, default="notice", server_default="notice")
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)          # 본문 (없어도 됨 — 제목만 있는 공지 허용)
    event_date = Column(String, nullable=True)  # 일정 날짜 (YYYY-MM-DD). 공지는 비워둔다.
    pinned = Column(Boolean, nullable=False, default=False, server_default="false")
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)


class SwimSession(Base):
    """정기수영 회차 (관리자가 '정기수영 열기'로 생성)."""

    __tablename__ = "swim_sessions"

    id = Column(Integer, primary_key=True, index=True)
    meet_date = Column(String, nullable=False)   # 모이는 날 (YYYY-MM-DD)
    meet_time = Column(String, nullable=False)   # 모이는 시각 (HH:MM)
    location = Column(String, nullable=False)    # 위치
    cap_training = Column(Integer, nullable=False)  # 훈련부 정원
    cap_progress = Column(Integer, nullable=False)  # 진도부 정원
    late_queue_enabled = Column(Boolean, nullable=False, default=False)  # 후순위 제도 적용
    apply_start_at = Column(DateTime, nullable=False)  # 신청 시작 (UTC)
    apply_end_at = Column(DateTime, nullable=False)    # 신청 마감 (UTC)
    created_at = Column(DateTime, server_default=func.now())


class SwimApplication(Base):
    """정기수영 신청. 순번은 저장하지 않고 applied_at 순으로 매번 계산한다
    (취소가 생기면 자동으로 앞으로 당겨진다)."""

    __tablename__ = "swim_applications"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("swim_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    division = Column(String, nullable=False)  # "training"(훈련부) | "progress"(진도부)
    queue = Column(String, nullable=False, default="normal")  # "normal"(일반) | "late"(후순위)
    # 후순위 신청이 병합으로 합류했는지. queue는 출신 표식으로 유지되므로
    # 배정·예비 계산에서 일반 큐가 후순위보다 '항상' 앞선다.
    merged = Column(Boolean, nullable=False, default=False, server_default="false")
    applied_at = Column(DateTime, nullable=False)  # 신청 시각 (UTC) — 선착순 기준

    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_swim_app_session_user"),
    )
