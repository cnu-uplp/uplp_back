"""로컬 개발용 관리자 로그인 헬퍼.

    python dev_login.py            # 로컬 admin(role=admin)으로 토큰 발급
    python dev_login.py 5          # 특정 user id로 토큰 발급 (일반 회원 화면 확인용)

프론트 로그인 화면은 카카오 버튼만 남아 있어서, 로컬에서 관리자 화면을 보려면
토큰을 직접 브라우저에 심어야 한다. 이 스크립트는 그 붙여넣기용 코드를 출력한다.

⚠️ 로컬 전용 — 운영 DB(Render)에는 절대 쓰지 말 것.
   운영 관리자는 ADMIN_KAKAO_IDS(카카오 id)로 지정한다.
"""

import sys

import models  # noqa: F401  (User를 Base.metadata에 등록)
from database import SessionLocal
from models import User
from security import create_access_token

FRONT_ORIGIN = "http://localhost:3000"

db = SessionLocal()
try:
    if len(sys.argv) > 1:
        user = db.get(User, int(sys.argv[1]))
        if user is None:
            sys.exit(f"user id={sys.argv[1]} 를 찾을 수 없습니다.")
    else:
        user = db.query(User).filter(User.role == "admin").first()
        if user is None:
            sys.exit("admin 계정이 없습니다. 먼저 `python seed_admin.py` 를 실행하세요.")

    token = create_access_token(subject=str(user.id))
    # localStorage에 심을 user 객체 — 프론트가 인사말·초기 렌더에 쓴다.
    # role은 화면 표시용일 뿐이고, 실제 권한은 서버가 매 요청마다 다시 검사한다.
    display = user.name or user.nickname or user.username or f"회원{user.id}"
    payload = (
        "{"
        f'id:{user.id},'
        f'name:"{display}",'
        f'role:"{user.role}"'
        "}"
    )

    print(f"\n  대상: id={user.id}  {display}  (role={user.role})")
    print(f"\n  1) 브라우저에서 {FRONT_ORIGIN} 를 연다")
    print("  2) 개발자 도구 > Console 에 아래 한 줄을 붙여넣고 Enter\n")
    print(
        f'localStorage.setItem("accessToken","{token}");'
        f'localStorage.setItem("user",JSON.stringify({payload}));'
        "location.reload()"
    )
    print("\n  (로그아웃하려면 우측 상단 로그아웃 버튼)\n")
finally:
    db.close()
