from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    home_id = Column(Integer, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    reading_id = Column(Integer, ForeignKey("energy_readings.id", ondelete="SET NULL"), nullable=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    anomaly_type = Column(String(100), nullable=False)  # spike, vampire_drain, flatline, peak_overuse
    severity = Column(String(50), nullable=False, default="warning")  # critical, warning, info
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(Text, nullable=True)
    estimated_extra_cost = Column(Float, nullable=True, default=0.0)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    home = relationship("Home", back_populates="anomalies")
