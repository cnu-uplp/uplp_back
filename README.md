# uplp_back

충남대 수영동아리 **우파루파(UPLP)** 웹사이트 백엔드 (FastAPI)

프론트엔드는 별도 Next.js 프로젝트(`uplp_front`)입니다.

- 배포: https://uplp-back.onrender.com (Render)
- API 문서: `/docs` (Swagger UI)
- API 명세서: Notion — `The uplp / API 명세서`

## 요구 사항

- Python 3.11+ (배포 이미지는 3.11-slim)
- PostgreSQL

## 설치

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 환경 변수

프로젝트 루트에 `.env` 파일을 만듭니다.

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/uplp
JWT_SECRET_KEY=change-this-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 카카오 로그인
KAKAO_REST_API_KEY=
KAKAO_CLIENT_SECRET=

# 관리자 부트스트랩 (콤마 구분)
ADMIN_KAKAO_IDS=

# 레인대관 신청서에 들어가는 동아리 정보
CLUB_NAME=우파루파
CLUB_SIGNER=유진우
CLUB_CONTACT=010-0000-0000
RENTAL_HOURS=2시간

# 우파루파 대화 (선택)
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant
```

| 변수 | 설명 |
|---|---|
| `KAKAO_REST_API_KEY` | 카카오 개발자 콘솔의 REST API 키 |
| `KAKAO_CLIENT_SECRET` | 콘솔에서 Client Secret을 **켠 경우에만** 필요. 켜놓고 값을 안 넣으면 `KOE010`이 납니다 |
| `ADMIN_KAKAO_IDS` | 이 카카오 id로 로그인하면 `role=admin`이 부여됩니다 |
| `CLUB_*` · `RENTAL_HOURS` | 레인대관 신청서 자동 생성에 들어가는 값. 임원이 바뀌면 이 값만 교체하면 됩니다 |

> `.env`에 여분 값(`PYTHON_VERSION` 등)이 있어도 무시하고 기동합니다 (`extra = "ignore"`).

## DB 준비

```bash
psql -d postgres -c "CREATE DATABASE uplp OWNER postgres;"
```

테이블은 서버 시작 시 자동 생성됩니다(`Base.metadata.create_all`).
컬럼이 추가된 경우 `main.py`가 기동 시 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`를 돌리므로
기존 DB를 지우지 않아도 마이그레이션됩니다.

로컬 검증용 관리자 계정(`admin` / `admin123`, `role=admin`)이 필요하면:

```bash
python seed_admin.py
```

## 실행

```bash
uvicorn main:app --reload --port 8000
```

## 프론트엔드 연동

CORS는 `main.py`에서 `http://localhost:3000` 과 `https://uplp-front.vercel.app` 를 허용합니다.
다른 주소를 쓴다면 `allow_origins`를 맞춰 수정해야 합니다.

## 데이터 모델

| 테이블 | 설명 |
|---|---|
| `users` | 카카오 회원(`kakao_id`, `nickname`, `phone_number`, `college`, `department`)과 관리자 계정(`username`, `hashed_password`)을 함께 담습니다. `role`은 `member`/`admin`, `is_deprioritized`는 후순위 대상 여부 |
| `swim_sessions` | 정기수영 회차. 모이는 날짜·시각·위치, 훈련부/진도부 정원, 후순위 제도 사용 여부, 신청 시작/마감 시각(UTC) |
| `swim_applications` | 신청 내역. `division`(training/progress), `queue`(normal/late), `merged`(후순위 병합 여부), `applied_at`(선착순 기준 시각) |

## 정기수영 순번 규칙

이 프로젝트에서 가장 주의해야 할 부분입니다.

- **순번은 DB에 저장하지 않습니다.** 조회할 때마다 `applied_at` 기준으로 다시 계산합니다.
  덕분에 취소·정원 변경이 생겨도 예비번호가 자동으로 당겨집니다.
- 정렬 순서는 항상 `일반 신청자 → 병합된 후순위 신청자 → 미병합 후순위 대기` 입니다.
  후순위 회원이 아무리 먼저 신청해도 일반 신청자를 앞지르지 않습니다.
- 후순위 대기는 관리자가 **후순위 병합**을 눌러야(`merged=True`) 본 명단 뒤에 붙습니다.
- 정원 안에 든 인원이 `assigned`, 넘친 인원이 `reserve`(예비번호)입니다.

```python
normal       = [a for a in apps if a.queue == "normal"]
merged_late  = [a for a in apps if a.queue == "late" and a.merged]
pending_late = [a for a in apps if a.queue == "late" and not a.merged]
ordered = sorted(normal, key=key) + sorted(merged_late, key=key)
assigned, reserve = ordered[:cap], ordered[cap:]
```

## 레인대관 신청서 생성

`GET /api/swim/sessions/{id}/roster.docx` 는 스포렉스에 제출하는
**CNU SPOREX Swimming 레인대관 신청서**(원본 HWP 양식)를 `.docx`로 재현해 내려줍니다.
구현은 `routers/swim.py` 의 `roster_docx()` 한 곳에 모여 있습니다.

- 원본 PDF에서 좌표·글자 크기·행 높이·테두리 굵기를 실측해 **A4 3페이지를 1mm 이내로 재현**합니다.
- 자동 기입: 참석자 이름 / 전화번호 / 사용 희망 날짜 / 이용 인원. 참석 확인란은 현장 서명용으로 비웁니다.
- 명단에는 **배정 인원만** 들어갑니다(예비·후순위 대기 제외). 훈련부·진도부는 한 표로 합칩니다.
- **마감된 회차**만, **관리자만** 받을 수 있습니다.

### 수정할 때 주의할 점

원본 양식을 손보다 문서가 깨진 적이 여러 번 있어서, 아래는 반드시 지켜야 합니다.

1. **줄간격은 고정(EXACTLY)으로 둡니다.** 원본은 HWP라 줄간격이 글자크기의 160%인데
   워드의 맑은 고딕 기본값은 174%입니다. 그냥 두면 한 줄마다 밀려서 마지막 표가 다음 장으로 넘어갑니다.
2. **OOXML 자식 요소는 순서까지 스키마를 따라야 합니다.** 순서가 틀리면 워드가
   "파일을 열 때 오류"를 내며 아예 열지 않습니다. 저장 직전에 `tblPr`/`tcPr`/`trPr`을 자동 정렬합니다.
3. **`w:fldChar`/`w:instrText`는 반드시 `w:r`(run) 안에** 넣어야 합니다.
4. `doc.add_section()`은 앞 페이지 끝에 **보이지 않는 빈 문단**을 남깁니다.
   높이를 눌러두지 않으면 1페이지가 넘칩니다.
5. 표 왼쪽 테두리 위치는 `본문여백 + tblInd − 셀좌여백` 입니다. `style_table(left_mm=...)`이 역산합니다.

## API

| 에픽 | 기능 | Method | Path | JWT | 비고 |
|---|---|---|---|---|---|
| 인증 | 로그인 | POST | `/api/auth/login` | 불필요 | 관리자 계정용. bcrypt 검증 |
| 인증 | 카카오 로그인 | POST | `/api/auth/kakao` | 불필요 | 인가 코드 → 토큰 교환 → JWT 발급 |
| 사용자 | 내 정보 조회 | GET | `/api/users/me` | 필요 | |
| 사용자 | 내 정보 수정 | PATCH | `/api/users/me` | 필요 | 전화번호(하이픈 없이)·단과대·학과 |
| 사용자 | 후순위 지정/해제 | PATCH | `/api/users/{id}/deprioritized` | 필요 | 관리자 전용 |
| 정기수영 | 회차 목록 | GET | `/api/swim/sessions` | 선택 | 로그인 시 내 신청 상태 포함 |
| 정기수영 | 회차 개설 | POST | `/api/swim/sessions` | 필요 | 관리자 전용 |
| 정기수영 | 신청 | POST | `/api/swim/sessions/{id}/apply` | 필요 | 신청 기간에만 |
| 정기수영 | 신청 취소 | DELETE | `/api/swim/sessions/{id}/apply` | 필요 | 취소 즉시 예비 인원이 당겨짐 |
| 정기수영 | 회차 수정 | PATCH | `/api/swim/sessions/{id}` | 필요 | 관리자 전용, **오픈 전까지만** |
| 정기수영 | 정원 조정 | PATCH | `/api/swim/sessions/{id}/capacity` | 필요 | 관리자 전용, 신청 중에도 가능 |
| 정기수영 | 후순위 병합 | POST | `/api/swim/sessions/{id}/merge` | 필요 | 관리자 전용 |
| 정기수영 | 마감 | POST | `/api/swim/sessions/{id}/close` | 필요 | 관리자 전용 |
| 정기수영 | 회차 삭제 | DELETE | `/api/swim/sessions/{id}` | 필요 | 관리자 전용 |
| 정기수영 | 명단 조회 | GET | `/api/swim/sessions/{id}/roster` | 불필요 | 전체 공개 (대시보드) |
| 정기수영 | 레인대관 신청서 | GET | `/api/swim/sessions/{id}/roster.docx` | 필요 | 관리자 전용, **마감 후에만** |
| 기타 | 우파루파 대화 | POST | `/api/upalupa/chat` | 불필요 | Groq(OpenAI 호환) |

권한은 프론트에서 UI를 숨기는 것과 별개로 서버에서 다시 검사합니다(`deps.get_current_admin` → 403).
개발자 도구로 버튼을 되살려도 통과하지 못합니다.

> **자체 회원가입(`POST /api/auth/join`)은 제공하지 않습니다.**
> 일반 회원은 카카오 로그인만 쓰고, 관리자 계정은 `seed_admin.py`로 직접 만듭니다.
> 개인정보를 최소한만 보관하기로 한 결정에 따라, 누구나 계정을 만들 수 있는 경로를 열어두지 않습니다.

## 프로젝트 구조

```
.
├── main.py            # FastAPI 앱, CORS, 라우터 등록, 기동 시 컬럼 마이그레이션
├── config.py          # 환경 변수 (pydantic-settings)
├── database.py        # SQLAlchemy 엔진/세션
├── models.py          # User / SwimSession / SwimApplication
├── schemas.py         # Pydantic 요청·응답 스키마
├── security.py        # 비밀번호 해싱, JWT 발급
├── deps.py            # get_current_user / get_current_user_optional / get_current_admin
├── seed_admin.py      # 로컬 검증용 관리자 계정 생성
└── routers/
    ├── auth.py        # 회원가입 · 로그인 · 카카오 로그인
    ├── users.py       # 내 정보 · 후순위 지정
    ├── swim.py        # 정기수영 전체 + 레인대관 신청서 docx 생성
    └── upalupa.py     # 우파루파 대화
```

## 배포 (Render)

Docker 런타임으로 배포합니다(`Dockerfile`, `render.yaml`).

```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

- 환경 변수는 Render 대시보드에서 직접 넣습니다. `render.yaml`에는 `sync: false`로 두어 git에 올라가지 않게 합니다.
- **git에 푸시한다고 자동 반영되지 않습니다.** 대시보드에서 재배포해야 합니다.
  배포가 최신인지 확인하려면 `https://uplp-back.onrender.com/openapi.json` 의 경로 목록을 보면 됩니다.

## 카카오 로그인 설정

카카오 개발자 콘솔에서 아래를 맞춰야 합니다.

- **Redirect URI 등록** — `https://uplp-front.vercel.app/login/kakao/callback`
  (로컬 테스트 시 `http://localhost:3000/login/kakao/callback`도 함께)
- **동의 항목은 콘솔에서만 관리합니다.** 코드에서 `scope`를 넘기지 않습니다.
  콘솔에서 끈 항목을 코드가 요청하면 `KOE205`가 납니다.
- Client Secret을 콘솔에서 켰다면 `KAKAO_CLIENT_SECRET`을 반드시 넣어야 합니다(`KOE010`).
