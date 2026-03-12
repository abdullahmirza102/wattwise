"""Celery application configuration."""
import logging
from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

celery_app = Celery(
    "wattwise",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "detect-anomalies-every-15-min": {
        "task": "app.core.celery_app.run_anomaly_detection",
        "schedule": crontab(minute="*/15"),
    },
    "generate-forecast-daily-midnight": {
        "task": "app.core.celery_app.run_forecast",
        "schedule": crontab(hour=0, minute=0),
    },
}


@celery_app.task(name="app.core.celery_app.run_anomaly_detection")
def run_anomaly_detection():
    """Run anomaly detection for all homes."""
    from app.core.database import SyncSessionLocal
    from app.models import Home
    from app.analysis.anomaly_detector import detect_anomalies

    session = SyncSessionLocal()
    try:
        homes = session.query(Home).all()
        total_anomalies = 0
        for home in homes:
            results = detect_anomalies(session, home.id)
            total_anomalies += len(results)
        logger.info(f"Anomaly detection complete: {total_anomalies} new anomalies across {len(homes)} homes")
        return {"homes_scanned": len(homes), "anomalies_detected": total_anomalies}
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        raise
    finally:
        session.close()


@celery_app.task(name="app.core.celery_app.run_forecast")
def run_forecast():
    """Generate forecasts for all homes."""
    from app.core.database import SyncSessionLocal
    from app.models import Home
    from app.analysis.forecaster import generate_forecast

    session = SyncSessionLocal()
    try:
        homes = session.query(Home).all()
        forecasts = 0
        for home in homes:
            result = generate_forecast(session, home.id)
            if result:
                forecasts += 1
        logger.info(f"Forecasting complete: {forecasts} forecasts generated for {len(homes)} homes")
        return {"homes_scanned": len(homes), "forecasts_generated": forecasts}
    except Exception as e:
        logger.error(f"Forecasting failed: {e}")
        raise
    finally:
        session.close()
