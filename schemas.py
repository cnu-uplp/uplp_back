from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class KakaoLoginRequest(BaseModel):
    code: str
    redirectUri: str


class ProfileUpdateRequest(BaseModel):
    phoneNumber: str
    college: str | None = None      # 단과대
    department: str | None = None    # 학과


class DeprioritizedUpdate(BaseModel):
    value: bool


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
