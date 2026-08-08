from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_staff
from models import Notice, User
from schemas import NoticeCreate, NoticeOut, NoticeUpdate

router = APIRouter(prefix="/api/notices", tags=["notices"])

VALID_CATEGORIES = {"notice", "schedule"}


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
