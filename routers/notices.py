import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from deps import (
    APPROVAL_APPROVED,
    get_current_staff,
    get_current_user,
    get_current_user_optional,
)
from models import Notice, NoticeComment, User, display_name
from schemas import (
    CommentCreate,
    CommentOut,
    NoticeCreate,
    NoticeOut,
    NoticeUpdate,
)

router = APIRouter(prefix="/api/notices", tags=["notices"])

VALID_CATEGORIES = {"notice", "schedule"}

# 업로드 허용 확장자. 실행 가능한 파일이 올라가 정적 경로로 서빙되는 것을 막는다.
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024   # 5MB — 폰 사진 한 장 기준
COMMENT_MAX = 1000


def _validate(category: str | None, event_date: str | None) -> None:
    if category is not None and category not in VALID_CATEGORIES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "category는 'notice' 또는 'schedule'이어야 합니다.",
        )
    # 일정 날짜는 YYYY-MM-DD 형식만 받는다 (프론트 <input type="date">와 동일)
    if event_date:
        try:
            datetime.strptime(event_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "날짜는 YYYY-MM-DD 형식이어야 합니다."
            )


@router.get("", response_model=list[NoticeOut])
def list_notices(db: Session = Depends(get_db)):
    """공지·일정 전체 조회 — 로그인 없이 누구나 볼 수 있다.

    정렬: 고정(pinned) 먼저 → 일정은 날짜 빠른 순, 공지는 최근 작성 순.
    event_date가 없는 항목(공지)은 뒤로 밀리지 않도록 created_at으로만 비교한다.
    """
    items = db.query(Notice).all()

    def sort_key(n: Notice):
        # created_at은 server_default라 이론상 None일 수 있어 방어한다.
        created = n.created_at or datetime.min
        if n.category == "schedule" and n.event_date:
            # 일정: 날짜 오름차순(다가오는 것 먼저)
            return (0 if n.pinned else 1, 0, n.event_date, "")
        # 공지: 최신 작성 먼저 → created_at 내림차순을 위해 음수 timestamp 사용
        return (0 if n.pinned else 1, 1, "", -created.timestamp())

    return [NoticeOut.model_validate(n) for n in sorted(items, key=sort_key)]


@router.post("", response_model=NoticeOut, status_code=status.HTTP_201_CREATED)
def create_notice(
    payload: NoticeCreate,
    admin: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """공지·일정 등록 — 관리자 전용."""
    title = payload.title.strip()
    if not title:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "제목을 입력해주세요.")
    _validate(payload.category, payload.eventDate)

    notice = Notice(
        category=payload.category,
        title=title,
        body=(payload.body or "").strip() or None,
        event_date=payload.eventDate or None,
        pinned=payload.pinned,
        image_url=payload.imageUrl or None,
        author_id=admin.id,
    )
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return NoticeOut.model_validate(notice)


@router.patch("/{notice_id}", response_model=NoticeOut)
def update_notice(
    notice_id: int,
    payload: NoticeUpdate,
    admin: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """공지·일정 수정 — 관리자 전용. 보낸 필드만 반영한다."""
    notice = db.get(Notice, notice_id)
    if notice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "공지를 찾을 수 없습니다.")
    _validate(payload.category, payload.eventDate)

    if payload.category is not None:
        notice.category = payload.category
    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "제목을 입력해주세요.")
        notice.title = title
    if payload.body is not None:
        notice.body = payload.body.strip() or None
    if payload.eventDate is not None:
        # 빈 문자열은 "날짜 지움"으로 처리
        notice.event_date = payload.eventDate or None
    if payload.pinned is not None:
        notice.pinned = payload.pinned
    if payload.imageUrl is not None:
        # 빈 문자열은 "이미지 제거"로 처리
        notice.image_url = payload.imageUrl or None

    notice.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(notice)
    return NoticeOut.model_validate(notice)


@router.delete("/{notice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notice(
    notice_id: int,
    admin: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """공지·일정 삭제 — 관리자 전용."""
    notice = db.get(Notice, notice_id)
    if notice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "공지를 찾을 수 없습니다.")
    db.delete(notice)
    db.commit()


# ──────────────────────────────────────────────────────────────
#  이미지 업로드
# ──────────────────────────────────────────────────────────────
@router.post("/image", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_staff),
):
    """공지에 붙일 이미지 업로드 — 임원진 이상. 저장 경로를 돌려준다.

    파일은 컨테이너 밖(호스트 볼륨)에 저장한다. 컨테이너를 지우고 다시 만드는 일이
    잦은데 이미지가 이미지 레이어 안에 있으면 그때마다 사라진다.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"이미지 파일만 올릴 수 있습니다 ({', '.join(sorted(ALLOWED_IMAGE_EXT))}).",
        )

    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"이미지는 {MAX_IMAGE_BYTES // (1024 * 1024)}MB 이하만 올릴 수 있습니다.",
        )
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "빈 파일입니다.")

    # 파일명은 서버가 새로 짓는다. 사용자가 준 이름을 쓰면 경로 탈출(../)이나
    # 한글·공백 때문에 URL이 깨진다.
    name = f"{secrets.token_hex(16)}{ext}"
    dest = Path(settings.upload_dir)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / name).write_bytes(data)

    return {"url": f"/uploads/{name}"}


# ──────────────────────────────────────────────────────────────
#  댓글
# ──────────────────────────────────────────────────────────────
def _comment_out(c: NoticeComment, users: dict[int, User]) -> CommentOut:
    out = CommentOut.model_validate(c)
    u = users.get(c.author_id) if c.author_id else None
    out.author = display_name(u) if u else "탈퇴한 회원"
    return out


@router.get("/{notice_id}/comments", response_model=list[CommentOut])
def list_comments(
    notice_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    """댓글 목록 — 오래된 것부터. 로그인 없이도 읽을 수 있다."""
    if db.get(Notice, notice_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "공지를 찾을 수 없습니다.")
    items = (
        db.query(NoticeComment)
        .filter(NoticeComment.notice_id == notice_id)
        .order_by(NoticeComment.created_at, NoticeComment.id)
        .all()
    )
    ids = {c.author_id for c in items if c.author_id}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(ids)).all()} if ids else {}
    return [_comment_out(c, users) for c in items]


@router.post(
    "/{notice_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED
)
def create_comment(
    notice_id: int,
    payload: CommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """댓글 작성 — 승인된 회원. 글은 임원진만 쓰지만 댓글은 부원 누구나 쓴다."""
    if user.approval_status != APPROVAL_APPROVED:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "임원진 승인 후 댓글을 쓸 수 있습니다."
        )
    if db.get(Notice, notice_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "공지를 찾을 수 없습니다.")

    body = payload.body.strip()
    if not body:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "내용을 입력해주세요.")
    if len(body) > COMMENT_MAX:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"댓글은 {COMMENT_MAX}자 이내로 써주세요."
        )

    c = NoticeComment(notice_id=notice_id, author_id=user.id, body=body)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _comment_out(c, {user.id: user})


@router.delete(
    "/{notice_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_comment(
    notice_id: int,
    comment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """댓글 삭제 — 본인 것이거나, 임원진이면 남의 것도 지울 수 있다."""
    c = db.get(NoticeComment, comment_id)
    if c is None or c.notice_id != notice_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "댓글을 찾을 수 없습니다.")
    if c.author_id != user.id and user.role not in ("executive", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "본인 댓글만 지울 수 있습니다.")
    db.delete(c)
    db.commit()
