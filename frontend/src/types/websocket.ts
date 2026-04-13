export interface RefreshStarted {
  event: "refresh:started";
  data: Record<string, never>;
  timestamp: string;
}

export interface RefreshCompleted {
  event: "refresh:completed";
  data: {
    success_count: number;
    failure_count: number;
    timestamp: string;
  };
  timestamp: string;
}

export interface WalletAdded {
  event: "wallet:added";
  data: {
    wallet_id: string;
  };
  timestamp: string;
}

export interface WalletRemoved {
  event: "wallet:removed";
  data: {
    wallet_id: string;
  };
  timestamp: string;
}

export interface WalletUpdated {
  event: "wallet:updated";
  data: {
    wallet_id: string;
  };
  timestamp: string;
}

export interface WalletHistoryProgress {
  event: "wallet:history:progress";
  data: {
    wallet_id: string;
    status: string;
    progress_pct: number | null;
  };
  timestamp: string;
}

export interface WalletHistoryCompleted {
  event: "wallet:history:completed";
  data: {
    wallet_id: string;
    partial: boolean;
  };
  timestamp: string;
}

export interface SettingsUpdated {
  event: "settings:updated";
  data: {
    key: string;
    value: string;
  };
  timestamp: string;
}

export type WebSocketEvent =
  | RefreshStarted
  | RefreshCompleted
  | WalletAdded
  | WalletRemoved
  | WalletUpdated
  | WalletHistoryProgress
  | WalletHistoryCompleted
  | SettingsUpdated;
