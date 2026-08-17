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

> venv를 만든 뒤 폴더를 옮기면 `venv/bin/uvicorn` 같은 스크립트의 첫 줄(shebang)이 옛 경로를
> 가리켜 `bad interpreter`가 납니다. `./venv/bin/python -m uvicorn ...` 처럼 모듈로 실행하면
> 우회되고, 깔끔히 고치려면 venv를 다시 만드세요.

## 환경 변수

프로젝트 루트에 `.env`를 만듭니다. **`.env`는 절대 커밋하지 않습니다.**

| 변수 | 설명 |
|---|---|
| `DATABASE_URL` | PostgreSQL 접속 주소 |
| `JWT_SECRET_KEY` | JWT 서명 키. 충분히 긴 랜덤 문자열 (`openssl rand -hex 32`) |
| `JWT_ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES` | 기본값 `HS256` / `1440` |
| `KAKAO_REST_API_KEY` | 카카오 개발자 콘솔의 REST API 키 |
| `KAKAO_CLIENT_SECRET` | 콘솔에서 Client Secret을 켠 경우에만 |
| `ADMIN_KAKAO_IDS` | 관리자 권한을 줄 카카오 id 목록 (콤마 구분) |
| `REQUIRE_APPROVAL` | 가입 승인제 사용 여부. 기본 `true` |
| `UPLOAD_DIR` | 공지 첨부 이미지 저장 경로. 기본 `uploads` |
| `CLUB_NAME` · `CLUB_SIGNER` · `CLUB_CONTACT` · `RENTAL_HOURS` | 레인대관 신청서에 들어가는 동아리 정보 |
| `GROQ_API_KEY` · `GROQ_MODEL` | 마스코트 대화 기능(선택) |

`CLUB_SIGNER`(담당자 실명)와 `CLUB_CONTACT`(연락처)는 **개인정보라 코드에 기본값이 없습니다.**
넣지 않으면 신청서의 해당 칸이 비어서 나옵니다. 배포 환경변수에만 넣으세요.

> ⚠️ **`config.py`는 값이 없어도 기본값으로 조용히 기동합니다.** `.env`가 로드되지 않으면
> `JWT_SECRET_KEY`가 공개된 기본값(`change-this-secret`)이 되어 **누구나 관리자 토큰을 위조**할 수
> 있고, `DATABASE_URL`도 로컬 기본값으로 붙어 "데이터가 사라진 것처럼" 보입니다.
> 배포 직후 반드시 `docker exec <컨테이너> printenv` 로 실제 주입 여부를 확인하세요.

> `.env`에 여분 값이 있어도 무시하고 기동합니다 (`extra = "ignore"`).

## DB 준비

`CREATE USER`와 `CREATE DATABASE`는 **한 문장에 묶으면 실패합니다**
(`CREATE DATABASE cannot run inside a transaction block`). `-c`를 나눠 주세요.

```bash
psql -c "CREATE USER uplp WITH PASSWORD '비밀번호';" -c "CREATE DATABASE uplp OWNER uplp;"
```

테이블은 서버 시작 시 자동 생성됩니다(`Base.metadata.create_all`).
컬럼이 추가된 경우 `main.py`가 기동 시 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`를 돌리므로
기존 DB를 지우지 않아도 마이그레이션됩니다.

## 실행

```bash
./venv/bin/python -m uvicorn main:app --reload --port 8000
```

### 로컬 로그인 (카카오 우회)

프론트는 카카오 로그인만 있어서 로컬에서는 로그인이 번거롭습니다. `dev_login.py`가 JWT를
직접 발급해 브라우저에 심을 코드를 출력합니다.

```bash
./venv/bin/python dev_login.py admin       # 관리자 (역할 변경까지 가능)
./venv/bin/python dev_login.py executive   # 임원진
./venv/bin/python dev_login.py student     # 재학생
./venv/bin/python dev_login.py alumni      # 졸업생
./venv/bin/python dev_login.py guest       # 외부인
```

출력된 `localStorage.setItem(...)` 한 줄을 브라우저 콘솔에 붙여넣으면 됩니다.
프리셋 계정은 학번·승인 상태까지 채워집니다 — 안 채우면 온보딩 모달에 막혀 화면을 못 봅니다.

**운영 DB에는 절대 쓰지 마세요.** 운영 관리자는 `ADMIN_KAKAO_IDS`로 지정합니다.

> 아이디/비밀번호 로그인(`POST /api/auth/login`)은 **2026-08-16에 제거했습니다.**
> 실제로 쓰지 않는데 시도 횟수 제한이 없어 대입 공격 표면만 남아 있었습니다.
> 로그인 경로는 카카오 하나뿐이고, 비밀번호는 아예 다루지 않습니다.

## 권한 체계 — 서로 다른 세 축

한 사용자가 세 값을 동시에 갖습니다. 서로 독립적이라 헷갈리기 쉽습니다.

| 축 | 값 | 의미 |
|---|---|---|
| `role` | `member` / `executive` / `admin` | **시스템 권한.** 임원진은 운영 기능, 관리자는 거기에 역할 변경까지 |
| `membership` | `student` / `alumni` / `guest` | **소속.** 정기수영 신청은 `student`만 (대관 명단에 연락처가 필요) |
| `approval_status` | `pending` / `approved` / `rejected` | **가입 승인.** 승인 전에는 둘러보기만 |
| `position` | `"회장"` 등 자유 입력 | **표시 전용.** 권한과 무관 — 졸업생 동문회장처럼 role은 member여도 직위는 가능 |

- 임원진·관리자는 **재학생만** 될 수 있습니다.
- 승인 검사는 **역할과 무관합니다.** 관리자도 승인을 받아야 신청할 수 있고,
  **자기 자신은 승인할 수 없습니다** — 임원진이 한 명뿐이면 아무도 자신을 승인해줄 수
  없으니, 다른 사람을 임원진으로 올려 승인받는 순서를 밟아야 합니다.

### 승인제 끄기 (시범 운영·데모)

```
REQUIRE_APPROVAL=false
```

가입 정보를 넣는 즉시 `approved`가 되고, 이미 대기 중이던 회원도 **재로그인만 하면** 풀립니다.
`apply()`·`roster()` 같은 검사는 손대지 않고 **승인 상태 자체를 바꿔주는 방식**이라 나머지
로직은 평소와 똑같이 동작합니다.

> ⚠️ 시범 운영이 끝나면 이 줄을 지워 기본값(`true`)으로 되돌리세요.
> 끄고 두면 아무나 가입해 바로 신청하고 명단의 실명까지 볼 수 있습니다.
> **`docker restart`로는 환경변수가 다시 읽히지 않습니다** — 컨테이너를 재생성해야 합니다.

## 다루는 개인정보

회원가입을 따로 두지 않고 카카오 로그인만 쓰는 것도, 보관 항목을 줄이기 위한 결정입니다.

| 항목 | 용도 | 비고 |
|---|---|---|
| 카카오 id · 닉네임 | 로그인 식별 | |
| 실명 · 학번(뒤 2자리) | 명단 표시, 동명이인 구분 | 전체 학번은 받지 않음 |
| 전화번호 | 레인대관 신청서 제출 | **재학생만** — 졸업생은 신청 불가라 수집하지 않음 |
| 단과대 · 학과 | 동아리 회원 확인 | |

- 명단의 실명은 **승인된 재학생·졸업생에게만** 보입니다. 외부인·비로그인·미승인에게는 `***`.
- 신청서(docx)에는 **회원 실명과 전화번호가 들어갑니다.** 생성된 파일을 저장소나 공유 드라이브에 올리지 마세요.
- 가입을 **거절**하면 수집한 연락처·학과·학번을 지웁니다. 계정은 남겨 재신청이 가능하게 둡니다.
- 신청서 원본 양식에 "개인 신상정보는 대관 신청한 날짜 일주일 후 파기됩니다"라고 적혀 있습니다.
  실제 파기 절차는 아직 코드에 없습니다 — 운영 시 수동으로 챙겨야 합니다.

## 데이터 모델

| 테이블 | 설명 |
|---|---|
| `users` | 카카오 회원. `role`·`membership`·`approval_status`·`position` 네 값과 `admission_year`, `is_deprioritized`(후순위 대상) |
| `swim_sessions` | 정기수영 회차. 날짜·시각·위치, 부서별 정원, 후순위 제도 사용 여부, 신청 시작/마감 시각(UTC) |
| `swim_applications` | 신청 내역. `division`, `queue`, `merged`, `applied_at`(선착순 기준 시각) |
| `notices` | 공지·일정. `category`, `pinned`, `image_url`(첨부 이미지) |
| `notice_comments` | 공지 댓글. 공지 삭제 시 CASCADE로 함께 삭제 |
| `content_sections` | 홈·소개 페이지에서 임원진이 웹으로 고치는 본문. `page`(`home`/`about`/`info`), 마크다운 `body`, `width`, `visible` |

`display_name(user)`는 화면용 이름을 만듭니다 — `김철수 21`, 졸업생은 `김철수 21 OB`.
**신청서(docx)에는 쓰지 않습니다.** 스포렉스에 내는 공문서라 실명만 들어가야 합니다.

## 정기수영 순번 규칙

이 프로젝트에서 가장 주의해야 할 부분입니다.

- **순번은 DB에 저장하지 않습니다.** 조회할 때마다 `applied_at` 기준으로 다시 계산합니다.
  덕분에 취소·정원 변경이 생겨도 예비번호가 자동으로 당겨지고, **동시 신청에서 카운터가
  틀어지는 경합이 구조적으로 없습니다.**
- 정렬 키는 `(applied_at, id)`입니다. 같은 순간에 들어와도 순서가 흔들리지 않습니다.
- 정렬 순서는 항상 `일반 신청자 → 병합된 후순위 신청자 → 미병합 후순위 대기` 입니다.
  후순위 회원이 아무리 먼저 신청해도 일반 신청자를 앞지르지 않습니다.
- 후순위 대기는 관리자가 **후순위 병합**을 눌러야(`merged=True`) 본 명단 뒤에 붙습니다.
- 정원 안에 든 인원이 `assigned`, 넘친 인원이 `reserve`(예비번호)입니다.
- 중복 신청은 `uq_swim_app_session_user` 제약이 최종 방어선입니다. 조회와 INSERT 사이는
  원자적이지 않아 더블클릭이면 둘 다 통과하는데, `IntegrityError`를 잡아 **409**로 돌려줍니다.
  (그대로 두면 500이 나가서 "실패한 줄 알고 또 누르는" 사고가 납니다.)

```python
normal       = [a for a in apps if a.queue == "normal"]
merged_late  = [a for a in apps if a.queue == "late" and a.merged]
pending_late = [a for a in apps if a.queue == "late" and not a.merged]
ordered = sorted(normal, key=key) + sorted(merged_late, key=key)
assigned, reserve = ordered[:cap], ordered[cap:]
```

### 동시 신청 부하 (로컬 측정, 2026-08-15)

| 동시 신청 | 결과 | 소요 |
|---|---|---|
| 40명 | 전원 성공 | 189ms |
| 100명 | 전원 성공 | 369ms |
| 150명 | 전원 성공 | 527ms |
| 200명 | 73 성공 / 127 실패 | 30초 타임아웃 |

한계는 성능이 아니라 **DB 커넥션 풀**입니다. 초과분은
`QueuePool limit of size 20 overflow 10 reached` 로 30초 대기 후 500이 납니다.
더 필요하면 `database.py`의 `pool_size`를 올리되 PostgreSQL `max_connections`(기본 100)
안에서 조정하세요.

## 공지 이미지 업로드

- `POST /api/notices/image` — 임원진 이상. 저장 경로(`/uploads/<랜덤>.jpg`)를 돌려줍니다.
- 허용 확장자: `jpg` `jpeg` `png` `gif` `webp` `heic` `heif`, **5MB 이하**.
- 파일명은 서버가 새로 짓습니다. 사용자가 준 이름을 쓰면 경로 탈출(`../`)이나 한글·공백으로 URL이 깨집니다.
- FastAPI가 `/uploads`를 직접 서빙하므로 **nginx에 별도 location을 만들 필요가 없습니다.**

> ⚠️ **nginx `client_max_body_size`가 기본 1MB입니다.** 폰 사진은 2~5MB라 요청이
> 앱에 닿기도 전에 **413**으로 잘립니다. 앱의 5MB 제한은 실행될 기회조차 없습니다.
> 서버 설정에 `client_max_body_size 10M;`을 넣어야 합니다.

> ⚠️ 이미지는 **호스트 볼륨**에 저장해야 합니다. 컨테이너 안에 두면 재생성할 때마다 사라집니다.
> `docker run -v /var/uplp/uploads:/app/uploads ...`

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
| 인증 | 카카오 로그인 (유일) |
| 사용자 | 내 정보 조회·수정, 목록, 가입 승인·거절, 소속·역할·직위 변경, 후순위 지정, 승인 대기 수 |
| 정기수영 | 회차 관리(개설·수정·삭제·마감), 신청·취소, 정원 조정, 후순위 병합, 명단 조회, 신청서 다운로드 |
| 공지 | 공지·일정 CRUD, 댓글 CRUD, 이미지 업로드 |
| 콘텐츠 | 홈·소개 섹션 CRUD·순서 변경, 동아리 기본 정보 |
| 기타 | 마스코트 대화 |

### 권한

- 임원진 전용은 `deps.get_current_staff`, 관리자 전용은 `deps.get_current_admin`으로 검사합니다(→ 403).
  프론트에서 UI를 숨기는 것과 **별개로** 서버에서 다시 막으므로, 개발자 도구로 버튼을 되살려도 통과하지 못합니다.
- 관리자만 할 수 있는 것은 **역할 변경 하나**입니다. 나머지 운영 기능은 임원진도 됩니다.
- 공지 **글**은 임원진만 쓰지만 **댓글**은 승인된 회원 누구나 씁니다.
- **자체 회원가입도, 아이디/비밀번호 로그인도 없습니다.** 카카오 로그인 하나뿐입니다.

## 프로젝트 구조

```
.
├── main.py            # FastAPI 앱, CORS, 라우터 등록, 기동 시 컬럼 마이그레이션, /uploads 정적 서빙
├── config.py          # 환경 변수 (pydantic-settings)
├── database.py        # SQLAlchemy 엔진/세션 (커넥션 풀 20+10, pool_pre_ping)
├── models.py          # User / SwimSession / SwimApplication / Notice / NoticeComment / ContentSection
├── schemas.py         # Pydantic 요청·응답 스키마
├── security.py        # 비밀번호 해싱, JWT 발급
├── deps.py            # 현재 사용자 · 임원진/관리자 검사 · 소속·승인 상수
├── dev_login.py       # 로컬 개발용 토큰 발급 (소속별 프리셋)
└── routers/
    ├── auth.py        # 카카오 로그인 (유일한 로그인 경로)
    ├── users.py       # 내 정보 · 승인 · 소속 · 역할 · 직위 · 후순위
    ├── swim.py        # 정기수영 전체 + 레인대관 신청서 docx 생성
    ├── notices.py     # 공지·일정 + 댓글 + 이미지 업로드
    ├── content.py     # 홈·소개 편집 섹션, 동아리 기본 정보
    └── upalupa.py     # 마스코트 대화
```

## 배포 (AWS Lightsail)

Render에서 옮겨왔습니다. 무료 PostgreSQL이 30일이면 만료·삭제되고, 15분 유휴 후 cold start가
최대 50초라 정각 티케팅에 치명적이었기 때문입니다.

```
프론트  Vercel                        무료
백엔드  Lightsail 서울 1GB ($7/월)    Ubuntu 22.04
도메인  DuckDNS (무료 서브도메인)
인증서  Let's Encrypt (certbot, 자동 갱신)
DB      호스트에 PostgreSQL 직접 설치  ← 컨테이너 밖이라 컨테이너를 지워도 유지
앱      Docker + --restart=always     nginx가 127.0.0.1:8000 으로 프록시
```

### 배포 절차

```bash
cd ~/uplp_back && git pull && sudo docker build -t uplp-back . \
  && sudo docker rm -f uplp \
  && sudo docker run -d --name uplp --restart=always \
     --env-file /etc/uplp/.env \
     -v /var/uplp/uploads:/app/uploads \
     -p 127.0.0.1:8000:10000 uplp-back
```

| 바꾼 것 | 필요한 조치 |
|---|---|
| 코드 | `git pull` + `docker build` + 컨테이너 재생성 |
| `.env` 값 | **컨테이너 재생성** (`docker restart`는 환경변수를 다시 읽지 않습니다) |
| nginx 설정 | `sudo nginx -t && sudo systemctl reload nginx` (앱 무관, 무중단) |

### 서버 설정 메모

- **환경변수는 `/etc/uplp/.env` (chmod 600) 하나가 원본입니다.** 인스턴스를 날리면 같이
  사라지므로 따로 보관해 두세요.
- **스왑 2GB** — docx 생성 시 lxml이 메모리를 밀어올립니다.
- **백업 두 겹** — `pg_dump` 크론(03:30 KST, `/etc/cron.d/uplp-backup`, 14일 보관) +
  Lightsail 자동 스냅샷(04:00 KST). 크론은 서버 디스크에 저장되므로 인스턴스가 통째로
  날아가는 경우는 스냅샷이 담당합니다. **이미지(`/var/uplp/uploads`)는 pg_dump에 안 들어갑니다.**
- **cron은 서버 시간(UTC)을 씁니다.** `0 4 * * *`는 한국시각 13:00입니다. 9시간 빼세요.
- **서버 시간대는 UTC로 둡니다.** `swim.py`의 `_now()`가 `datetime.utcnow()`라 KST로 바꾸면
  티케팅 오픈 시각이 9시간 어긋납니다.
- 방화벽은 22·80·443만. **5432는 열지 마세요** — DB는 같은 인스턴스라 localhost로만 붙습니다.
- 컨테이너에서 호스트 DB로 붙을 때는 `localhost`가 아니라 **`172.17.0.1`**(Docker 브리지)입니다.

### 문제가 생기면

```bash
sudo docker logs uplp --tail 50
```

로그인만 안 되는 것처럼 보여도 **DB 문제일 수 있습니다.** 카카오 토큰 교환은 DB를 안 거쳐서
정상으로 보이고, 그다음 사용자 생성 단계에서 죽기 때문입니다. DB를 타는 엔드포인트로 1초 만에
가려집니다.

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://<도메인>/api/notices
```

## 카카오 로그인 설정

카카오 개발자 콘솔에서 아래를 맞춰야 합니다.

- **Redirect URI 등록** — 배포 주소와 로컬 주소 각각 `/login/kakao/callback`
- **동의 항목은 콘솔에서만 관리합니다.** 코드에서 `scope`를 넘기지 않습니다.
  콘솔에서 끈 항목을 코드가 요청하면 `KOE205`가 납니다.
- Client Secret을 콘솔에서 켰다면 `KAKAO_CLIENT_SECRET`을 반드시 넣어야 합니다(`KOE010`).

> **백엔드 주소가 바뀌어도 카카오 설정은 건드릴 필요가 없습니다.** 프론트가
> `window.location.origin`으로 redirect URI를 만들어 보내므로 카카오는 **프론트 주소만** 봅니다.
> CORS도 같은 이유로 백엔드 주소를 넣을 필요가 없습니다.

## Third-Party Notices

See [`../../uplp_front/THIRD-PARTY-NOTICES.txt`](../../uplp_front/THIRD-PARTY-NOTICES.txt)
for third-party open-source licenses used by the web client.
