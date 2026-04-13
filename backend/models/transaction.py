from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.wallet import Wallet


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("wallet_id", "tx_hash", name="uq_tx_wallet_hash"),
        Index("ix_tx_wallet_height", "wallet_id", "block_height"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    wallet_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wallets.id"), nullable=False
    )
    tx_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[str] = mapped_column(String(40), nullable=False)
    balance_after: Mapped[str | None] = mapped_column(String(40))
    block_height: Mapped[int | None] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    wallet: Mapped["Wallet"] = relationship(back_populates="transactions")
