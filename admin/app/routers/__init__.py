from fastapi import APIRouter

from .admins import router as admins_router
from .analytics import router as analytics_router
from .bids import router as bids_router
from .client_actions import router as client_actions_router
from .masters import router as masters_router
from .orders import router as orders_router
from .payouts import router as payouts_router
from .specialists import router as specialists_router
from .specialties import router as specialties_router
from .users import router as users_router

# Создаем корневой роутер
api_router = APIRouter()

# Подключаем все роутеры
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
api_router.include_router(bids_router, prefix="/bids", tags=["bids"])
api_router.include_router(payouts_router, prefix="/payouts", tags=["payouts"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(masters_router, prefix="/masters", tags=["masters"])
api_router.include_router(admins_router, prefix="/admins", tags=["admins"])
api_router.include_router(specialties_router, prefix="/specialties", tags=["specialties"])
api_router.include_router(specialists_router, prefix="/specialists", tags=["specialists"])
api_router.include_router(client_actions_router, prefix="/client-actions", tags=["client_actions"])
