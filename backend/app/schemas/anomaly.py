from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AnomalySchema(BaseModel):
    id: int
    home_id: int
    reading_id: Optional[int] = None
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    anomaly_type: str
    severity: str
    detected_at: Optional[datetime] = None
    description: Optional[str] = None
    estimated_extra_cost: Optional[float] = 0.0
    is_acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AnomalyList(BaseModel):
    anomalies: List[AnomalySchema]
    total: int
    unacknowledged_count: int
