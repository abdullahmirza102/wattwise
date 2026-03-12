"""
Bill Forecasting Engine
Uses day-of-week seasonality + trend projection on the last 60 days of data.
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

import numpy as np
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models import EnergyReading, Forecast, Home
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def generate_forecast(session: Session, home_id: int) -> Optional[Dict]:
    """Generate a 30-day forecast for a home based on the last 60 days of data."""
    home = session.query(Home).filter(Home.id == home_id).first()
    if not home:
        logger.error(f"Home {home_id} not found")
        return None

    now = datetime.now(timezone.utc)
    sixty_days_ago = now - timedelta(days=60)

    # Get daily aggregated consumption
    daily_data = (
        session.query(
            func.date_trunc("day", EnergyReading.timestamp).label("day"),
            func.sum(EnergyReading.kwh_consumed).label("total_kwh"),
        )
        .filter(and_(
            EnergyReading.home_id == home_id,
            EnergyReading.timestamp >= sixty_days_ago,
        ))
        .group_by(func.date_trunc("day", EnergyReading.timestamp))
        .order_by(func.date_trunc("day", EnergyReading.timestamp))
        .all()
    )

    if len(daily_data) < 7:
        logger.warning(f"Home {home_id}: insufficient data for forecast ({len(daily_data)} days)")
        return None

    # Build arrays
    days = []
    values = []
    for row in daily_data:
        days.append(row.day)
        values.append(float(row.total_kwh))

    values = np.array(values)

    # Day-of-week seasonality
    dow_avg = {}
    for i, d in enumerate(days):
        dow = d.weekday()
        if dow not in dow_avg:
            dow_avg[dow] = []
        dow_avg[dow].append(values[i])
    for dow in dow_avg:
        dow_avg[dow] = np.mean(dow_avg[dow])

    # Linear trend
    x = np.arange(len(values))
    if len(x) > 1:
        coeffs = np.polyfit(x, values, 1)
        slope = coeffs[0]
        intercept = coeffs[1]
    else:
        slope = 0
        intercept = values[0]

    # Generate 30-day predictions
    daily_predictions = []
    total_predicted_kwh = 0
    residuals = []

    # Calculate residuals for confidence interval
    for i in range(len(values)):
        trend = slope * i + intercept
        dow = days[i].weekday()
        seasonal = dow_avg.get(dow, np.mean(values))
        predicted = (trend + seasonal) / 2
        residuals.append(values[i] - predicted)

    residual_std = np.std(residuals) if residuals else 0

    for day_offset in range(1, 31):
        future_date = now + timedelta(days=day_offset)
        dow = future_date.weekday()

        trend_value = slope * (len(values) + day_offset) + intercept
        seasonal_value = dow_avg.get(dow, np.mean(values))

        predicted = max(0, (trend_value + seasonal_value) / 2)
        lower = max(0, predicted - 1.96 * residual_std)
        upper = predicted + 1.96 * residual_std

        daily_predictions.append({
            "date": future_date.strftime("%Y-%m-%d"),
            "predicted_kwh": round(predicted, 2),
            "lower_bound": round(lower, 2),
            "upper_bound": round(upper, 2),
        })
        total_predicted_kwh += predicted

    predicted_cost = round(total_predicted_kwh * home.tariff_rate_per_kwh, 2)
    confidence_lower = round(sum(d["lower_bound"] for d in daily_predictions) * home.tariff_rate_per_kwh, 2)
    confidence_upper = round(sum(d["upper_bound"] for d in daily_predictions) * home.tariff_rate_per_kwh, 2)

    # Confidence score based on data quality
    data_days = len(daily_data)
    confidence_score = min(0.95, 0.5 + (data_days / 60) * 0.4 + (0.05 if residual_std < np.mean(values) * 0.3 else 0))

    forecast_month = (now + timedelta(days=15)).strftime("%Y-%m")

    # Upsert forecast
    existing = session.query(Forecast).filter(
        and_(Forecast.home_id == home_id, Forecast.forecast_month == forecast_month)
    ).first()

    if existing:
        existing.predicted_kwh = round(total_predicted_kwh, 2)
        existing.predicted_cost = predicted_cost
        existing.confidence_score = round(confidence_score, 2)
        existing.confidence_lower = confidence_lower
        existing.confidence_upper = confidence_upper
        existing.daily_predictions = json.dumps(daily_predictions)
    else:
        forecast = Forecast(
            home_id=home_id,
            forecast_month=forecast_month,
            predicted_kwh=round(total_predicted_kwh, 2),
            predicted_cost=predicted_cost,
            confidence_score=round(confidence_score, 2),
            confidence_lower=confidence_lower,
            confidence_upper=confidence_upper,
            daily_predictions=json.dumps(daily_predictions),
        )
        session.add(forecast)

    session.commit()
    logger.info(f"Home {home_id}: forecast generated - {total_predicted_kwh:.1f} kWh, ${predicted_cost}")

    return {
        "home_id": home_id,
        "forecast_month": forecast_month,
        "predicted_kwh": round(total_predicted_kwh, 2),
        "predicted_cost": predicted_cost,
        "confidence_score": round(confidence_score, 2),
        "daily_predictions": daily_predictions,
    }
