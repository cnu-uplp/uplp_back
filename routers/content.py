from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_staff
from models import ContentSection, User
from schemas import (
    ContentReorder,
    ContentSectionCreate,
    ContentSectionOut,
    ContentSectionUpdate,
)

router = APIRouter(prefix="/api/content", tags=["content"])

# 섹션을 붙일 수 있는 페이지. 임의 문자열을 허용하면 오타로 만든 섹션이
# 어느 화면에도 안 나오면서 DB에만 쌓인다.
#   home  / about  — 마크다운 본문 섹션
#   info          — 동아리 기본 정보(항목: 값). 홈 히어로와 소개 페이지가 같은 목록을
#                   읽는다. 활동 시간을 한 번만 고치면 두 화면이 같이 바뀐다.
VALID_PAGES = ("home", "about", "info")

# 6칸 그리드에서 차지하는 칸 수. 픽셀 자유 배치 대신 칸 단위로만 고르게 해서
# 어떤 화면 폭에서도 레이아웃이 성립하게 한다. half 4개 = 2x2.
VALID_WIDTHS = ("full", "half", "third")

BODY_MAX = 20000  # 마크다운 본문 상한 (한 섹션이 페이지를 통째로 먹지 않게)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _check_page(page: str) -> None:
    if page not in VALID_PAGES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"page는 {', '.join(VALID_PAGES)} 중 하나여야 합니다.",
        )


def _check_width(width: str) -> None:
    if width not in VALID_WIDTHS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"width는 {', '.join(VALID_WIDTHS)} 중 하나여야 합니다.",
        )


def _check_body(body: str) -> None:
    if len(body) > BODY_MAX:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"본문은 {BODY_MAX}자 이내로 작성해주세요."
        )


@router.get("/{page}", response_model=list[ContentSectionOut])
def list_sections(
    page: str,
    db: Session = Depends(get_db),
):
    """페이지의 섹션 목록 — 로그인 없이 누구나 조회.

    숨김(visible=False) 섹션도 내려보낸다. 임원진 편집 화면에서 다시 켤 수 있어야 하고,
    일반 방문자에게 감추는 것은 프론트가 렌더 단계에서 처리한다.
    (숨김 섹션은 '준비 중인 안내'라 비밀이 아니다 — 감출 목적이면 삭제한다)
    """
    _check_page(page)
    items = (
        db.query(ContentSection)
        .filter(ContentSection.page == page)
        .order_by(ContentSection.sort_order, ContentSection.id)
        .all()
    )
    return [ContentSectionOut.model_validate(s) for s in items]


@router.post("", response_model=ContentSectionOut, status_code=status.HTTP_201_CREATED)
def create_section(
    payload: ContentSectionCreate,
    staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """섹션 추가 — 임원진 이상."""
    _check_page(payload.page)
    _check_body(payload.body)
    _check_width(payload.width)

    order = payload.sortOrder
    if order is None:
        # 맨 뒤로. 같은 페이지의 최대값 + 1
        last = (
            db.query(ContentSection)
            .filter(ContentSection.page == payload.page)
            .order_by(ContentSection.sort_order.desc())
            .first()
        )
        order = (last.sort_order + 1) if last else 0

    section = ContentSection(
        page=payload.page,
        title=(payload.title or "").strip() or None,
        body=payload.body,
        sort_order=order,
        visible=payload.visible,
        width=payload.width,
        updated_by=staff.id,
        updated_at=_now(),
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return ContentSectionOut.model_validate(section)


@router.patch("/{section_id}", response_model=ContentSectionOut)
def update_section(
    section_id: int,
    payload: ContentSectionUpdate,
    staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """섹션 수정 — 임원진 이상. 보낸 필드만 반영한다."""
    section = db.get(ContentSection, section_id)
    if section is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "섹션을 찾을 수 없습니다.")

    if payload.title is not None:
        # 빈 문자열은 "제목 없음"으로 (본문만 있는 섹션 허용)
        section.title = payload.title.strip() or None
    if payload.body is not None:
        _check_body(payload.body)
        section.body = payload.body
    if payload.sortOrder is not None:
        section.sort_order = payload.sortOrder
    if payload.visible is not None:
        section.visible = payload.visible
    if payload.width is not None:
        _check_width(payload.width)
        section.width = payload.width

    section.updated_by = staff.id
    section.updated_at = _now()
    db.commit()
    db.refresh(section)
    return ContentSectionOut.model_validate(section)


@router.post("/{page}/reorder", response_model=list[ContentSectionOut])
def reorder_sections(
    page: str,
    payload: ContentReorder,
    staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """순서 일괄 변경 — 임원진 이상. 보낸 id 순서대로 0,1,2… 를 다시 매긴다.

    한 칸씩 올리고 내릴 때마다 PATCH를 두 번 쏘면 중간에 실패했을 때 순서가 꼬인다.
    화면이 보고 있는 최종 순서를 통째로 보내 한 트랜잭션에서 확정한다.
    """
    _check_page(page)
    sections = {
        s.id: s
        for s in db.query(ContentSection).filter(ContentSection.page == page).all()
    }
    # 다른 페이지의 id나 없는 id가 섞이면 순서가 조용히 어긋난다 — 먼저 막는다.
    unknown = [i for i in payload.ids if i not in sections]
    if unknown:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"이 페이지에 없는 섹션입니다: {unknown}",
        )
    if len(payload.ids) != len(sections):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "순서 목록에 이 페이지의 섹션이 모두 들어 있어야 합니다.",
        )

    for order, sid in enumerate(payload.ids):
        sections[sid].sort_order = order
    db.commit()

    items = (
        db.query(ContentSection)
        .filter(ContentSection.page == page)
        .order_by(ContentSection.sort_order, ContentSection.id)
        .all()
    )
    return [ContentSectionOut.model_validate(s) for s in items]


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(
    section_id: int,
    staff: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """섹션 삭제 — 임원진 이상."""
    section = db.get(ContentSection, section_id)
    if section is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "섹션을 찾을 수 없습니다.")
    db.delete(section)
    db.commit()
