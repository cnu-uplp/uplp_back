from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/uplp"
    jwt_secret_key: str = "change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # Groq (OpenAI 호환) - 우파루파 대화용
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.1-8b-instant"

    # 카카오 로그인
    kakao_rest_api_key: str = ""
    kakao_client_secret: str = ""  # 콘솔에서 켰을 때만 사용

    class Config:
        env_file = ".env"
        # .env / 환경변수에 여분 값(PYTHON_VERSION 등)이 있어도 무시하고 앱을 기동한다.
        extra = "ignore"


settings = Settings()
