from pydantic import BaseModel
from typing import List, Optional
from app.schemas.device import DeviceBreakdown
from app.schemas.anomaly import AnomalySchema


class KPICards(BaseModel):
    today_kwh: float
    today_cost: float
    month_kwh: float
    month_cost: float
    month_vs_last_month_pct: Optional[float] = None
    active_anomalies: int
    predicted_bill: Optional[float] = None
    current_wattage: Optional[float] = None


class DailyConsumption(BaseModel):
    date: str
    kwh: float
    cost: float
    is_peak_heavy: bool = False


class ComparisonData(BaseModel):
    this_month_kwh: float
    this_month_cost: float
    last_month_kwh: Optional[float] = None
    last_month_cost: Optional[float] = None
    same_month_last_year_kwh: Optional[float] = None
    same_month_last_year_cost: Optional[float] = None


class DashboardResponse(BaseModel):
    home_id: int
    home_name: str
    kpi: KPICards
    daily_consumption: List[DailyConsumption]
    top_devices: List[DeviceBreakdown]
    recent_anomalies: List[AnomalySchema]
    comparison: Optional[ComparisonData] = None
