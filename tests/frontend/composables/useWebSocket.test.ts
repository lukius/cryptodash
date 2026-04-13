import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";

// ---- Shared mock state (closed over by vi.doMock factories) ----
const mockFetchSummary = vi.fn().mockResolvedValue(undefined);
const mockFetchComposition = vi.fn().mockResolvedValue(undefined);
const mockFetchPortfolioHistory = vi.fn().mockResolvedValue(undefined);
const mockFetchPriceHistory = vi.fn().mockResolvedValue(undefined);
const mockFetchWallets = vi.fn().mockResolvedValue(undefined);
const mockFetchSettings = vi.fn().mockResolvedValue(undefined);

const mockDashboard = {
  isRefreshing: false,
  selectedRange: "30d",
  fetchSummary: mockFetchSummary,
  fetchComposition: mockFetchComposition,
  fetchPortfolioHistory: mockFetchPortfolioHistory,
  fetchPriceHistory: mockFetchPriceHistory,
};

// Pinia exposes state as plain values (auto-unwrapped refs).
const mockWallets = {
  wallets: [] as Array<{ id: string; history_status: string }>,
  fetchWallets: mockFetchWallets,
};

const mockSettings = {
  fetchSettings: mockFetchSettings,
};

let mockToken: string | null = "test-token-123";
let mockIsAuthenticated = true;

// ---- WebSocket mock ----
type WsEventHandler = (event: MessageEvent | CloseEvent | Event) => void;

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: WsEventHandler | null = null;
  onmessage: WsEventHandler | null = null;
  onclose: WsEventHandler | null = null;
  onerror: WsEventHandler | null = null;

  static instances: MockWebSocket[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(_data: string) {}

  close() {
    this.readyState = MockWebSocket.CLOSED;
    const event = { code: 1000, reason: "closed", wasClean: true } as CloseEvent;
    this.onclose?.(event);
  }

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event("open"));
  }

  simulateMessage(data: unknown) {
    const event = { data: JSON.stringify(data) } as MessageEvent;
    this.onmessage?.(event);
  }

  simulateClose(code = 1006) {
    this.readyState = MockWebSocket.CLOSED;
    const event = { code, reason: "", wasClean: false } as CloseEvent;
    this.onclose?.(event);
  }
}

// ---- Helpers ----

async function importComposable() {
  const mod = await import("@/composables/useWebSocket");
  return mod.useWebSocket;
}

// ---- Tests ----

describe("useWebSocket", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    // Re-register mocks before each module reset so the fresh module sees them.
    vi.doMock("@/stores/dashboard", () => ({
      useDashboardStore: () => mockDashboard,
    }));
    vi.doMock("@/stores/wallets", () => ({
      useWalletsStore: () => mockWallets,
    }));
    vi.doMock("@/stores/settings", () => ({
      useSettingsStore: () => mockSettings,
    }));
    vi.doMock("@/stores/auth", () => ({
      useAuthStore: () => ({
        get token() { return mockToken; },
        get isAuthenticated() { return mockIsAuthenticated; },
      }),
    }));
    // Reset module cache so each test gets a fresh singleton.
    vi.resetModules();
    MockWebSocket.instances = [];
    mockDashboard.isRefreshing = false;
    mockWallets.wallets = [];
    mockToken = "test-token-123";
    mockIsAuthenticated = true;
    vi.stubGlobal("WebSocket", MockWebSocket);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("connects with the auth token in the URL", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toContain("token=test-token-123");
    expect(MockWebSocket.instances[0].url).toContain("/api/ws");
  });

  it("sets isConnected=true on open, false on close", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();

    const instance = MockWebSocket.instances[0];
    expect(ws.isConnected.value).toBe(false);

    instance.simulateOpen();
    expect(ws.isConnected.value).toBe(true);

    instance.simulateClose(1000);
    expect(ws.isConnected.value).toBe(false);
  });

  it("dispatches refresh:started → sets dashboard.isRefreshing=true", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();

    MockWebSocket.instances[0].simulateMessage({
      event: "refresh:started",
      data: {},
      timestamp: "2026-01-01T00:00:00Z",
    });

    expect(mockDashboard.isRefreshing).toBe(true);
  });

  it("dispatches refresh:completed → calls fetchSummary, sets isRefreshing=false, does NOT call fetchComposition/history", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();

    mockDashboard.isRefreshing = true;
    MockWebSocket.instances[0].simulateMessage({
      event: "refresh:completed",
      data: { success_count: 2, failure_count: 0, timestamp: "2026-01-01T00:00:00Z" },
      timestamp: "2026-01-01T00:00:00Z",
    });

    expect(mockFetchSummary).toHaveBeenCalled();
    expect(mockDashboard.isRefreshing).toBe(false);
    expect(mockFetchComposition).not.toHaveBeenCalled();
    expect(mockFetchPortfolioHistory).not.toHaveBeenCalled();
    expect(mockFetchPriceHistory).not.toHaveBeenCalled();
  });

  it("dispatches wallet:added → calls wallets.fetchWallets", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();

    MockWebSocket.instances[0].simulateMessage({
      event: "wallet:added",
      data: { wallet_id: "wallet-abc" },
      timestamp: "2026-01-01T00:00:00Z",
    });

    expect(mockFetchWallets).toHaveBeenCalled();
  });

  it("dispatches wallet:removed → calls wallets.fetchWallets", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();

    MockWebSocket.instances[0].simulateMessage({
      event: "wallet:removed",
      data: { wallet_id: "wallet-abc" },
      timestamp: "2026-01-01T00:00:00Z",
    });

    expect(mockFetchWallets).toHaveBeenCalled();
  });

  it("dispatches wallet:updated → calls wallets.fetchWallets", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();

    MockWebSocket.instances[0].simulateMessage({
      event: "wallet:updated",
      data: { wallet_id: "wallet-abc" },
      timestamp: "2026-01-01T00:00:00Z",
    });

    expect(mockFetchWallets).toHaveBeenCalled();
  });

  it("dispatches wallet:history:progress → updates wallet history_status in store", async () => {
    const useWebSocket = await importComposable();
    mockWallets.wallets = [{ id: "wallet-xyz", history_status: "pending" }];
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();

    MockWebSocket.instances[0].simulateMessage({
      event: "wallet:history:progress",
      data: { wallet_id: "wallet-xyz", status: "importing", progress_pct: 42 },
      timestamp: "2026-01-01T00:00:00Z",
    });

    expect(mockWallets.wallets[0].history_status).toBe("importing");
  });

  it("dispatches wallet:history:completed → calls wallets.fetchWallets", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();

    MockWebSocket.instances[0].simulateMessage({
      event: "wallet:history:completed",
      data: { wallet_id: "wallet-abc", partial: false },
      timestamp: "2026-01-01T00:00:00Z",
    });

    expect(mockFetchWallets).toHaveBeenCalled();
  });

  it("dispatches settings:updated → calls settings.fetchSettings", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();

    MockWebSocket.instances[0].simulateMessage({
      event: "settings:updated",
      data: { key: "refresh_interval_minutes", value: "30" },
      timestamp: "2026-01-01T00:00:00Z",
    });

    expect(mockFetchSettings).toHaveBeenCalled();
  });

  it("auto-reconnects after unexpected disconnect with setTimeout", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();

    const setTimeoutSpy = vi.spyOn(globalThis, "setTimeout");
    MockWebSocket.instances[0].simulateClose(1006);

    expect(setTimeoutSpy).toHaveBeenCalled();
  });

  it("does not reconnect after calling disconnect()", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();

    ws.disconnect();
    const countBefore = MockWebSocket.instances.length;

    vi.advanceTimersByTime(5000);
    expect(MockWebSocket.instances.length).toBe(countBefore);
  });

  it("disconnect() stops reconnect and sets isConnected=false", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();
    expect(ws.isConnected.value).toBe(true);

    ws.disconnect();
    expect(ws.isConnected.value).toBe(false);
  });

  it("does not reconnect if token is null (logged out)", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();

    mockToken = null;
    mockIsAuthenticated = false;
    MockWebSocket.instances[0].simulateClose(1006);

    vi.advanceTimersByTime(5000);
    expect(MockWebSocket.instances.length).toBe(1);
  });

  it("URL-encodes the token", async () => {
    mockToken = "token+with/special=chars";
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();

    expect(MockWebSocket.instances[0].url).toContain(
      "token=token%2Bwith%2Fspecial%3Dchars",
    );
  });

  it("exponential backoff: 1000ms → 2000ms → 4000ms → 8000ms → 16000ms → 30000ms (cap)", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    MockWebSocket.instances[0].simulateOpen();

    const delays: number[] = [];
    const origSetTimeout = globalThis.setTimeout;
    vi.spyOn(globalThis, "setTimeout").mockImplementation(
      (fn: TimerHandler, delay?: number, ...args: unknown[]) => {
        if (typeof delay === "number") delays.push(delay);
        return (origSetTimeout as typeof setTimeout)(fn as () => void, delay, ...args);
      },
    );

    // Simulate 6 consecutive failures — never call simulateOpen so backoff
    // does not reset to 1000ms between cycles.
    const expectedDelays = [1000, 2000, 4000, 8000, 16000, 30000];
    for (const expected of expectedDelays) {
      MockWebSocket.instances[MockWebSocket.instances.length - 1].simulateClose(1006);
      vi.advanceTimersByTime(expected);
    }

    expect(delays).toEqual(expectedDelays);
  });

  it("sends ping every 30s after connect", async () => {
    const useWebSocket = await importComposable();
    const ws = useWebSocket();
    ws.connect();
    const instance = MockWebSocket.instances[0];
    const sendSpy = vi.spyOn(instance, "send");
    instance.simulateOpen();

    vi.advanceTimersByTime(30_000);
    expect(sendSpy).toHaveBeenCalledWith("ping");

    vi.advanceTimersByTime(30_000);
    expect(sendSpy).toHaveBeenCalledTimes(2);
  });
});
