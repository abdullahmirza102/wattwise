from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    home_id = Column(Integer, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_month = Column(String(7), nullable=False)  # YYYY-MM format
    predicted_kwh = Column(Float, nullable=False)
    predicted_cost = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=True, default=0.85)
    confidence_lower = Column(Float, nullable=True)
    confidence_upper = Column(Float, nullable=True)
    daily_predictions = Column(String, nullable=True)  # JSON string of daily predictions
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    home = relationship("Home", back_populates="forecasts")
