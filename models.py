from sqlalchemy import BigInteger, Column, DateTime, Integer, String, func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # 카카오 로그인
    kakao_id = Column(BigInteger, unique=True, index=True, nullable=True)
    nickname = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)

    # 레거시 아이디/비밀번호 로그인 (카카오 유저는 값이 없음)
    username = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
