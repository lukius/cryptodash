from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (Index("ix_ps_coin_timestamp", "coin", "timestamp"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    coin: Mapped[str] = mapped_column(String(3), nullable=False)
    price_usd: Mapped[str] = mapped_column(String(40), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
