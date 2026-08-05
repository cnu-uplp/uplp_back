from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class JoinRequest(BaseModel):
    name: str
    username: str
    password: str


class KakaoLoginRequest(BaseModel):
    code: str
    redirectUri: str


class PhoneUpdateRequest(BaseModel):
    phoneNumber: str


class UserInfo(BaseModel):
    id: int
    nickname: str | None = None
    email: str | None = None
    # ORM 속성은 phone_number(snake), 응답은 phoneNumber(camel)로 매핑
    phoneNumber: str | None = Field(default=None, alias="phone_number")
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
