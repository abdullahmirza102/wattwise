from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ReadingSchema(BaseModel):
    id: int
    home_id: int
    device_id: Optional[int] = None
    timestamp: datetime
    kwh_consumed: float
    voltage: Optional[float] = None
    current: Optional[float] = None
    power_factor: Optional[float] = None

    model_config = {"from_attributes": True}


class ReadingQuery(BaseModel):
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    device_id: Optional[int] = None
    granularity: str = "hour"  # hour, day, week


class ReadingAggregated(BaseModel):
    period: str
    total_kwh: float
    avg_kwh: float
    max_kwh: float
    cost: float
    reading_count: int
