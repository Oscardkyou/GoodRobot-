from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class TokenData(BaseModel):
    username: str | None = None
    scopes: list[str] = []

class Token(BaseModel):
    access_token: str
    token_type: str

# Схемы для пользователей
class UserRole(str, Enum):
    ADMIN = "admin"
    CLIENT = "client"
    MASTER = "master"
    PARTNER = "partner"

class UserBase(BaseModel):
    username: str
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: UserRole
    is_active: bool = True

class UserCreate(UserBase):
    password: str | None = None
    telegram_id: int | None = None
    zones: list[int] | None = None

class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = None

class UserResponse(UserBase):
    id: int
    telegram_id: int | None = None
    created_at: datetime
    last_login: datetime | None = None
    zones: list[int] | None = None

    class Config:
        from_attributes = True

# Схемы для заказов
class OrderStatus(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class OrderBase(BaseModel):
    title: str
    description: str
    price: float
    client_id: int
    status: OrderStatus = OrderStatus.NEW
    address: str | None = None
    latitude: str | None = None
    longitude: str | None = None

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: float | None = None
    status: OrderStatus | None = None
    address: str | None = None
    latitude: str | None = None
    longitude: str | None = None

class OrderResponse(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    client_username: str | None = None

    class Config:
        from_attributes = True

# Схемы для ставок
class BidStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class BidBase(BaseModel):
    order_id: int
    master_id: int
    price: float
    comment: str | None = None
    status: BidStatus = BidStatus.PENDING

class BidCreate(BidBase):
    pass

class BidUpdate(BaseModel):
    price: float | None = None
    comment: str | None = None
    status: BidStatus | None = None

class BidResponse(BidBase):
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    master_username: str | None = None
    order_title: str | None = None

    class Config:
        from_attributes = True

# Схемы для выплат
class PayoutStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"

class PayoutBase(BaseModel):
    user_id: int
    amount: float
    status: PayoutStatus = PayoutStatus.PENDING
    details: str | None = None

class PayoutCreate(PayoutBase):
    pass

class PayoutUpdate(BaseModel):
    amount: float | None = None
    status: PayoutStatus | None = None
    details: str | None = None

class PayoutResponse(PayoutBase):
    id: int
    created_at: datetime
    processed_at: datetime | None = None
    user_username: str | None = None

    class Config:
        from_attributes = True
