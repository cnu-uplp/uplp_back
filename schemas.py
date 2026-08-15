from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class KakaoLoginRequest(BaseModel):
    code: str
    redirectUri: str


class ProfileUpdateRequest(BaseModel):
    # 가입은 재학생·졸업생만 받는다 (외부인 가입 경로는 제거).
    #   재학생  이름 + 학번 + 전화번호 + 학과
    #   졸업생  이름 + 학번 + 학과(재학 당시)   — 신청을 못 하므로 연락처는 받지 않음
    membership: str = "student"      # "student" | "alumni"
    admissionYear: str | None = None  # 학번 뒤 2자리 ("21")
    phoneNumber: str | None = None
    name: str | None = None          # 실명 — 대관 명단·인사말에 쓴다
    college: str | None = None      # 단과대
    department: str | None = None    # 학과


class NoticeCreate(BaseModel):
    category: str = "notice"         # "notice"(공지사항) | "schedule"(일정)
    title: str
    body: str | None = None
    eventDate: str | None = None     # 일정 날짜 (YYYY-MM-DD)
    pinned: bool = False
    imageUrl: str | None = None      # 업로드 후 받은 "/uploads/xxx.jpg"


class NoticeUpdate(BaseModel):
    """부분 수정 — 보낸 필드만 반영한다."""

    category: str | None = None
    title: str | None = None
    body: str | None = None
    eventDate: str | None = None
    pinned: bool | None = None
    imageUrl: str | None = None      # 빈 문자열이면 이미지 제거


class NoticeOut(BaseModel):
    id: int
    category: str
    title: str
    body: str | None = None
    eventDate: str | None = Field(default=None, validation_alias="event_date")
    pinned: bool
    imageUrl: str | None = Field(default=None, validation_alias="image_url")
    createdAt: datetime | None = Field(default=None, validation_alias="created_at")
    updatedAt: datetime | None = Field(default=None, validation_alias="updated_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CommentCreate(BaseModel):
    body: str


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    body: str
    # 작성자 표시 이름 ("김철수 21"). 라우터에서 채워 넣는다.
    author: str | None = None
    authorId: int | None = Field(default=None, validation_alias="author_id")
    createdAt: datetime | None = Field(default=None, validation_alias="created_at")


class DeprioritizedUpdate(BaseModel):
    value: bool


class RoleUpdate(BaseModel):
    role: str  # "member"(일반 부원) | "executive"(임원진) | "admin"(관리자)


class MembershipUpdate(BaseModel):
    membership: str  # "student"(재학생) | "alumni"(졸업생) | "guest"(외부인)


class ApprovalUpdate(BaseModel):
    approval: str  # "approved"(승인) | "rejected"(거절) | "pending"(보류로 되돌림)


class PositionUpdate(BaseModel):
    # "회장" · "홍보부" · "동문회장" 등 자유 입력. 빈 문자열이면 직위 해제.
    position: str


class ContentSectionCreate(BaseModel):
    page: str = "about"           # "home" | "about"
    title: str | None = None
    body: str = ""                # 마크다운
    sortOrder: int | None = None  # 없으면 맨 뒤에 붙인다
    visible: bool = True
    width: str = "full"           # "full" | "half" | "third"


class ContentSectionUpdate(BaseModel):
    """보낸 필드만 반영한다."""

    title: str | None = None
    body: str | None = None
    sortOrder: int | None = None
    visible: bool | None = None
    width: str | None = None


class ContentReorder(BaseModel):
    # 화면에 보이는 순서대로의 섹션 id 목록
    ids: list[int]


class ContentSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    page: str
    title: str | None = None
    body: str
    sortOrder: int = Field(validation_alias="sort_order")
    visible: bool
    width: str = "full"
    updatedAt: datetime | None = Field(default=None, validation_alias="updated_at")


class SwimSessionCreate(BaseModel):
    meetDate: str        # 모이는 날 (YYYY-MM-DD)
    meetTime: str        # 모이는 시각 (HH:MM)
    location: str
    capTraining: int     # 훈련부 정원
    capProgress: int     # 진도부 정원
    lateQueueEnabled: bool = False
    applyStartAt: str    # 신청 시작 (ISO datetime)
    applyEndAt: str      # 신청 마감 (ISO datetime)


class SwimCapacityUpdate(BaseModel):
    capTraining: int     # 훈련부 정원
    capProgress: int     # 진도부 정원


class SwimApplyRequest(BaseModel):
    division: str        # "training"(훈련부) | "progress"(진도부)


class UserInfo(BaseModel):
    id: int
    nickname: str | None = None
    email: str | None = None
    # ORM 속성 phone_number(snake)에서 읽되(validation_alias), 응답 키는 필드명 phoneNumber(camel)로 낸다.
    phoneNumber: str | None = Field(default=None, validation_alias="phone_number")
    college: str | None = None
    department: str | None = None
    membership: str | None = None
    admissionYear: str | None = Field(default=None, validation_alias="admission_year")
    approvalStatus: str | None = Field(default=None, validation_alias="approval_status")
    # User.display_name 프로퍼티에서 읽는다 ("김철수 21" / "김철수 21 OB")
    displayName: str | None = Field(default=None, validation_alias="display_name")
    position: str | None = None
    role: str | None = None
    isDeprioritized: bool | None = Field(default=None, validation_alias="is_deprioritized")
    # 레거시 아이디/비번 유저용 (카카오 유저는 없음)
    username: str | None = None
    name: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AuthResponse(BaseModel):
    accessToken: str
    user: UserInfo


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
