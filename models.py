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
    # 학번 뒤 2자리만 받는다 ("21"). 동명이인을 가르는 용도라 전체 학번은 받지 않는다
    # — 개인정보를 필요한 만큼만 수집한다는 방침.
    admission_year = Column(String, nullable=True)
    # 소속: "student"(재학생 부원) / "alumni"(졸업생) / "guest"(외부인)
    #   role(권한)과는 다른 축이다. 임원진·관리자는 student만 될 수 있고,
    #   정기수영 신청도 student만 가능하다(대관 명단에 전화번호가 필요하므로).
    #   졸업생 모임의 '회장' 같은 직위는 권한이 아니라 표시용이라 role로 표현하지 않는다.
    membership = Column(
        String, nullable=False, default="student", server_default="student"
    )

    # 가입 승인: "pending"(임원진 승인 대기) / "approved" / "rejected"
    #   role·membership과 또 다른 축이다. 승인 전에는 둘러보기만 되고
    #   정기수영 신청·명단 실명 조회가 막힌다.
    approval_status = Column(
        String, nullable=False, default="pending", server_default="pending"
    )

    # 직위: "회장" · "부회장" · "홍보부" · "동문회장" 등 자유 입력 (표시 전용).
    #   권한과 무관하다 — 졸업생 회장처럼 role은 member지만 직위는 있을 수 있다.
    #   직위는 해마다 바뀌고 동아리마다 이름이 달라서 enum으로 고정하지 않는다.
    position = Column(String, nullable=True)

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

    @property
    def display_name(self) -> str:
        """UserInfo 응답의 displayName. 규칙은 아래 display_name() 하나에만 둔다."""
        return display_name(self)


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


class ContentSection(Base):
    """홈·동아리 소개 페이지의 본문 섹션. 임원진이 웹에서 직접 고친다.

    문구가 코드에 박혀 있으면 회칙·회비·활동 시간이 바뀔 때마다 배포를 해야 한다.
    섹션 단위로 DB에 두고 마크다운으로 쓰게 해서, 추가·삭제·순서 변경까지 화면에서 끝낸다.

    page  — "home"(홈 하단) / "about"(동아리 소개). 페이지별로 목록이 갈린다.
    body  — 마크다운. 프론트가 안전한 부분집합만 렌더한다(HTML 주입 불가).
    """

    __tablename__ = "content_sections"

    id = Column(Integer, primary_key=True, index=True)
    page = Column(String, nullable=False, default="about", server_default="about")
    title = Column(String, nullable=True)   # 없으면 제목 없이 본문만 렌더
    body = Column(Text, nullable=False, default="", server_default="")
    # 정렬 기준. 화면에서 위/아래로 옮길 때 이 값만 바꾼다.
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    # 지우지 않고 잠시 내리고 싶을 때가 있다 (준비 중인 안내 등)
    visible = Column(Boolean, nullable=False, default=True, server_default="true")
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
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


def display_name(u: "User") -> str:
    """화면에 쓰는 이름. 동명이인을 학번으로 가르고, 졸업생은 OB를 붙인다.

        김철수 21        재학생
        김철수 21 OB     졸업생

    ⚠️ 레인대관 신청서(docx)에는 쓰지 않는다 — 그쪽은 스포렉스에 내는 공문서라
       실명만 들어가야 한다. 그래서 name 필드를 따로 유지한다.
    """
    base = u.name or u.nickname or f"회원{u.id}"
    if not u.admission_year:
        return base
    if u.membership == "alumni":
        return f"{base} {u.admission_year} OB"
    if u.membership == "student":
        return f"{base} {u.admission_year}"
    return base
