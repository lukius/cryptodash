from typing import Literal

from pydantic import BaseModel, Field


class WalletCreate(BaseModel):
    network: Literal["BTC", "KAS"]
    address: str = Field(min_length=1)
    tag: str | None = Field(default=None)


class WalletTagUpdate(BaseModel):
    tag: str = Field(min_length=1)


class WalletResponse(BaseModel):
    id: str
    network: str
    address: str
    tag: str
    balance: str | None  # Decimal as string, None if pending
    balance_usd: str | None
    created_at: str
    last_updated: str | None
    warning: str | None  # e.g. "Last update failed."
    history_status: str  # "complete", "importing", "failed", "pending"


class WalletListResponse(BaseModel):
    wallets: list[WalletResponse]
    count: int
    limit: int = 50


class TransactionResponse(BaseModel):
    id: str
    tx_hash: str
    amount: str
    balance_after: str | None
    block_height: int | None
    timestamp: str
