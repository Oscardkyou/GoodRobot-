"""Router for unified management screen (specialties & masters tabs)."""

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.app.database import get_db
from app.models.specialty import Specialty

templates = Jinja2Templates(directory="admin/templates")
router = APIRouter()


@router.get("/management", include_in_schema=False)
async def get_management_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Render unified management page with tabs."""
    result = await db.execute(select(Specialty).order_by(Specialty.name))
    specialties: list[Specialty] = result.scalars().all()
    return templates.TemplateResponse(
        "management.html",
        {
            "request": request,
            "specialties": specialties,
            "page_type": "private",
        },
    )
