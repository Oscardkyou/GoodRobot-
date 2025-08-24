from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []

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
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole
    is_active: bool = True

class UserCreate(UserBase):
    password: Optional[str] = None
    telegram_id: Optional[int] = None
    zones: Optional[List[int]] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserResponse(UserBase):
    id: int
    telegram_id: Optional[int] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    zones: Optional[List[int]] = None

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

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    status: Optional[OrderStatus] = None

class OrderResponse(OrderBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    client_username: Optional[str] = None
    
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
    comment: Optional[str] = None
    status: BidStatus = BidStatus.PENDING

class BidCreate(BidBase):
    pass

class BidUpdate(BaseModel):
    price: Optional[float] = None
    comment: Optional[str] = None
    status: Optional[BidStatus] = None

class BidResponse(BidBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    master_username: Optional[str] = None
    order_title: Optional[str] = None
    
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
    details: Optional[str] = None

class PayoutCreate(PayoutBase):
    pass

class PayoutUpdate(BaseModel):
    amount: Optional[float] = None
    status: Optional[PayoutStatus] = None
    details: Optional[str] = None

class PayoutResponse(PayoutBase):
    id: int
    created_at: datetime
    processed_at: Optional[datetime] = None
    user_username: Optional[str] = None
    
    class Config:
        from_attributes = True