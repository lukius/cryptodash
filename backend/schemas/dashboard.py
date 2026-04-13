from pydantic import BaseModel


class CompositionSegment(BaseModel):
    network: str
    value_usd: str
    percentage: str


class PortfolioSummary(BaseModel):
    total_value_usd: str | None
    total_btc: str
    total_kas: str
    btc_value_usd: str | None
    kas_value_usd: str | None
    change_24h_usd: str | None
    change_24h_pct: str | None
    btc_price_usd: str | None
    kas_price_usd: str | None
    last_updated: str | None


class HistoryDataPoint(BaseModel):
    timestamp: str
    value: str


class PortfolioHistoryResponse(BaseModel):
    data_points: list[HistoryDataPoint]
    range: str
    unit: str


class WalletHistoryResponse(BaseModel):
    wallet_id: str
    data_points: list[HistoryDataPoint]
    range: str
    unit: str


class PriceHistoryResponse(BaseModel):
    btc: list[HistoryDataPoint]
    kas: list[HistoryDataPoint]
    range: str


class PortfolioComposition(BaseModel):
    segments: list[CompositionSegment]
