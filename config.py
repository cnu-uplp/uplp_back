from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/uplp"
    jwt_secret_key: str = "change-this-secret"
    jwt_algorithm: str = "HS256"
    # 로그인 유지 시간(분). 짧게 두는 대신, 만료되면 프론트가
    # "인증이 만료되었습니다. 다시 로그인해주세요." 를 띄우고 로그인 화면으로 보낸다.
    # 대관 명단에 실명·연락처가 들어가는 서비스라 세션을 오래 열어두지 않는다.
    access_token_expire_minutes: int = 30

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

    # 가입 승인제 사용 여부.
    #   True(기본)  임원진이 승인해야 정기수영 신청·명단 실명 조회가 열린다
    #   False       가입 정보를 넣는 즉시 승인 처리 (시범 운영·데모용)
    # ⚠️ 데모가 끝나면 REQUIRE_APPROVAL 환경변수를 지워 기본값(True)으로 되돌릴 것.
    #    켜두지 않으면 아무나 가입해서 바로 신청하고 명단의 실명까지 볼 수 있다.
    require_approval: bool = True

    # 공지 첨부 이미지 저장 위치 (컨테이너 안 경로).
    # 운영에서는 호스트 볼륨을 여기에 붙인다 — 컨테이너를 지우고 다시 만들어도
    # 이미지가 남아야 하기 때문이다.
    #   docker run -v /var/uplp/uploads:/app/uploads ...
    upload_dir: str = "uploads"

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
