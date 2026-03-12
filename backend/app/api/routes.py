import csv
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import func, text, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.config import get_settings
from app.core.redis import cache_get, cache_set, cache_delete
from app.models import Home, Device, EnergyReading, Anomaly, Forecast
from app.schemas.dashboard import (
    DashboardResponse, KPICards, DailyConsumption, ComparisonData,
)
from app.schemas.device import DeviceBreakdown
from app.schemas.anomaly import AnomalySchema, AnomalyList
from app.schemas.forecast import ForecastSchema
from app.schemas.energy_reading import ReadingSchema, ReadingAggregated

router = APIRouter(tags=["energy"])
settings = get_settings()


def get_tariff_rate(hour: int) -> float:
    """Time-of-Use tariff: peak 2-7pm, off-peak 11pm-7am, standard otherwise."""
    if 14 <= hour < 19:
        return settings.PEAK_RATE
    elif hour >= 23 or hour < 7:
        return settings.OFF_PEAK_RATE
    else:
        return settings.STANDARD_RATE


# ── Dashboard ───────────────────────────────────────────────────────────

@router.get("/homes/{home_id}/dashboard", response_model=DashboardResponse)
async def get_dashboard(home_id: int, db: AsyncSession = Depends(get_db)):
    # Check cache
    cache_key = f"dashboard:{home_id}"
    cached = await cache_get(cache_key)
    if cached:
        return DashboardResponse(**cached)

    # Verify home exists
    home = (await db.execute(select(Home).where(Home.id == home_id))).scalar_one_or_none()
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    last_month_end = month_start - timedelta(seconds=1)

    # Today's kWh
    today_result = await db.execute(
        select(func.coalesce(func.sum(EnergyReading.kwh_consumed), 0.0))
        .where(and_(EnergyReading.home_id == home_id, EnergyReading.timestamp >= today_start))
    )
    today_kwh = float(today_result.scalar())

    # This month kWh
    month_result = await db.execute(
        select(func.coalesce(func.sum(EnergyReading.kwh_consumed), 0.0))
        .where(and_(EnergyReading.home_id == home_id, EnergyReading.timestamp >= month_start))
    )
    month_kwh = float(month_result.scalar())

    # Last month kWh
    last_month_result = await db.execute(
        select(func.coalesce(func.sum(EnergyReading.kwh_consumed), 0.0))
        .where(and_(
            EnergyReading.home_id == home_id,
            EnergyReading.timestamp >= last_month_start,
            EnergyReading.timestamp <= last_month_end,
        ))
    )
    last_month_kwh = float(last_month_result.scalar())

    month_cost = round(month_kwh * home.tariff_rate_per_kwh, 2)
    last_month_cost = round(last_month_kwh * home.tariff_rate_per_kwh, 2)
    pct_change = None
    if last_month_cost > 0:
        pct_change = round(((month_cost - last_month_cost) / last_month_cost) * 100, 1)

    # Active anomalies count
    anomaly_count_result = await db.execute(
        select(func.count(Anomaly.id))
        .where(and_(Anomaly.home_id == home_id, Anomaly.is_acknowledged == False))
    )
    active_anomalies = anomaly_count_result.scalar()

    # Predicted bill
    forecast_result = await db.execute(
        select(Forecast)
        .where(Forecast.home_id == home_id)
        .order_by(Forecast.created_at.desc())
        .limit(1)
    )
    latest_forecast = forecast_result.scalar_one_or_none()
    predicted_bill = latest_forecast.predicted_cost if latest_forecast else None

    # Current wattage (latest reading)
    latest_reading_result = await db.execute(
        select(EnergyReading)
        .where(EnergyReading.home_id == home_id)
        .order_by(EnergyReading.timestamp.desc())
        .limit(1)
    )
    latest_reading = latest_reading_result.scalar_one_or_none()
    current_wattage = None
    if latest_reading:
        current_wattage = round(latest_reading.kwh_consumed * 12000, 1)  # Convert 5-sec reading to watts approx

    kpi = KPICards(
        today_kwh=round(today_kwh, 2),
        today_cost=round(today_kwh * home.tariff_rate_per_kwh, 2),
        month_kwh=round(month_kwh, 2),
        month_cost=month_cost,
        month_vs_last_month_pct=pct_change,
        active_anomalies=active_anomalies,
        predicted_bill=predicted_bill,
        current_wattage=current_wattage,
    )

    # Daily consumption for last 7 days
    seven_days_ago = now - timedelta(days=7)
    daily_query = await db.execute(
        select(
            func.date_trunc("day", EnergyReading.timestamp).label("day"),
            func.sum(EnergyReading.kwh_consumed).label("total_kwh"),
        )
        .where(and_(EnergyReading.home_id == home_id, EnergyReading.timestamp >= seven_days_ago))
        .group_by(text("1"))
        .order_by(text("1"))
    )
    daily_rows = daily_query.all()
    daily_consumption = [
        DailyConsumption(
            date=str(row.day.date()) if row.day else "",
            kwh=round(float(row.total_kwh), 2),
            cost=round(float(row.total_kwh) * home.tariff_rate_per_kwh, 2),
            is_peak_heavy=float(row.total_kwh) > (month_kwh / max(now.day, 1)) * 1.3,
        )
        for row in daily_rows
    ]

    # Top devices breakdown
    device_query = await db.execute(
        select(
            Device.id,
            Device.name,
            Device.type,
            func.coalesce(func.sum(EnergyReading.kwh_consumed), 0.0).label("total_kwh"),
        )
        .outerjoin(EnergyReading, and_(
            EnergyReading.device_id == Device.id,
            EnergyReading.timestamp >= month_start,
        ))
        .where(Device.home_id == home_id)
        .group_by(Device.id, Device.name, Device.type)
        .order_by(text("total_kwh DESC"))
    )
    device_rows = device_query.all()
    total_device_kwh = sum(float(r.total_kwh) for r in device_rows) or 1.0

    top_devices = [
        DeviceBreakdown(
            device_id=r.id,
            device_name=r.name,
            device_type=r.type,
            monthly_kwh=round(float(r.total_kwh), 2),
            monthly_cost=round(float(r.total_kwh) * home.tariff_rate_per_kwh, 2),
            percentage_of_total=round((float(r.total_kwh) / total_device_kwh) * 100, 1),
        )
        for r in device_rows
    ]

    # Recent anomalies
    anomaly_query = await db.execute(
        select(Anomaly)
        .where(Anomaly.home_id == home_id)
        .order_by(Anomaly.detected_at.desc())
        .limit(5)
    )
    recent_anomalies = [
        AnomalySchema(
            id=a.id, home_id=a.home_id, reading_id=a.reading_id,
            device_id=a.device_id, anomaly_type=a.anomaly_type,
            severity=a.severity, detected_at=a.detected_at,
            description=a.description, estimated_extra_cost=a.estimated_extra_cost,
            is_acknowledged=a.is_acknowledged, acknowledged_at=a.acknowledged_at,
        )
        for a in anomaly_query.scalars().all()
    ]

    # Comparison
    year_ago_start = month_start.replace(year=month_start.year - 1)
    year_ago_end = year_ago_start.replace(month=year_ago_start.month % 12 + 1) if year_ago_start.month < 12 else year_ago_start.replace(year=year_ago_start.year + 1, month=1)
    year_ago_result = await db.execute(
        select(func.coalesce(func.sum(EnergyReading.kwh_consumed), 0.0))
        .where(and_(
            EnergyReading.home_id == home_id,
            EnergyReading.timestamp >= year_ago_start,
            EnergyReading.timestamp < year_ago_end,
        ))
    )
    year_ago_kwh = float(year_ago_result.scalar())

    comparison = ComparisonData(
        this_month_kwh=round(month_kwh, 2),
        this_month_cost=month_cost,
        last_month_kwh=round(last_month_kwh, 2),
        last_month_cost=last_month_cost,
        same_month_last_year_kwh=round(year_ago_kwh, 2) if year_ago_kwh > 0 else None,
        same_month_last_year_cost=round(year_ago_kwh * home.tariff_rate_per_kwh, 2) if year_ago_kwh > 0 else None,
    )

    response = DashboardResponse(
        home_id=home.id,
        home_name=home.name,
        kpi=kpi,
        daily_consumption=daily_consumption,
        top_devices=top_devices,
        recent_anomalies=recent_anomalies,
        comparison=comparison,
    )

    # Cache for 30 seconds
    await cache_set(cache_key, response.model_dump(), ttl=30)
    return response


# ── Readings ────────────────────────────────────────────────────────────

@router.get("/homes/{home_id}/readings")
async def get_readings(
    home_id: int,
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    device_id: Optional[int] = None,
    granularity: str = Query("hour", regex="^(hour|day|week)$"),
    db: AsyncSession = Depends(get_db),
):
    home = (await db.execute(select(Home).where(Home.id == home_id))).scalar_one_or_none()
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")

    now = datetime.now(timezone.utc)
    if not from_date:
        from_date = now - timedelta(days=7)
    if not to_date:
        to_date = now

    filters = [
        EnergyReading.home_id == home_id,
        EnergyReading.timestamp >= from_date,
        EnergyReading.timestamp <= to_date,
    ]
    if device_id:
        filters.append(EnergyReading.device_id == device_id)

    trunc_map = {"hour": "hour", "day": "day", "week": "week"}
    trunc = trunc_map[granularity]

    query = (
        select(
            func.date_trunc(trunc, EnergyReading.timestamp).label("period"),
            func.sum(EnergyReading.kwh_consumed).label("total_kwh"),
            func.avg(EnergyReading.kwh_consumed).label("avg_kwh"),
            func.max(EnergyReading.kwh_consumed).label("max_kwh"),
            func.count(EnergyReading.id).label("reading_count"),
        )
        .where(and_(*filters))
        .group_by(text("1"))
        .order_by(text("1"))
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        ReadingAggregated(
            period=str(r.period),
            total_kwh=round(float(r.total_kwh), 4),
            avg_kwh=round(float(r.avg_kwh), 4),
            max_kwh=round(float(r.max_kwh), 4),
            cost=round(float(r.total_kwh) * home.tariff_rate_per_kwh, 2),
            reading_count=r.reading_count,
        )
        for r in rows
    ]


# ── Anomalies ───────────────────────────────────────────────────────────

@router.get("/homes/{home_id}/anomalies", response_model=AnomalyList)
async def get_anomalies(
    home_id: int,
    unacknowledged_only: bool = Query(False),
    severity: Optional[str] = None,
    device_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    home = (await db.execute(select(Home).where(Home.id == home_id))).scalar_one_or_none()
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")

    filters = [Anomaly.home_id == home_id]
    if unacknowledged_only:
        filters.append(Anomaly.is_acknowledged == False)
    if severity:
        filters.append(Anomaly.severity == severity)
    if device_id:
        filters.append(Anomaly.device_id == device_id)

    result = await db.execute(
        select(Anomaly).where(and_(*filters)).order_by(Anomaly.detected_at.desc())
    )
    anomalies = result.scalars().all()

    unack_result = await db.execute(
        select(func.count(Anomaly.id))
        .where(and_(Anomaly.home_id == home_id, Anomaly.is_acknowledged == False))
    )
    unack_count = unack_result.scalar()

    return AnomalyList(
        anomalies=[
            AnomalySchema(
                id=a.id, home_id=a.home_id, reading_id=a.reading_id,
                device_id=a.device_id, anomaly_type=a.anomaly_type,
                severity=a.severity, detected_at=a.detected_at,
                description=a.description, estimated_extra_cost=a.estimated_extra_cost,
                is_acknowledged=a.is_acknowledged, acknowledged_at=a.acknowledged_at,
            )
            for a in anomalies
        ],
        total=len(anomalies),
        unacknowledged_count=unack_count,
    )


@router.post("/homes/{home_id}/anomalies/{anomaly_id}/acknowledge")
async def acknowledge_anomaly(
    home_id: int, anomaly_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Anomaly).where(and_(Anomaly.id == anomaly_id, Anomaly.home_id == home_id))
    )
    anomaly = result.scalar_one_or_none()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    anomaly.is_acknowledged = True
    anomaly.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()

    await cache_delete(f"dashboard:{home_id}")
    return {"status": "acknowledged", "anomaly_id": anomaly_id}


# ── Forecast ────────────────────────────────────────────────────────────

@router.get("/homes/{home_id}/forecast", response_model=Optional[ForecastSchema])
async def get_forecast(home_id: int, db: AsyncSession = Depends(get_db)):
    home = (await db.execute(select(Home).where(Home.id == home_id))).scalar_one_or_none()
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")

    result = await db.execute(
        select(Forecast)
        .where(Forecast.home_id == home_id)
        .order_by(Forecast.created_at.desc())
        .limit(1)
    )
    forecast = result.scalar_one_or_none()
    if not forecast:
        return None

    daily_preds = None
    if forecast.daily_predictions:
        try:
            daily_preds = json.loads(forecast.daily_predictions)
        except (json.JSONDecodeError, TypeError):
            daily_preds = None

    return ForecastSchema(
        id=forecast.id,
        home_id=forecast.home_id,
        forecast_month=forecast.forecast_month,
        predicted_kwh=forecast.predicted_kwh,
        predicted_cost=forecast.predicted_cost,
        confidence_score=forecast.confidence_score,
        confidence_lower=forecast.confidence_lower,
        confidence_upper=forecast.confidence_upper,
        daily_predictions=daily_preds,
        created_at=forecast.created_at,
    )


# ── Device Breakdown ────────────────────────────────────────────────────

@router.get("/homes/{home_id}/devices/breakdown")
async def get_device_breakdown(home_id: int, db: AsyncSession = Depends(get_db)):
    home = (await db.execute(select(Home).where(Home.id == home_id))).scalar_one_or_none()
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    device_query = await db.execute(
        select(
            Device.id,
            Device.name,
            Device.type,
            Device.is_active,
            func.coalesce(func.sum(EnergyReading.kwh_consumed), 0.0).label("total_kwh"),
        )
        .outerjoin(EnergyReading, and_(
            EnergyReading.device_id == Device.id,
            EnergyReading.timestamp >= month_start,
        ))
        .where(Device.home_id == home_id)
        .group_by(Device.id, Device.name, Device.type, Device.is_active)
        .order_by(text("total_kwh DESC"))
    )
    device_rows = device_query.all()
    total_kwh = sum(float(r.total_kwh) for r in device_rows) or 1.0

    # Find cheapest hour for each device
    breakdowns = []
    for r in device_rows:
        # Find hour with lowest average usage for this device
        hour_query = await db.execute(
            select(
                extract("hour", EnergyReading.timestamp).label("hr"),
                func.avg(EnergyReading.kwh_consumed).label("avg_kwh"),
            )
            .where(and_(
                EnergyReading.device_id == r.id,
                EnergyReading.timestamp >= month_start,
            ))
            .group_by(text("1"))
            .order_by(text("avg_kwh ASC"))
            .limit(1)
        )
        cheapest_row = hour_query.first()
        cheapest_hour = int(cheapest_row.hr) if cheapest_row else None

        # Potential savings: difference between peak and off-peak cost
        device_kwh = float(r.total_kwh)
        peak_cost = device_kwh * settings.PEAK_RATE
        offpeak_cost = device_kwh * settings.OFF_PEAK_RATE
        potential_savings = round(peak_cost - offpeak_cost, 2) if device_kwh > 0 else 0

        # Check if device has anomalies
        anomaly_check = await db.execute(
            select(func.count(Anomaly.id))
            .where(and_(
                Anomaly.device_id == r.id,
                Anomaly.is_acknowledged == False,
            ))
        )
        has_anomaly = anomaly_check.scalar() > 0

        status = "anomalous" if has_anomaly else ("active" if r.is_active else "idle")

        breakdowns.append(DeviceBreakdown(
            device_id=r.id,
            device_name=r.name,
            device_type=r.type,
            monthly_kwh=round(device_kwh, 2),
            monthly_cost=round(device_kwh * home.tariff_rate_per_kwh, 2),
            percentage_of_total=round((device_kwh / total_kwh) * 100, 1),
            cheapest_hour=cheapest_hour,
            potential_savings=potential_savings,
            status=status,
        ))

    return breakdowns


# ── Compare ─────────────────────────────────────────────────────────────

@router.get("/homes/{home_id}/compare", response_model=ComparisonData)
async def compare_periods(home_id: int, db: AsyncSession = Depends(get_db)):
    home = (await db.execute(select(Home).where(Home.id == home_id))).scalar_one_or_none()
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    last_month_end = month_start - timedelta(seconds=1)

    async def sum_kwh(start, end):
        r = await db.execute(
            select(func.coalesce(func.sum(EnergyReading.kwh_consumed), 0.0))
            .where(and_(
                EnergyReading.home_id == home_id,
                EnergyReading.timestamp >= start,
                EnergyReading.timestamp <= end,
            ))
        )
        return float(r.scalar())

    this_kwh = await sum_kwh(month_start, now)
    last_kwh = await sum_kwh(last_month_start, last_month_end)

    year_ago_start = month_start.replace(year=month_start.year - 1)
    year_ago_end = now.replace(year=now.year - 1)
    year_kwh = await sum_kwh(year_ago_start, year_ago_end)

    rate = home.tariff_rate_per_kwh
    return ComparisonData(
        this_month_kwh=round(this_kwh, 2),
        this_month_cost=round(this_kwh * rate, 2),
        last_month_kwh=round(last_kwh, 2),
        last_month_cost=round(last_kwh * rate, 2),
        same_month_last_year_kwh=round(year_kwh, 2) if year_kwh > 0 else None,
        same_month_last_year_cost=round(year_kwh * rate, 2) if year_kwh > 0 else None,
    )


# ── CSV Upload ──────────────────────────────────────────────────────────

@router.post("/homes/{home_id}/upload-csv")
async def upload_csv(
    home_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    home = (await db.execute(select(Home).where(Home.id == home_id))).scalar_one_or_none()
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(decoded))
    rows_imported = 0
    errors = []

    for i, row in enumerate(reader):
        try:
            # Support common column names
            ts_val = row.get("timestamp") or row.get("Timestamp") or row.get("datetime") or row.get("DateTime")
            kwh_val = row.get("kwh") or row.get("kWh") or row.get("kwh_consumed") or row.get("consumption")

            if not ts_val or not kwh_val:
                errors.append(f"Row {i+1}: missing timestamp or kwh column")
                continue

            ts = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            kwh = float(kwh_val)

            reading = EnergyReading(
                home_id=home_id,
                timestamp=ts,
                kwh_consumed=kwh,
            )
            db.add(reading)
            rows_imported += 1
        except (ValueError, KeyError) as e:
            errors.append(f"Row {i+1}: {str(e)}")

    await db.commit()
    await cache_delete(f"dashboard:{home_id}")

    return {
        "status": "success",
        "rows_imported": rows_imported,
        "errors": errors[:10],  # Limit error reporting
        "total_errors": len(errors),
    }


# ── What-If Analysis ───────────────────────────────────────────────────

@router.post("/homes/{home_id}/what-if")
async def what_if_analysis(
    home_id: int,
    device_type: str = Query(...),
    reduction_percent: float = Query(..., ge=0, le=100),
    db: AsyncSession = Depends(get_db),
):
    home = (await db.execute(select(Home).where(Home.id == home_id))).scalar_one_or_none()
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get device kwh for this type
    result = await db.execute(
        select(func.coalesce(func.sum(EnergyReading.kwh_consumed), 0.0))
        .join(Device, EnergyReading.device_id == Device.id)
        .where(and_(
            EnergyReading.home_id == home_id,
            Device.type == device_type,
            EnergyReading.timestamp >= month_start,
        ))
    )
    device_kwh = float(result.scalar())
    saved_kwh = device_kwh * (reduction_percent / 100.0)
    saved_cost = round(saved_kwh * home.tariff_rate_per_kwh, 2)

    return {
        "device_type": device_type,
        "current_monthly_kwh": round(device_kwh, 2),
        "reduction_percent": reduction_percent,
        "saved_kwh": round(saved_kwh, 2),
        "saved_cost": saved_cost,
        "new_monthly_kwh": round(device_kwh - saved_kwh, 2),
        "new_monthly_cost": round((device_kwh - saved_kwh) * home.tariff_rate_per_kwh, 2),
    }
