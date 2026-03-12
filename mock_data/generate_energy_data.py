"""
Realistic Energy Mock Data Generator
Simulates a real home's energy consumption with circadian rhythm,
seasonal variation, per-device patterns, and optional anomaly injection.
"""
import argparse
import json
import os
import sys
import random
from datetime import datetime, timedelta, timezone

import numpy as np

# Add parent to path so we can import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import SyncSessionLocal
from app.core.init_db import init_db
from app.models import Home, Device, EnergyReading, Anomaly

# Load scenario configs
SCENARIO_DIR = os.path.join(os.path.dirname(__file__), "scenarios")


def load_scenario(name: str) -> dict:
    path = os.path.join(SCENARIO_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


# ── Device Simulation Profiles ──────────────────────────────────────────

def circadian_factor(hour: int) -> float:
    """Base circadian occupancy pattern: low at night, peaks morning/evening."""
    pattern = {
        0: 0.15, 1: 0.10, 2: 0.08, 3: 0.08, 4: 0.08, 5: 0.12,
        6: 0.35, 7: 0.65, 8: 0.75, 9: 0.60, 10: 0.50, 11: 0.50,
        12: 0.55, 13: 0.50, 14: 0.45, 15: 0.45, 16: 0.50, 17: 0.65,
        18: 0.80, 19: 0.90, 20: 0.85, 21: 0.75, 22: 0.50, 23: 0.30,
    }
    return pattern.get(hour, 0.5)


def seasonal_factor(season: str) -> dict:
    """Return multipliers per device type based on season."""
    factors = {
        "summer": {"hvac": 1.8, "fridge": 1.1, "lights": 0.8, "ev_charger": 1.0, "washer_dryer": 1.0, "vampire": 1.0},
        "winter": {"hvac": 1.6, "fridge": 0.9, "lights": 1.3, "ev_charger": 1.0, "washer_dryer": 1.1, "vampire": 1.0},
        "spring": {"hvac": 0.6, "fridge": 1.0, "lights": 1.0, "ev_charger": 1.0, "washer_dryer": 1.0, "vampire": 1.0},
        "autumn": {"hvac": 0.7, "fridge": 1.0, "lights": 1.1, "ev_charger": 1.0, "washer_dryer": 1.0, "vampire": 1.0},
    }
    return factors.get(season, factors["summer"])


def scale_factor(scale: str) -> float:
    """Energy scale multiplier based on home size."""
    return {"small": 0.6, "medium": 1.0, "large": 1.5}.get(scale, 1.0)


def simulate_device_reading(device_type: str, hour: int, minute: int, season: str,
                             scale: str, day_of_week: int, scenario_config: dict) -> float:
    """
    Simulate a single 5-second energy reading (in kWh) for a device.
    Returns kWh consumed in this 5-second interval.
    """
    base_circadian = circadian_factor(hour)
    s_factors = seasonal_factor(season)
    s_mult = s_factors.get(device_type, 1.0)
    sc_mult = scale_factor(scale)

    # Scenario multiplier
    scenario_mult = scenario_config.get("device_multipliers", {}).get(device_type, 1.0)

    # 5-second interval: divide hourly wattage accordingly
    # watts * (5/3600) = kWh per 5 seconds
    interval_hours = 5.0 / 3600.0

    if device_type == "hvac":
        # HVAC cycles on/off. ~60% duty cycle during peak, less off-peak
        duty = base_circadian * s_mult * 0.7
        if random.random() < duty:
            watts = 3500 * sc_mult * scenario_mult
        else:
            watts = 0
        # Add noise
        watts += random.gauss(0, 50) if watts > 0 else 0

    elif device_type == "fridge":
        # Constant ~150W with compressor cycles every ~20 min
        cycle_pos = (minute * 60 + (datetime.now().second % 60)) % 1200
        if cycle_pos < 800:  # Running 2/3 of cycle
            watts = 150 * s_mult * scenario_mult + random.gauss(0, 10)
        else:
            watts = 30 * scenario_mult  # Idle between compressor cycles

    elif device_type == "ev_charger":
        # EV charges 6-8pm weekdays, draws 7.2kW
        is_weekday = day_of_week < 5
        if is_weekday and 18 <= hour < 21 and random.random() < 0.8:
            watts = 7200 * sc_mult * scenario_mult + random.gauss(0, 100)
        elif not is_weekday and 10 <= hour < 14 and random.random() < 0.3:
            watts = 7200 * sc_mult * scenario_mult + random.gauss(0, 100)
        else:
            watts = 0

    elif device_type == "washer_dryer":
        # 2kW burst 2-3x per week, random weekday evenings
        # Simulate ~probability per reading
        is_laundry_time = (18 <= hour <= 21) and (day_of_week in [1, 3, 5])
        if is_laundry_time and random.random() < 0.4:
            watts = 2000 * sc_mult * scenario_mult + random.gauss(0, 100)
        else:
            watts = 0

    elif device_type == "lights":
        # Follow occupancy, low wattage
        watts = 500 * base_circadian * sc_mult * scenario_mult + random.gauss(0, 20)

    elif device_type == "vampire":
        # Always on: router, TV standby, phone chargers
        watts = 80 * scenario_mult + random.gauss(0, 5)

    else:
        watts = 100 * base_circadian * sc_mult + random.gauss(0, 10)

    watts = max(0, watts)
    kwh = watts * interval_hours
    return round(kwh, 6)


def inject_anomalies(session, home_id: int, devices: list, readings_by_device: dict,
                      start_date: datetime, end_date: datetime, num_anomalies: int = 7):
    """Inject realistic anomalies into the data."""
    total_days = (end_date - start_date).days
    anomalies_created = 0

    device_map = {d.id: d for d in devices}

    # 1. HVAC dirty filter: 3-day period with 40% higher consumption
    hvac = next((d for d in devices if d.type == "hvac"), None)
    if hvac:
        spike_start = start_date + timedelta(days=random.randint(10, total_days - 10))
        spike_end = spike_start + timedelta(days=3)
        count = 0
        for reading in readings_by_device.get(hvac.id, []):
            if spike_start <= reading.timestamp <= spike_end:
                reading.kwh_consumed *= 1.4
                count += 1
        if count > 0:
            anomaly = Anomaly(
                home_id=home_id, device_id=hvac.id,
                anomaly_type="spike", severity="warning",
                detected_at=spike_start + timedelta(hours=6),
                description=f"Central AC drawing 40% more power than usual over 3 days. Possible dirty filter or refrigerant leak.",
                estimated_extra_cost=round(count * 0.001 * 0.28, 2),
            )
            session.add(anomaly)
            anomalies_created += 1

    # 2. Midnight vampire drain - device left on
    washer = next((d for d in devices if d.type == "washer_dryer"), None)
    if washer:
        drain_day = start_date + timedelta(days=random.randint(5, total_days - 5))
        for reading in readings_by_device.get(washer.id, []):
            if reading.timestamp.date() == drain_day.date() and 1 <= reading.timestamp.hour <= 5:
                reading.kwh_consumed = 2000 * (5.0 / 3600.0)  # 2kW at night
        anomaly = Anomaly(
            home_id=home_id, device_id=washer.id,
            anomaly_type="vampire_drain", severity="warning",
            detected_at=drain_day.replace(hour=3),
            description=f"Washer/Dryer consuming 2kW at 3AM. Did someone leave it running overnight?",
            estimated_extra_cost=round(2.0 * 4 * 0.12, 2),
        )
        session.add(anomaly)
        anomalies_created += 1

    # 3. Super Bowl party spike
    party_day = start_date + timedelta(days=random.randint(15, total_days - 5))
    for device in devices:
        for reading in readings_by_device.get(device.id, []):
            if reading.timestamp.date() == party_day.date() and 16 <= reading.timestamp.hour <= 23:
                reading.kwh_consumed *= 2.5
    anomaly = Anomaly(
        home_id=home_id,
        anomaly_type="spike", severity="info",
        detected_at=party_day.replace(hour=18),
        description=f"Unusually high consumption across all devices on {party_day.date()}. Party or guests visiting?",
        estimated_extra_cost=round(15 * 0.28, 2),
    )
    session.add(anomaly)
    anomalies_created += 1

    # 4. Peak hour overuse warnings
    anomaly = Anomaly(
        home_id=home_id,
        anomaly_type="peak_overuse", severity="info",
        detected_at=start_date + timedelta(days=random.randint(1, total_days - 1)),
        description="Consistently high consumption during peak hours (2-7pm). Shifting to off-peak could save $12-18/month.",
        estimated_extra_cost=15.0,
    )
    session.add(anomaly)
    anomalies_created += 1

    # 5. Additional random spikes
    for _ in range(min(3, num_anomalies - anomalies_created)):
        device = random.choice(devices)
        spike_day = start_date + timedelta(days=random.randint(1, total_days - 1))
        for reading in readings_by_device.get(device.id, []):
            if reading.timestamp.date() == spike_day.date() and 12 <= reading.timestamp.hour <= 14:
                reading.kwh_consumed *= 3.0
                break
        anomaly = Anomaly(
            home_id=home_id, device_id=device.id,
            anomaly_type="spike", severity="warning",
            detected_at=spike_day.replace(hour=13),
            description=f"Unexpected spike on {device.name} at noon. Check if device is malfunctioning.",
            estimated_extra_cost=round(random.uniform(1, 5), 2),
        )
        session.add(anomaly)
        anomalies_created += 1

    session.commit()
    print(f"  Injected {anomalies_created} anomalies")


def generate_data(home_id: int, days: int = 90, scale: str = "medium",
                   season: str = "summer", inject_anomaly: bool = True,
                   scenario: str = "normal"):
    """Main data generation function."""
    # Initialize DB tables first
    init_db()

    scenario_config = load_scenario(scenario)
    session = SyncSessionLocal()

    try:
        home = session.query(Home).filter(Home.id == home_id).first()
        if not home:
            print(f"Home {home_id} not found. Creating default home...")
            init_db()
            home = session.query(Home).filter(Home.id == home_id).first()
            if not home:
                print("Failed to create home. Exiting.")
                return

        devices = session.query(Device).filter(Device.home_id == home_id).all()
        if not devices:
            print("No devices found for this home. Run init_db first.")
            return

        print(f"Generating {days} days of data for '{home.name}' ({len(devices)} devices)")
        print(f"  Scale: {scale}, Season: {season}, Scenario: {scenario}")

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days)

        readings_by_device = {d.id: [] for d in devices}
        total_readings = 0
        batch = []
        batch_size = 5000

        # Generate readings: every 5 seconds for mock, but for history we sample every 5 minutes
        # to keep DB size manageable
        sample_interval = timedelta(minutes=5)  # 5-minute intervals for historical data
        current_time = start_date

        while current_time < now:
            hour = current_time.hour
            minute = current_time.minute
            day_of_week = current_time.weekday()

            for device in devices:
                kwh = simulate_device_reading(
                    device.type, hour, minute, season, scale,
                    day_of_week, scenario_config,
                )
                # Scale from 5-second to 5-minute interval
                kwh *= 60  # 5 min = 60 x 5 seconds

                voltage = 120 + random.gauss(0, 2)
                power_factor = min(1.0, max(0.8, 0.95 + random.gauss(0, 0.02)))
                current_amps = (kwh * 1000 / (5.0 / 60.0)) / (voltage * power_factor) if voltage > 0 else 0

                reading = EnergyReading(
                    home_id=home_id,
                    device_id=device.id,
                    timestamp=current_time,
                    kwh_consumed=kwh,
                    voltage=round(voltage, 1),
                    current=round(current_amps, 2),
                    power_factor=round(power_factor, 3),
                )
                batch.append(reading)
                readings_by_device[device.id].append(reading)
                total_readings += 1

            if len(batch) >= batch_size:
                session.add_all(batch)
                session.flush()
                progress = ((current_time - start_date).total_seconds() / (now - start_date).total_seconds()) * 100
                print(f"  Progress: {progress:.0f}% ({total_readings:,} readings)")
                batch = []

            current_time += sample_interval

        # Flush remaining
        if batch:
            session.add_all(batch)
            session.flush()

        print(f"  Generated {total_readings:,} readings")

        # Inject anomalies
        if inject_anomaly:
            inject_anomalies(session, home_id, devices, readings_by_device, start_date, now)

        session.commit()
        print(f"Data generation complete!")

        # Run forecaster
        from app.analysis.forecaster import generate_forecast
        print("Running forecast generation...")
        result = generate_forecast(session, home_id)
        if result:
            print(f"  Forecast: {result['predicted_kwh']:.1f} kWh, ${result['predicted_cost']:.2f}")
        else:
            print("  Insufficient data for forecast")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Generate mock energy data for WattWise")
    parser.add_argument("--home-id", type=int, default=1, help="Home ID to generate data for")
    parser.add_argument("--days", type=int, default=90, help="Days of history to generate")
    parser.add_argument("--scale", choices=["small", "medium", "large"], default="medium")
    parser.add_argument("--season", choices=["summer", "winter", "spring", "autumn"], default="summer")
    parser.add_argument("--inject-anomalies", action="store_true", default=True)
    parser.add_argument("--no-anomalies", action="store_true", default=False)
    parser.add_argument("--scenario", choices=["normal", "eco", "wasteful", "vacation"], default="normal")

    args = parser.parse_args()
    inject = args.inject_anomalies and not args.no_anomalies

    generate_data(
        home_id=args.home_id,
        days=args.days,
        scale=args.scale,
        season=args.season,
        inject_anomaly=inject,
        scenario=args.scenario,
    )


if __name__ == "__main__":
    main()
