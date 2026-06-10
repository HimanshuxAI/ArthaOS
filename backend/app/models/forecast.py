from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    next_month_revenue: Mapped[float] = mapped_column(Float, default=0)
    next_month_expenses: Mapped[float] = mapped_column(Float, default=0)
    expected_profit: Mapped[float] = mapped_column(Float, default=0)
    expected_tax: Mapped[float] = mapped_column(Float, default=0)
    confidence: Mapped[str] = mapped_column(String(40), default="low")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User")
