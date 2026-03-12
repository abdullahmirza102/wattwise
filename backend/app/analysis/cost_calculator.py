"""
Cost Calculator with Time-of-Use tariff support.
"""
from datetime import datetime
from typing import List, Dict
from app.core.config import get_settings

settings = get_settings()


def get_tariff_rate(hour: int) -> float:
    """Get tariff rate based on time of use."""
    if 14 <= hour < 19:       # Peak: 2pm-7pm
        return settings.PEAK_RATE
    elif hour >= 23 or hour < 7:  # Off-peak: 11pm-7am
        return settings.OFF_PEAK_RATE
    else:                          # Standard
        return settings.STANDARD_RATE


def get_tariff_label(hour: int) -> str:
    if 14 <= hour < 19:
        return "peak"
    elif hour >= 23 or hour < 7:
        return "off-peak"
    else:
        return "standard"


def calculate_cost_for_readings(readings: List[Dict]) -> Dict:
    """
    Calculate cost breakdown for a set of readings.
    Each reading dict should have 'timestamp' (datetime) and 'kwh_consumed' (float).
    """
    total_cost = 0
    peak_cost = 0
    offpeak_cost = 0
    standard_cost = 0
    total_kwh = 0
    peak_kwh = 0
    offpeak_kwh = 0
    standard_kwh = 0

    for r in readings:
        ts = r["timestamp"]
        kwh = r["kwh_consumed"]
        hour = ts.hour if isinstance(ts, datetime) else 12

        rate = get_tariff_rate(hour)
        cost = kwh * rate
        total_cost += cost
        total_kwh += kwh

        label = get_tariff_label(hour)
        if label == "peak":
            peak_cost += cost
            peak_kwh += kwh
        elif label == "off-peak":
            offpeak_cost += cost
            offpeak_kwh += kwh
        else:
            standard_cost += cost
            standard_kwh += kwh

    return {
        "total_kwh": round(total_kwh, 4),
        "total_cost": round(total_cost, 2),
        "peak": {"kwh": round(peak_kwh, 4), "cost": round(peak_cost, 2), "rate": settings.PEAK_RATE},
        "off_peak": {"kwh": round(offpeak_kwh, 4), "cost": round(offpeak_cost, 2), "rate": settings.OFF_PEAK_RATE},
        "standard": {"kwh": round(standard_kwh, 4), "cost": round(standard_cost, 2), "rate": settings.STANDARD_RATE},
    }


def calculate_shift_savings(device_kwh_by_hour: Dict[int, float], device_name: str) -> Dict:
    """
    Calculate potential savings if a device's load is shifted to the cheapest hours.
    device_kwh_by_hour: {hour: total_kwh_for_that_hour}
    """
    current_cost = sum(kwh * get_tariff_rate(hour) for hour, kwh in device_kwh_by_hour.items())
    total_kwh = sum(device_kwh_by_hour.values())

    # Best case: all usage at off-peak rate
    best_cost = total_kwh * settings.OFF_PEAK_RATE
    savings = current_cost - best_cost

    # Find cheapest hour
    cheapest_hour = min(range(24), key=lambda h: get_tariff_rate(h))

    return {
        "device_name": device_name,
        "current_monthly_cost": round(current_cost, 2),
        "optimal_monthly_cost": round(best_cost, 2),
        "potential_savings": round(savings, 2),
        "recommendation": (
            f"If you shifted {device_name} usage to after 11pm, "
            f"you could save ${savings:.2f}/month."
        ) if savings > 0.50 else f"{device_name} is already running at efficient hours.",
        "cheapest_hour": cheapest_hour,
    }
