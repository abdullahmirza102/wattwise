from pydantic import BaseModel
from typing import Optional


class DeviceSchema(BaseModel):
    id: int
    home_id: int
    name: str
    type: str
    wattage_rated: float
    is_active: bool

    model_config = {"from_attributes": True}


class DeviceBreakdown(BaseModel):
    device_id: int
    device_name: str
    device_type: str
    monthly_kwh: float
    monthly_cost: float
    percentage_of_total: float
    cheapest_hour: Optional[int] = None
    potential_savings: Optional[float] = None
    status: str = "active"  # active, idle, anomalous
