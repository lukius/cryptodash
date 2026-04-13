from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.wallet import Wallet


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"
    __table_args__ = (Index("ix_bs_wallet_timestamp", "wallet_id", "timestamp"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    wallet_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wallets.id"), nullable=False
    )
    balance: Mapped[str] = mapped_column(String(40), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)

    wallet: Mapped["Wallet"] = relationship(back_populates="balance_snapshots")
