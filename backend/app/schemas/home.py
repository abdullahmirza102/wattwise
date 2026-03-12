from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HomeCreate(BaseModel):
    name: str
    location: Optional[str] = None
    size_sqft: Optional[int] = None
    num_occupants: int = 2
    tariff_rate_per_kwh: float = 0.18


class HomeSchema(BaseModel):
    id: int
    name: str
    location: Optional[str] = None
    size_sqft: Optional[int] = None
    num_occupants: int
    tariff_rate_per_kwh: float
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
