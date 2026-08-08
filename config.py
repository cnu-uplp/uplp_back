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

    # 관리자 부트스트랩: admin 권한을 줄 카카오 id 목록 (콤마 구분)
    # 예) ADMIN_KAKAO_IDS="5023767808,1234567890"
    admin_kakao_ids: str = ""

    # 스포렉스 레인대관 신청서에 들어가는 동아리 정보 (임원 바뀌면 env로 교체)
    club_name: str = "우파루파"
    club_signer: str = "유진우"
    club_contact: str = "010-3058-7675"
    rental_hours: str = "2시간"

    class Config:
        env_file = ".env"
        # .env / 환경변수에 여분 값(PYTHON_VERSION 등)이 있어도 무시하고 앱을 기동한다.
        extra = "ignore"


settings = Settings()
