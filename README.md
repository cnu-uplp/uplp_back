# uplp_back

uplp 프로젝트 백엔드 (FastAPI)

## 요구 사항

- Python 3.12+
- PostgreSQL (로컬에서 실행 중이어야 함)

## 설치

```bash
# 1. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 2. 의존성 설치
pip install -r requirements.txt
```

## 환경 변수

프로젝트 루트에 `.env` 파일을 생성합니다.

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/uplp
JWT_SECRET_KEY=change-this-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

## DB 준비

PostgreSQL이 떠있는 상태에서 `DATABASE_URL`에 지정한 데이터베이스를 미리 생성해야 합니다.

```bash
psql -d postgres -c "CREATE DATABASE uplp OWNER postgres;"
```

테이블은 서버 시작 시 자동으로 생성됩니다 (`main.py`의 `Base.metadata.create_all`).

## 실행

```bash
uvicorn main:app --reload --port 8000
```

서버가 뜨면 `http://localhost:8000`에서 접속할 수 있습니다.

- API 문서(Swagger UI): `http://localhost:8000/docs`

## 프론트엔드 연동

`uplp_front`를 `http://localhost:3000`에서 띄우는 것을 기준으로 CORS가 설정되어 있습니다 (`main.py`). 다른 포트/주소를 쓴다면 `allow_origins` 값을 맞춰서 수정해야 합니다.

## 구현된 API

| 기능 | Method | Path | 비고 |
|---|---|---|---|
| 로그인 | POST | `/api/auth/login` | bcrypt 비밀번호 검증, 성공 시 JWT(accessToken) + 사용자 정보 반환 |

나머지 API(회원가입, 카카오 로그인, 정기수영 신청, 공지사항, 정보 조회/수정)는 Notion API 명세서 기준 미구현 상태입니다.

## 프로젝트 구조

```
.
├── main.py          # FastAPI 앱, CORS, 라우터 등록
├── config.py        # 환경 변수 설정
├── database.py      # SQLAlchemy 엔진/세션
├── models.py         # User 등 DB 모델
├── schemas.py        # Pydantic 요청/응답 스키마
├── security.py        # 비밀번호 해싱, JWT 발급
└── routers/
    └── auth.py        # 인증 관련 라우터
```
