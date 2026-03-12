"""
Live Mock Data Streamer
Inserts a new energy reading every 5 seconds per device.
Designed to run as a Docker service feeding the WebSocket live gauge.
"""
import argparse
import os
import sys
import time
import random
import logging
from datetime import datetime, timezone

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import SyncSessionLocal
from app.core.init_db import init_db
from app.models import Home, Device, EnergyReading

logging.basicConfig(level=logging.INFO, format="%(asctime)s [STREAMER] %(message)s")
logger = logging.getLogger(__name__)


def circadian_factor(hour: int) -> float:
    pattern = {
        0: 0.15, 1: 0.10, 2: 0.08, 3: 0.08, 4: 0.08, 5: 0.12,
        6: 0.35, 7: 0.65, 8: 0.75, 9: 0.60, 10: 0.50, 11: 0.50,
        12: 0.55, 13: 0.50, 14: 0.45, 15: 0.45, 16: 0.50, 17: 0.65,
        18: 0.80, 19: 0.90, 20: 0.85, 21: 0.75, 22: 0.50, 23: 0.30,
    }
    return pattern.get(hour, 0.5)


def simulate_live_reading(device_type: str, hour: int) -> float:
    """Simulate a 5-second energy reading in kWh."""
    base = circadian_factor(hour)
    interval_hours = 5.0 / 3600.0

    if device_type == "hvac":
        duty = base * 0.7
        watts = 3500 if random.random() < duty else 0
        watts += random.gauss(0, 50) if watts > 0 else 0
    elif device_type == "fridge":
        watts = 150 if random.random() < 0.67 else 30
        watts += random.gauss(0, 10)
    elif device_type == "ev_charger":
        is_evening = 18 <= hour < 21
        watts = 7200 if is_evening and random.random() < 0.7 else 0
    elif device_type == "washer_dryer":
        is_laundry = 18 <= hour <= 21 and random.random() < 0.15
        watts = 2000 if is_laundry else 0
    elif device_type == "lights":
        watts = 500 * base + random.gauss(0, 20)
    elif device_type == "vampire":
        watts = 80 + random.gauss(0, 5)
    else:
        watts = 100 * base

    return round(max(0, watts * interval_hours), 6)


def stream(home_id: int, interval: int = 5, error_rate: float = 0.05):
    """Main streaming loop."""
    init_db()

    session = SyncSessionLocal()
    home = session.query(Home).filter(Home.id == home_id).first()
    if not home:
        logger.error(f"Home {home_id} not found")
        session.close()
        return

    devices = session.query(Device).filter(Device.home_id == home_id).all()
    if not devices:
        logger.error(f"No devices for home {home_id}")
        session.close()
        return

    logger.info(f"Starting live stream for '{home.name}' ({len(devices)} devices) every {interval}s")
    session.close()

    while True:
        try:
            session = SyncSessionLocal()
            now = datetime.now(timezone.utc)
            hour = now.hour
            total_watts = 0

            for device in devices:
                # Inject error spike occasionally
                if random.random() < error_rate:
                    kwh = simulate_live_reading(device.type, hour) * random.uniform(3, 8)
                else:
                    kwh = simulate_live_reading(device.type, hour)

                voltage = 120 + random.gauss(0, 2)
                power_factor = min(1.0, max(0.8, 0.95 + random.gauss(0, 0.02)))
                watts = kwh * (3600 / 5)  # Convert back to watts for logging
                total_watts += watts * 1000

                reading = EnergyReading(
                    home_id=home_id,
                    device_id=device.id,
                    timestamp=now,
                    kwh_consumed=kwh,
                    voltage=round(voltage, 1),
                    current=round(watts * 1000 / max(voltage, 1), 2),
                    power_factor=round(power_factor, 3),
                )
                session.add(reading)

            session.commit()
            logger.info(f"Streamed {len(devices)} device readings | Home total: {total_watts/1000:.1f}W")
            session.close()

        except Exception as e:
            logger.error(f"Stream error: {e}")
            try:
                session.close()
            except Exception:
                pass

        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="WattWise Live Mock Data Streamer")
    parser.add_argument("--home-id", type=int, default=1)
    parser.add_argument("--interval", type=int, default=5, help="Seconds between readings")
    parser.add_argument("--error-rate", type=float, default=0.05, help="Probability of anomaly injection per reading")
    args = parser.parse_args()

    stream(args.home_id, args.interval, args.error_rate)


if __name__ == "__main__":
    main()
