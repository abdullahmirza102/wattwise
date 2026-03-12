from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DailyPrediction(BaseModel):
    date: str
    predicted_kwh: float
    lower_bound: float
    upper_bound: float


class ForecastSchema(BaseModel):
    id: Optional[int] = None
    home_id: int
    forecast_month: str
    predicted_kwh: float
    predicted_cost: float
    confidence_score: float
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    daily_predictions: Optional[List[DailyPrediction]] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WhatIfRequest(BaseModel):
    device_type: str
    reduction_percent: float  # 0-100
