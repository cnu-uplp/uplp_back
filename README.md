# uplp_back

충남대 수영동아리 **우파루파(UPLP)** 웹사이트 백엔드 (FastAPI)

프론트엔드는 별도 Next.js 프로젝트(`uplp_front`)입니다.

> ⚠️ **이 저장소는 공개되어 있습니다.**
> 실제 키·비밀번호·회원 개인정보(실명·전화번호·카카오 id)를 코드나 문서에 적지 마세요.
> 전부 환경변수로만 주입합니다. 자세한 API 명세는 Notion(비공개)에서 관리합니다.

## 요구 사항

- Python 3.11+
- PostgreSQL

## 설치

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 환경 변수

프로젝트 루트에 `.env`를 만듭니다. **`.env`는 절대 커밋하지 않습니다.**

| 변수 | 설명 |
|---|---|
| `DATABASE_URL` | PostgreSQL 접속 주소 |
| `JWT_SECRET_KEY` | JWT 서명 키. 충분히 긴 랜덤 문자열 |
| `JWT_ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES` | 기본값 `HS256` / `1440` |
| `KAKAO_REST_API_KEY` | 카카오 개발자 콘솔의 REST API 키 |
| `KAKAO_CLIENT_SECRET` | 콘솔에서 Client Secret을 켠 경우에만 |
| `ADMIN_KAKAO_IDS` | 관리자 권한을 줄 카카오 id 목록 (콤마 구분) |
| `CLUB_NAME` · `CLUB_SIGNER` · `CLUB_CONTACT` · `RENTAL_HOURS` | 레인대관 신청서에 들어가는 동아리 정보 |
| `GROQ_API_KEY` · `GROQ_MODEL` | 마스코트 대화 기능(선택) |

`CLUB_SIGNER`(담당자 실명)와 `CLUB_CONTACT`(연락처)는 **개인정보라 코드에 기본값이 없습니다.**
넣지 않으면 신청서의 해당 칸이 비어서 나옵니다. 배포 환경변수에만 넣으세요.

> `.env`에 여분 값이 있어도 무시하고 기동합니다 (`extra = "ignore"`).

## DB 준비

```bash
psql -d postgres -c "CREATE DATABASE uplp OWNER postgres;"
```

테이블은 서버 시작 시 자동 생성됩니다(`Base.metadata.create_all`).
컬럼이 추가된 경우 `main.py`가 기동 시 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`를 돌리므로
기존 DB를 지우지 않아도 마이그레이션됩니다.

로컬 개발용 관리자 계정이 필요하면 비밀번호를 직접 정해서 만듭니다.

```bash
SEED_ADMIN_PASSWORD='직접-정한-긴-비밀번호' python seed_admin.py
```

**운영 환경에서는 쓰지 마세요.** 운영 관리자는 `ADMIN_KAKAO_IDS`(카카오 로그인)로 지정합니다.

## 실행

```bash
uvicorn main:app --reload --port 8000
```

## 프론트엔드 연동

CORS 허용 출처는 `main.py`에서 관리합니다. 배포 주소가 바뀌면 `allow_origins`를 맞춰 수정하세요.

## 다루는 개인정보

회원가입을 따로 두지 않고 카카오 로그인만 쓰는 것도, 보관 항목을 줄이기 위한 결정입니다.

| 항목 | 용도 | 비고 |
|---|---|---|
| 카카오 id · 닉네임 | 로그인 식별 | |
| 전화번호 | 레인대관 신청서 제출 | 시설 측 요구 항목 |
| 단과대 · 학과 | 동아리 회원 확인 | |

- 신청서(docx)에는 **회원 실명과 전화번호가 들어갑니다.** 생성된 파일을 저장소나 공유 드라이브에 올리지 마세요.
- 신청서 원본 양식에 "개인 신상정보는 대관 신청한 날짜 일주일 후 파기됩니다"라고 적혀 있습니다. 실제 파기 절차는 아직 코드에 없습니다 — 운영 시 수동으로 챙겨야 합니다.

## 데이터 모델

| 테이블 | 설명 |
|---|---|
| `users` | 카카오 회원과 관리자 계정을 함께 담습니다. `role`은 `member`/`admin`, `is_deprioritized`는 후순위 대상 여부 |
| `swim_sessions` | 정기수영 회차. 날짜·시각·위치, 부서별 정원, 후순위 제도 사용 여부, 신청 시작/마감 시각(UTC) |
| `swim_applications` | 신청 내역. `division`, `queue`, `merged`, `applied_at`(선착순 기준 시각) |

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

정기수영이 마감되면 스포렉스 제출용 신청서(원본 HWP 양식)를 `.docx`로 재현해 내려받습니다.
구현은 `routers/swim.py` 의 `roster_docx()` 한 곳에 모여 있습니다.

- 원본 PDF에서 좌표·글자 크기·행 높이·테두리 굵기를 실측해 **A4 3페이지를 1mm 이내로 재현**합니다.
- 자동 기입: 참석자 이름 / 전화번호 / 사용 희망 날짜 / 이용 인원. 참석 확인란은 현장 서명용으로 비웁니다.
- 명단에는 **배정 인원만** 들어갑니다(예비·후순위 대기 제외).
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

전체 명세(경로·요청·응답·권한)는 **Notion의 `API 명세서`** 에서 관리합니다.
`/docs`(Swagger UI)에서도 볼 수 있습니다.

에픽 단위 요약만 적어둡니다.

| 에픽 | 내용 |
|---|---|
| 인증 | 카카오 로그인, 관리자 로그인 |
| 사용자 | 내 정보 조회·수정, 후순위 지정 |
| 정기수영 | 회차 관리(개설·수정·삭제·마감), 신청·취소, 정원 조정, 후순위 병합, 명단 조회, 신청서 다운로드 |
| 기타 | 마스코트 대화 |

### 권한

- 관리자 전용 엔드포인트는 `deps.get_current_admin`으로 검사합니다(→ 403).
  프론트에서 UI를 숨기는 것과 **별개로** 서버에서 다시 막으므로, 개발자 도구로 버튼을 되살려도 통과하지 못합니다.
- **자체 회원가입은 제공하지 않습니다.** 일반 회원은 카카오 로그인만 쓰고,
  관리자 계정은 `seed_admin.py`로 직접 만듭니다.

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
├── seed_admin.py      # 로컬 개발용 관리자 계정 생성
└── routers/
    ├── auth.py        # 로그인 · 카카오 로그인
    ├── users.py       # 내 정보 · 후순위 지정
    ├── swim.py        # 정기수영 전체 + 레인대관 신청서 docx 생성
    └── upalupa.py     # 마스코트 대화
```

## 배포

Docker 런타임으로 배포합니다(`Dockerfile`, `render.yaml`).

- 환경 변수는 호스팅 대시보드에서 직접 넣습니다. `render.yaml`에는 `sync: false`로 두어 git에 올라가지 않게 합니다.
- **git에 푸시한다고 자동 반영되지 않습니다.** 대시보드에서 재배포해야 합니다.

## 카카오 로그인 설정

카카오 개발자 콘솔에서 아래를 맞춰야 합니다.

- **Redirect URI 등록** — 배포 주소와 로컬 주소 각각 `/login/kakao/callback`
- **동의 항목은 콘솔에서만 관리합니다.** 코드에서 `scope`를 넘기지 않습니다.
  콘솔에서 끈 항목을 코드가 요청하면 `KOE205`가 납니다.
- Client Secret을 콘솔에서 켰다면 `KAKAO_CLIENT_SECRET`을 반드시 넣어야 합니다(`KOE010`).

## Third-Party Notices

See [`../../uplp_front/THIRD-PARTY-NOTICES.txt`](../../uplp_front/THIRD-PARTY-NOTICES.txt)
for third-party open-source licenses used by the web client.
