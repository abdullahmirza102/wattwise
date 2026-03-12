from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class EnergyReading(Base):
    __tablename__ = "energy_readings"

    id = Column(Integer, primary_key=True, index=True)
    home_id = Column(Integer, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    kwh_consumed = Column(Float, nullable=False)
    voltage = Column(Float, nullable=True, default=120.0)
    current = Column(Float, nullable=True)
    power_factor = Column(Float, nullable=True, default=0.95)

    home = relationship("Home", back_populates="readings")
    device = relationship("Device", back_populates="readings")

    __table_args__ = (
        Index("ix_readings_home_timestamp", "home_id", "timestamp"),
        Index("ix_readings_device_timestamp", "device_id", "timestamp"),
        Index("ix_readings_timestamp", "timestamp"),
    )
