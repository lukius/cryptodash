from typing import Literal

from pydantic import BaseModel, Field


class WalletCreate(BaseModel):
    network: Literal["BTC", "KAS"]
    address: str = Field(min_length=1)
    tag: str | None = Field(default=None)


class WalletTagUpdate(BaseModel):
    tag: str = Field(min_length=1)


class DerivedAddressResponse(BaseModel):
    address: str
    balance_native: str  # BTC as Decimal string
    balance_usd: str | None  # USD value, None if no price available


class WalletResponse(BaseModel):
    id: str
    network: str
    address: str
    tag: str
    wallet_type: str  # "individual" or "hd"
    extended_key_type: str | None  # "xpub", "ypub", "zpub", or None
    balance: str | None  # Decimal as string, None if pending
    balance_usd: str | None
    created_at: str
    last_updated: str | None
    warning: str | None  # e.g. "Last update failed."
    history_status: str  # "complete", "importing", "failed", "pending"
    # HD wallet fields (None for individual wallets)
    derived_addresses: list[DerivedAddressResponse] | None = None
    derived_address_count: int | None = None  # total stored (≤200)
    derived_address_total: int | None = None  # raw API total (may be >200)
    hd_loading: bool = False  # True while first fetch is in progress


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
