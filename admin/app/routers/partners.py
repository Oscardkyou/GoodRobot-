import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import or_, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from admin.app.auth import get_current_admin
from app.models.partner import Partner
from app.models.user import User
from core.db import get_session
from core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="admin/templates")
settings = get_settings()


class PartnerUpsertIn(BaseModel):
    tg_id: Optional[int] = Field(default=None, description="Telegram ID пользователя")
    phone: Optional[str] = Field(default=None, description="Телефон пользователя (+7 ...) без пробелов")
    payout_percent: Optional[int] = Field(default=None, ge=0, le=100)
    slug: Optional[str] = None
    referral_code: Optional[str] = None


class PartnerResponse(BaseModel):
    id: int
    user_id: int
    tg_id: Optional[int]
    phone: Optional[str]
    name: Optional[str]
    payout_percent: int
    referral_code: Optional[str]
    slug: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_class=HTMLResponse)
async def get_partners_page(request: Request, current_admin=Depends(get_current_admin)):
    """Страница управления партнёрами (дашборд)."""
    is_superadmin = _is_superadmin_username(getattr(current_admin, "username", None))
    return templates.TemplateResponse(
        "partners.html",
        {"request": request, "page_type": "private", "is_superadmin": is_superadmin},
    )


@router.get("/api", response_model=list[PartnerResponse])
async def list_partners(
    search: Optional[str] = Query(default=None, description="Поиск по телефону, имени или tg_id"),
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
):
    """Список партнёров с фильтрацией по телефону/имени/tg_id."""
    stmt = (
        select(Partner, User)
        .join(User, User.id == Partner.user_id)
        .order_by(Partner.id.desc())
        .offset(skip)
        .limit(limit)
    )
    if search:
        like = f"%{search}%"
        try:
            tg_id_val = int(search)
        except Exception:
            tg_id_val = None
        stmt = stmt.filter(
            or_(
                User.phone.ilike(like),
                User.name.ilike(like),
                (User.tg_id == tg_id_val) if tg_id_val else False,
            )
        )
    res = await db.execute(stmt)
    rows = res.all()
    items: list[PartnerResponse] = []
    for p, u in rows:
        items.append(
            PartnerResponse(
                id=p.id,
                user_id=u.id,
                tg_id=u.tg_id,
                phone=u.phone,
                name=u.name,
                payout_percent=p.payout_percent,
                referral_code=p.referral_code,
                slug=p.slug,
            )
        )
    return items


def _is_superadmin_username(username: str | None) -> bool:
    if not username:
        return False
    raw = settings.superadmin_usernames or ""
    allowed = {u.strip().lower() for u in raw.split(",") if u.strip()}
    return username.strip().lower() in allowed


async def _get_or_create_user_by_identity(db: AsyncSession, tg_id: Optional[int], phone: Optional[str]) -> User:
    if not tg_id and not phone:
        raise HTTPException(status_code=400, detail="Нужно указать tg_id или phone")

    stmt = select(User)
    if tg_id and phone:
        stmt = stmt.filter(or_(User.tg_id == tg_id, User.phone == phone))
    elif tg_id:
        stmt = stmt.filter(User.tg_id == tg_id)
    else:
        stmt = stmt.filter(User.phone == phone)

    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if user:
        return user
    # Создаём минимального пользователя
    user = User(tg_id=tg_id or 0, phone=phone, role="partner", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/api", response_model=PartnerResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_partner(
    payload: PartnerUpsertIn,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
):
    """Создаёт или обновляет партнёра по tg_id/phone. Также обновляет payout_percent/slug/referral_code.
    Если пользователь не найден — создаётся (с ролью partner)."""
    # Разрешаем изменять payout_percent только суперадмину
    if payload.payout_percent is not None and not _is_superadmin_username(getattr(current_admin, "username", None)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Изменять процент партнёра может только суперадмин")
    user = await _get_or_create_user_by_identity(db, payload.tg_id, payload.phone)

    # Проверяем наличие Partner
    res = await db.execute(select(Partner).where(Partner.user_id == user.id))
    partner = res.scalar_one_or_none()
    created = False
    if not partner:
        # Генерируем дефолтные значения
        referral_code = payload.referral_code or (f"REF{user.tg_id:08d}" if user.tg_id else None)
        slug = payload.slug or (f"partner_{user.tg_id}" if user.tg_id else None)
        payout_percent = (
            payload.payout_percent
            if payload.payout_percent is not None
            else settings.partner_default_payout_percent
        )
        partner = Partner(user_id=user.id, referral_code=referral_code, slug=slug, payout_percent=payout_percent)
        db.add(partner)
        created = True
    else:
        # Обновление
        if payload.payout_percent is not None:
            partner.payout_percent = payload.payout_percent
        if payload.slug is not None:
            partner.slug = payload.slug
        if payload.referral_code is not None:
            partner.referral_code = payload.referral_code

    # Также можем обновить на стороне пользователя tg_id/phone
    if payload.tg_id and user.tg_id != payload.tg_id:
        user.tg_id = payload.tg_id
    if payload.phone and user.phone != payload.phone:
        user.phone = payload.phone

    await db.commit()
    await db.refresh(partner)
    # refetch user after commit
    await db.refresh(user)

    status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    # FastAPI ignores returned status_code with response_model; use Response if needed. Here fine.
    return PartnerResponse(
        id=partner.id,
        user_id=user.id,
        tg_id=user.tg_id,
        phone=user.phone,
        name=user.name,
        payout_percent=partner.payout_percent,
        referral_code=partner.referral_code,
        slug=partner.slug,
    )


@router.put("/api/{partner_id}", response_model=PartnerResponse)
async def update_partner(
    partner_id: int,
    payload: PartnerUpsertIn,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
):
    res = await db.execute(select(Partner, User).join(User, User.id == Partner.user_id).where(Partner.id == partner_id))
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Партнёр не найден")
    partner, user = row

    # Разрешаем изменять payout_percent только суперадмину
    if payload.payout_percent is not None:
        if not _is_superadmin_username(getattr(current_admin, "username", None)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Изменять процент партнёра может только суперадмин")
        partner.payout_percent = payload.payout_percent
    if payload.slug is not None:
        partner.slug = payload.slug
    if payload.referral_code is not None:
        partner.referral_code = payload.referral_code
    if payload.tg_id is not None:
        user.tg_id = payload.tg_id
    if payload.phone is not None:
        user.phone = payload.phone

    await db.commit()
    await db.refresh(partner)
    await db.refresh(user)

    return PartnerResponse(
        id=partner.id,
        user_id=user.id,
        tg_id=user.tg_id,
        phone=user.phone,
        name=user.name,
        payout_percent=partner.payout_percent,
        referral_code=partner.referral_code,
        slug=partner.slug,
    )


@router.delete("/api/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_partner(
    partner_id: int,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
):
    res = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = res.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Партнёр не найден")
    await db.execute(delete(Partner).where(Partner.id == partner_id))
    await db.commit()
    return HTMLResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/by_identity", response_model=PartnerResponse)
async def get_partner_by_identity(
    tg_id: Optional[int] = None,
    phone: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
):
    if not tg_id and not phone:
        raise HTTPException(status_code=400, detail="Нужно передать tg_id или phone")

    stmt = select(Partner, User).join(User, User.id == Partner.user_id)
    if tg_id and phone:
        stmt = stmt.filter(or_(User.tg_id == tg_id, User.phone == phone))
    elif tg_id:
        stmt = stmt.filter(User.tg_id == tg_id)
    else:
        stmt = stmt.filter(User.phone == phone)

    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Партнёр не найден")
    partner, user = row

    return PartnerResponse(
        id=partner.id,
        user_id=user.id,
        tg_id=user.tg_id,
        phone=user.phone,
        name=user.name,
        payout_percent=partner.payout_percent,
        referral_code=partner.referral_code,
        slug=partner.slug,
    )


@router.delete("/api/by_identity", status_code=status.HTTP_204_NO_CONTENT)
async def delete_partner_by_identity(
    tg_id: Optional[int] = None,
    phone: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    current_admin=Depends(get_current_admin),
):
    if not tg_id and not phone:
        raise HTTPException(status_code=400, detail="Нужно передать tg_id или phone")

    stmt = select(Partner).join(User, User.id == Partner.user_id)
    if tg_id and phone:
        stmt = stmt.filter(or_(User.tg_id == tg_id, User.phone == phone))
    elif tg_id:
        stmt = stmt.filter(User.tg_id == tg_id)
    else:
        stmt = stmt.filter(User.phone == phone)

    res = await db.execute(stmt)
    partner = res.scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Партнёр не найден")

    await db.execute(delete(Partner).where(Partner.id == partner.id))
    await db.commit()
    return HTMLResponse(status_code=status.HTTP_204_NO_CONTENT)
