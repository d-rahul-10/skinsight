from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from base import Base


class AnalysisRecord(Base):
    __tablename__ = "analysis_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    predicted_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_status: Mapped[str] = mapped_column(String(24), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(600), nullable=True)

    @property
    def image_retained(self) -> bool:
        return self.image_path is not None
