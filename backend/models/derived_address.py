from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.wallet import Wallet


class DerivedAddress(Base):
    __tablename__ = "derived_addresses"
    __table_args__ = (
        UniqueConstraint("wallet_id", "address", name="uq_derived_wallet_address"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    wallet_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("wallets.id"), nullable=False
    )
    address: Mapped[str] = mapped_column(String(64), nullable=False)
    current_balance_native: Mapped[str] = mapped_column(String(40), nullable=False)
    balance_sat: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    wallet: Mapped["Wallet"] = relationship(back_populates="derived_addresses")
