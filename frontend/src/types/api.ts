export interface AuthStatusResponse {
  account_exists: boolean;
  authenticated: boolean;
  username: string | null;
}

export interface LoginRequest {
  username: string;
  password: string;
  remember_me: boolean;
}

export interface LoginResponse {
  token: string;
  expires_at: string;
}

export interface SetupRequest {
  username: string;
  password: string;
  password_confirm: string;
}

export interface WalletCreate {
  network: "BTC" | "KAS";
  address: string;
  tag: string | null;
}

export interface WalletTagUpdate {
  tag: string;
}

export interface DerivedAddressResponse {
  address: string;
  balance_native: string;
  balance_usd: string | null;
}

export interface WalletResponse {
  id: string;
  network: "BTC" | "KAS";
  address: string;
  tag: string;
  wallet_type: "individual" | "hd";
  extended_key_type: "xpub" | "ypub" | "zpub" | null;
  balance: string | null;
  balance_usd: string | null;
  created_at: string;
  last_updated: string | null;
  warning: string | null;
  history_status: "complete" | "importing" | "failed" | "pending";
  derived_addresses: DerivedAddressResponse[] | null;
  derived_address_count: number | null;
  derived_address_total: number | null;
  hd_loading: boolean;
}

export interface WalletListResponse {
  wallets: WalletResponse[];
  count: number;
  limit: number;
}

export interface PortfolioSummary {
  total_value_usd: string | null;
  total_btc: string;
  total_kas: string;
  btc_value_usd: string | null;
  kas_value_usd: string | null;
  change_24h_usd: string | null;
  change_24h_pct: string | null;
  btc_price_usd: string | null;
  kas_price_usd: string | null;
  last_updated: string | null;
}

export interface HistoryDataPoint {
  timestamp: string;
  value: string;
}

export interface PortfolioHistoryResponse {
  data_points: HistoryDataPoint[];
  range: string;
  unit: string;
}

export interface WalletHistoryResponse {
  wallet_id: string;
  data_points: HistoryDataPoint[];
  range: string;
  unit: string;
}

export interface PriceHistoryResponse {
  btc: HistoryDataPoint[];
  kas: HistoryDataPoint[];
  range: string;
}

export interface CompositionSegment {
  network: string;
  value_usd: string;
  percentage: string;
}

export interface PortfolioComposition {
  segments: CompositionSegment[];
}

export interface SettingsResponse {
  refresh_interval_minutes: number | null;
}

export interface SettingsUpdate {
  refresh_interval_minutes: number | null;
}

export interface TransactionResponse {
  id: string;
  tx_hash: string;
  amount: string;
  balance_after: string;
  block_height: number | null;
  timestamp: string;
}
