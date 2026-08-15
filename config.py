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
    # 예) ADMIN_KAKAO_IDS="1234567890,2345678901"
    admin_kakao_ids: str = ""

    # 스포렉스 레인대관 신청서에 들어가는 동아리 정보.
    # 담당자 실명·연락처는 개인정보이므로 코드에 기본값을 두지 않는다.
    # 반드시 환경변수(CLUB_SIGNER, CLUB_CONTACT)로 주입할 것.
    # 이 저장소는 공개되어 있다 — 실제 값을 여기 적지 말 것.
    club_name: str = "우파루파"
    club_signer: str = ""
    club_contact: str = ""
    rental_hours: str = "2시간"

    class Config:
        env_file = ".env"
        # .env / 환경변수에 여분 값(PYTHON_VERSION 등)이 있어도 무시하고 앱을 기동한다.
        extra = "ignore"


settings = Settings()
