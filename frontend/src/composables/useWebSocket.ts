import { ref } from "vue";
import type { Ref } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useDashboardStore } from "@/stores/dashboard";
import { useWalletsStore } from "@/stores/wallets";
import { useSettingsStore } from "@/stores/settings";
import type { WebSocketEvent } from "@/types/websocket";
import type { WalletResponse } from "@/types/api";

const PING_INTERVAL_MS = 30_000;
const INITIAL_BACKOFF_MS = 1_000;
const MAX_BACKOFF_MS = 30_000;

let socket: WebSocket | null = null;
let pingTimer: ReturnType<typeof setInterval> | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let intentionalClose = false;
let backoffMs = INITIAL_BACKOFF_MS;

const isConnected: Ref<boolean> = ref(false);

function buildUrl(token: string): string {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${location.host}/api/ws?token=${encodeURIComponent(token)}`;
}

function clearPingTimer() {
  if (pingTimer !== null) {
    clearInterval(pingTimer);
    pingTimer = null;
  }
}

function clearReconnectTimer() {
  if (reconnectTimer !== null) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

function dispatchEvent(event: WebSocketEvent) {
  const dashboard = useDashboardStore();
  const wallets = useWalletsStore();
  const settings = useSettingsStore();

  switch (event.event) {
    case "refresh:started":
      dashboard.isRefreshing = true;
      break;

    case "refresh:completed":
      dashboard.isRefreshing = false;
      void dashboard.fetchSummary();
      break;

    case "wallet:added":
    case "wallet:removed":
    case "wallet:updated":
      void wallets.fetchWallets();
      void dashboard.fetchSummary();
      void dashboard.fetchComposition();
      break;

    case "wallet:history:progress": {
      const idx = wallets.wallets.findIndex(
        (w) => w.id === event.data.wallet_id,
      );
      if (idx !== -1) {
        wallets.wallets[idx] = {
          ...wallets.wallets[idx],
          history_status: event.data.status as WalletResponse["history_status"],
        };
      }
      break;
    }

    case "wallet:history:completed":
      void wallets.fetchWallets();
      break;

    case "settings:updated":
      void settings.fetchSettings();
      break;
  }
}

function scheduleReconnect() {
  const auth = useAuthStore();
  if (!auth.isAuthenticated || auth.token === null) return;

  clearReconnectTimer();
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    const auth = useAuthStore();
    if (!auth.isAuthenticated || auth.token === null) return;
    openSocket(auth.token as string);
  }, backoffMs);

  backoffMs = Math.min(backoffMs * 2, MAX_BACKOFF_MS);
}

function openSocket(token: string) {
  const url = buildUrl(token);
  socket = new WebSocket(url);

  socket.onopen = () => {
    isConnected.value = true;
    backoffMs = INITIAL_BACKOFF_MS;

    clearPingTimer();
    pingTimer = setInterval(() => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send("ping");
      }
    }, PING_INTERVAL_MS);
  };

  socket.onmessage = (event: MessageEvent) => {
    if (event.data === "pong") return;
    try {
      const parsed = JSON.parse(event.data as string) as WebSocketEvent;
      dispatchEvent(parsed);
    } catch {
      // ignore malformed messages
    }
  };

  socket.onclose = (event: CloseEvent) => {
    isConnected.value = false;
    clearPingTimer();
    socket = null;

    if (!intentionalClose && event.code !== 1000) {
      scheduleReconnect();
    }
  };

  socket.onerror = () => {
    // onclose will fire after onerror, which will trigger reconnect
  };
}

function connect(): void {
  const auth = useAuthStore();
  if (!auth.token) return;
  intentionalClose = false;
  backoffMs = INITIAL_BACKOFF_MS;
  openSocket(auth.token as string);
}

function disconnect(): void {
  intentionalClose = true;
  clearPingTimer();
  clearReconnectTimer();
  if (socket) {
    socket.close();
    socket = null;
  }
  isConnected.value = false;
}

export function useWebSocket() {
  return { isConnected, connect, disconnect };
}
