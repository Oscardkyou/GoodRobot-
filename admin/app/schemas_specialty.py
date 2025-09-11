
from pydantic import BaseModel


# Схемы для специальностей
class SpecialtyBase(BaseModel):
    name: str
    is_active: bool = True

class SpecialtyCreate(SpecialtyBase):
    pass

class SpecialtyUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None

class SpecialtyResponse(SpecialtyBase):
    id: int

    class Config:
        from_attributes = True

# Схема для добавления специальностей мастеру
class MasterSpecialtyUpdate(BaseModel):
    specialty_ids: list[int]
