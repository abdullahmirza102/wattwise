from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Home(Base):
    __tablename__ = "homes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    size_sqft = Column(Integer, nullable=True)
    num_occupants = Column(Integer, default=2)
    tariff_rate_per_kwh = Column(Float, default=0.18)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    devices = relationship("Device", back_populates="home", cascade="all, delete-orphan")
    readings = relationship("EnergyReading", back_populates="home", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="home", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="home", cascade="all, delete-orphan")
