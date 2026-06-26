from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: int
    username: str
    name: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    accessToken: str
    user: UserInfo
