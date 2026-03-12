"""
Anomaly Detection Engine
Detects: sudden spikes, vampire drain, flat-line faults, peak hour overuse.
Uses Z-score + rolling window approach.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

import numpy as np
from sqlalchemy import func, and_, extract
from sqlalchemy.orm import Session
from sqlalchemy.future import select

from app.models import EnergyReading, Anomaly, Device
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Thresholds
SPIKE_ZSCORE_THRESHOLD = 3.0
VAMPIRE_DRAIN_HOUR_START = 1  # 1 AM
VAMPIRE_DRAIN_HOUR_END = 5    # 5 AM
VAMPIRE_DRAIN_WATT_THRESHOLD = 200  # Watts - anything above this at night is suspicious
FLATLINE_ZERO_HOURS = 2
PEAK_HOURS = range(14, 19)  # 2pm - 7pm
PEAK_OVERUSE_MULTIPLIER = 1.5


def detect_anomalies(session: Session, home_id: int, lookback_hours: int = 24) -> List[Dict]:
    """Run all anomaly detectors for a home. Returns list of detected anomalies."""
    now = datetime.now(timezone.utc)
    lookback_start = now - timedelta(hours=lookback_hours)

    anomalies = []
    anomalies.extend(_detect_spikes(session, home_id, lookback_start, now))
    anomalies.extend(_detect_vampire_drain(session, home_id, lookback_start, now))
    anomalies.extend(_detect_flatline(session, home_id, lookback_start, now))
    anomalies.extend(_detect_peak_overuse(session, home_id, lookback_start, now))

    # Deduplicate - don't re-create anomalies for the same reading
    new_anomalies = []
    for a in anomalies:
        existing = session.query(Anomaly).filter(
            and_(
                Anomaly.home_id == home_id,
                Anomaly.anomaly_type == a["anomaly_type"],
                Anomaly.device_id == a.get("device_id"),
                Anomaly.detected_at >= lookback_start,
            )
        ).first()
        if not existing:
            anomaly = Anomaly(
                home_id=home_id,
                reading_id=a.get("reading_id"),
                device_id=a.get("device_id"),
                anomaly_type=a["anomaly_type"],
                severity=a["severity"],
                description=a["description"],
                estimated_extra_cost=a.get("estimated_extra_cost", 0),
            )
            session.add(anomaly)
            new_anomalies.append(a)

    session.commit()
    logger.info(f"Home {home_id}: detected {len(new_anomalies)} new anomalies")
    return new_anomalies


def _detect_spikes(session: Session, home_id: int, start: datetime, end: datetime) -> List[Dict]:
    """Detect sudden spikes > 3x rolling average using Z-score."""
    anomalies = []

    devices = session.query(Device).filter(Device.home_id == home_id).all()
    for device in devices:
        readings = (
            session.query(EnergyReading)
            .filter(and_(
                EnergyReading.device_id == device.id,
                EnergyReading.timestamp >= start - timedelta(hours=48),  # Extra window for rolling avg
                EnergyReading.timestamp <= end,
            ))
            .order_by(EnergyReading.timestamp)
            .all()
        )
        if len(readings) < 20:
            continue

        values = np.array([r.kwh_consumed for r in readings])
        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            continue

        # Check readings in the lookback window only
        for r in readings:
            if r.timestamp < start:
                continue
            z_score = (r.kwh_consumed - mean) / std
            if z_score > SPIKE_ZSCORE_THRESHOLD:
                extra_kwh = r.kwh_consumed - mean
                extra_cost = round(extra_kwh * settings.PEAK_RATE, 2)
                anomalies.append({
                    "anomaly_type": "spike",
                    "severity": "critical" if z_score > 5 else "warning",
                    "device_id": device.id,
                    "reading_id": r.id,
                    "description": (
                        f"Sudden spike detected on {device.name}: "
                        f"{r.kwh_consumed:.3f} kWh (Z-score: {z_score:.1f}, "
                        f"avg: {mean:.3f} kWh). {extra_kwh:.3f} kWh above normal."
                    ),
                    "estimated_extra_cost": extra_cost,
                })
                break  # One spike per device per detection run

    return anomalies


def _detect_vampire_drain(session: Session, home_id: int, start: datetime, end: datetime) -> List[Dict]:
    """Detect devices consuming significant power between 1-5 AM."""
    anomalies = []

    devices = session.query(Device).filter(
        and_(Device.home_id == home_id, Device.type != "fridge", Device.type != "vampire")
    ).all()

    for device in devices:
        night_readings = (
            session.query(EnergyReading)
            .filter(and_(
                EnergyReading.device_id == device.id,
                EnergyReading.timestamp >= start,
                EnergyReading.timestamp <= end,
                extract("hour", EnergyReading.timestamp) >= VAMPIRE_DRAIN_HOUR_START,
                extract("hour", EnergyReading.timestamp) < VAMPIRE_DRAIN_HOUR_END,
            ))
            .all()
        )

        if not night_readings:
            continue

        avg_night_kwh = np.mean([r.kwh_consumed for r in night_readings])
        avg_watts = avg_night_kwh * 12000  # Approx conversion for 5-sec readings

        if avg_watts > VAMPIRE_DRAIN_WATT_THRESHOLD:
            hours = len(night_readings) * 5 / 3600  # Rough hours
            extra_cost = round(avg_night_kwh * len(night_readings) * settings.OFF_PEAK_RATE, 2)
            anomalies.append({
                "anomaly_type": "vampire_drain",
                "severity": "warning",
                "device_id": device.id,
                "reading_id": night_readings[-1].id if night_readings else None,
                "description": (
                    f"Vampire drain detected: {device.name} drawing ~{avg_watts:.0f}W "
                    f"between {VAMPIRE_DRAIN_HOUR_START}AM-{VAMPIRE_DRAIN_HOUR_END}AM. "
                    f"Consider turning it off at night."
                ),
                "estimated_extra_cost": extra_cost,
            })

    return anomalies


def _detect_flatline(session: Session, home_id: int, start: datetime, end: datetime) -> List[Dict]:
    """Detect zero/near-zero readings for extended periods (possible sensor fault)."""
    anomalies = []

    devices = session.query(Device).filter(
        and_(Device.home_id == home_id, Device.type.in_(["fridge", "hvac"]))
    ).all()

    for device in devices:
        readings = (
            session.query(EnergyReading)
            .filter(and_(
                EnergyReading.device_id == device.id,
                EnergyReading.timestamp >= start,
                EnergyReading.timestamp <= end,
            ))
            .order_by(EnergyReading.timestamp)
            .all()
        )

        if len(readings) < 10:
            continue

        # Check for consecutive near-zero readings
        zero_streak = 0
        max_zero_streak = 0
        for r in readings:
            if r.kwh_consumed < 0.001:  # Near zero
                zero_streak += 1
                max_zero_streak = max(max_zero_streak, zero_streak)
            else:
                zero_streak = 0

        # If consecutive zeros span > 2 hours worth of readings
        readings_per_hour = 3600 / 5  # 720 readings per hour at 5-sec intervals
        if max_zero_streak > readings_per_hour * FLATLINE_ZERO_HOURS:
            anomalies.append({
                "anomaly_type": "flatline",
                "severity": "critical",
                "device_id": device.id,
                "reading_id": readings[-1].id if readings else None,
                "description": (
                    f"Flat-line fault: {device.name} reported zero consumption for "
                    f"over {FLATLINE_ZERO_HOURS} hours. Possible sensor malfunction "
                    f"or device failure."
                ),
                "estimated_extra_cost": 0,
            })

    return anomalies


def _detect_peak_overuse(session: Session, home_id: int, start: datetime, end: datetime) -> List[Dict]:
    """Detect high consumption during expensive peak tariff windows (2-7pm)."""
    anomalies = []

    # Get average hourly consumption across all hours
    all_hourly = (
        session.query(
            extract("hour", EnergyReading.timestamp).label("hr"),
            func.avg(EnergyReading.kwh_consumed).label("avg_kwh"),
        )
        .filter(and_(
            EnergyReading.home_id == home_id,
            EnergyReading.timestamp >= start - timedelta(days=7),
        ))
        .group_by(extract("hour", EnergyReading.timestamp))
        .all()
    )

    if not all_hourly:
        return anomalies

    overall_avg = np.mean([float(h.avg_kwh) for h in all_hourly])

    for h in all_hourly:
        hr = int(h.hr)
        if hr in PEAK_HOURS and float(h.avg_kwh) > overall_avg * PEAK_OVERUSE_MULTIPLIER:
            extra_kwh_per_reading = float(h.avg_kwh) - overall_avg
            # Rough estimate: peak hours * readings per hour * extra kwh
            hours_in_peak = len(PEAK_HOURS)
            extra_cost = round(extra_kwh_per_reading * 720 * hours_in_peak * (settings.PEAK_RATE - settings.OFF_PEAK_RATE), 2)
            anomalies.append({
                "anomaly_type": "peak_overuse",
                "severity": "info",
                "device_id": None,
                "reading_id": None,
                "description": (
                    f"High consumption during peak hours ({hr}:00): "
                    f"{float(h.avg_kwh)*12000:.0f}W average vs {overall_avg*12000:.0f}W overall. "
                    f"Shifting load to off-peak hours could save ~${extra_cost:.2f}/month."
                ),
                "estimated_extra_cost": extra_cost,
            })
            break  # One peak overuse anomaly per run

    return anomalies
