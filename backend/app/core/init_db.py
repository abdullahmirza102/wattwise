"""Initialize database tables and seed default data."""
import sys
import os

# Add parent paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import sync_engine, SyncSessionLocal, Base
from app.models import Home, Device, EnergyReading, Anomaly, Forecast


def init_db():
    """Create all tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=sync_engine)
    print("Tables created successfully.")

    # Seed default home and devices if empty
    session = SyncSessionLocal()
    try:
        home_count = session.query(Home).count()
        if home_count == 0:
            print("Seeding default home and devices...")
            home = Home(
                name="Demo Home",
                location="Austin, TX",
                size_sqft=2200,
                num_occupants=4,
                tariff_rate_per_kwh=0.18,
            )
            session.add(home)
            session.flush()

            devices = [
                Device(home_id=home.id, name="Central AC", type="hvac", wattage_rated=3500, is_active=True),
                Device(home_id=home.id, name="Refrigerator", type="fridge", wattage_rated=150, is_active=True),
                Device(home_id=home.id, name="EV Charger", type="ev_charger", wattage_rated=7200, is_active=True),
                Device(home_id=home.id, name="Washer/Dryer", type="washer_dryer", wattage_rated=2000, is_active=True),
                Device(home_id=home.id, name="Lighting", type="lights", wattage_rated=500, is_active=True),
                Device(home_id=home.id, name="Always-On (Router, Standby)", type="vampire", wattage_rated=80, is_active=True),
            ]
            session.add_all(devices)
            session.commit()
            print(f"Seeded home '{home.name}' with {len(devices)} devices.")
        else:
            print(f"Database already has {home_count} home(s). Skipping seed.")
    except Exception as e:
        session.rollback()
        print(f"Error seeding: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
