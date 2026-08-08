from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class KakaoLoginRequest(BaseModel):
    code: str
    redirectUri: str


class ProfileUpdateRequest(BaseModel):
    phoneNumber: str
    name: str | None = None          # 실명 — 대관 명단·인사말에 쓴다
    college: str | None = None      # 단과대
    department: str | None = None    # 학과


class NoticeCreate(BaseModel):
    category: str = "notice"         # "notice"(공지사항) | "schedule"(일정)
    title: str
    body: str | None = None
    eventDate: str | None = None     # 일정 날짜 (YYYY-MM-DD)
    pinned: bool = False


class NoticeUpdate(BaseModel):
    """부분 수정 — 보낸 필드만 반영한다."""

    category: str | None = None
    title: str | None = None
    body: str | None = None
    eventDate: str | None = None
    pinned: bool | None = None


class NoticeOut(BaseModel):
    id: int
    category: str
    title: str
    body: str | None = None
    eventDate: str | None = Field(default=None, validation_alias="event_date")
    pinned: bool
    createdAt: datetime | None = Field(default=None, validation_alias="created_at")
    updatedAt: datetime | None = Field(default=None, validation_alias="updated_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DeprioritizedUpdate(BaseModel):
    value: bool


class RoleUpdate(BaseModel):
    role: str  # "member"(일반 부원) | "executive"(임원진) | "admin"(관리자)


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
