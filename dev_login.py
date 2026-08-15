"""로컬 개발용 로그인 헬퍼.

    python dev_login.py                # 로컬 admin(관리자)으로 토큰 발급
    python dev_login.py 5              # user id 5 로 발급
    python dev_login.py student        # 재학생 테스트 계정
    python dev_login.py alumni         # 졸업생 테스트 계정
    python dev_login.py guest          # 외부인 테스트 계정
    python dev_login.py executive      # 임원진(재학생) 테스트 계정

프론트 로그인 화면은 카카오 버튼만 남아 있고, 로컬에서는 카카오 Redirect URI 등록 없이는
로그인이 안 된다. 이 스크립트는 그 과정을 건너뛰고 붙여넣기용 코드를 출력한다.
소속(membership)별로 화면이 어떻게 갈리는지 바로 바꿔가며 확인할 수 있다.

⚠️ 로컬 전용 — 운영 DB(Render/Lightsail)에는 절대 쓰지 말 것.
"""

import sys

import models  # noqa: F401  (User를 Base.metadata에 등록)
from database import SessionLocal
from models import User
from security import create_access_token

FRONT_ORIGIN = "http://localhost:3000"

# 별칭 → (membership, role, 표시이름). 없으면 만들고, 있으면 그 계정을 재사용한다.
PRESETS = {
    "student": ("student", "member", "테스트재학생"),
    "alumni": ("alumni", "member", "테스트졸업생"),
    "guest": ("guest", "member", "테스트외부인"),
    "executive": ("student", "executive", "테스트임원진"),
}


def pick_user(db, arg: str | None) -> User:
    if arg is None:
        user = db.query(User).filter(User.role == "admin").first()
        if user is None:
            sys.exit("admin 계정이 없습니다. 먼저 `python seed_admin.py` 를 실행하세요.")
        return user

    if arg in PRESETS:
        membership, role, label = PRESETS[arg]
        # 이름으로 찾아 재사용 — 매번 새 계정이 쌓이지 않게 한다.
        user = db.query(User).filter(User.name == label).first()
        if user is None:
            user = User(name=label, nickname=label)
            db.add(user)
        user.membership = membership
        user.role = role
        # 재학생만 연락처·학과가 필요하다 (온보딩 규칙과 동일)
        user.phone_number = "01000000000" if membership == "student" else None
        user.college = None if membership == "guest" else "공과대학"
        user.department = None if membership == "guest" else "컴퓨터공학과"
        db.commit()
        db.refresh(user)
        return user

    if not arg.isdigit():
        sys.exit(f"알 수 없는 인자: {arg!r}  (id 숫자 또는 {', '.join(PRESETS)})")
    user = db.get(User, int(arg))
    if user is None:
        sys.exit(f"user id={arg} 를 찾을 수 없습니다.")
    return user


db = SessionLocal()
try:
    user = pick_user(db, sys.argv[1] if len(sys.argv) > 1 else None)
    token = create_access_token(subject=str(user.id))
    display = user.name or user.nickname or user.username or f"회원{user.id}"

    # localStorage에 심을 user 객체 — 프론트가 인사말·초기 렌더에 쓴다.
    # 실제 권한·소속은 서버가 매 요청마다 다시 검사하므로 이 값은 표시용일 뿐이다.
    payload = (
        "{"
        f'id:{user.id},'
        f'name:"{display}",'
        f'role:"{user.role}",'
        f'membership:"{user.membership}"'
        "}"
    )

    print(f"\n  대상: id={user.id}  {display}")
    print(f"        소속={user.membership}  권한={user.role}  직위={user.position or '-'}")
    print(f"\n  1) 브라우저에서 {FRONT_ORIGIN} 를 연다")
    print("  2) 개발자 도구 > Console 에 아래 한 줄을 붙여넣고 Enter\n")
    print(
        f'localStorage.setItem("accessToken","{token}");'
        f'localStorage.setItem("user",JSON.stringify({payload}));'
        "location.reload()"
    )
    print(f"\n  다른 소속으로 바꿔보려면: python dev_login.py [{' | '.join(PRESETS)}]\n")
finally:
    db.close()
