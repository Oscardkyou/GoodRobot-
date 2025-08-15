from fastapi import APIRouter

from .users import router as users_router
from .orders import router as orders_router
from .bids import router as bids_router
from .payouts import router as payouts_router
from .analytics import router as analytics_router

# Создаем корневой роутер
api_router = APIRouter()

# Подключаем все роутеры
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
api_router.include_router(bids_router, prefix="/bids", tags=["bids"])
api_router.include_router(payouts_router, prefix="/payouts", tags=["payouts"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])