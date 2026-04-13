import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useWalletsStore } from "@/stores/wallets";

vi.mock("@/composables/useApi", () => ({
  useApi: vi.fn(),
  ApiError: class ApiError extends Error {
    readonly status: number;
    readonly detail: string;
    constructor(status: number, detail: string) {
      super(detail);
      this.name = "ApiError";
      this.status = status;
      this.detail = detail;
    }
  },
}));

vi.mock("@/router", () => ({
  default: { push: vi.fn() },
}));

import { useApi, ApiError } from "@/composables/useApi";

function makeApi(overrides: Record<string, unknown> = {}) {
  return {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    ...overrides,
  };
}

function makeWallet(overrides: Record<string, unknown> = {}) {
  return {
    id: "wallet-1",
    network: "BTC",
    address: "1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf Ne",
    tag: "BTC Wallet #1",
    balance: "1.5",
    balance_usd: "90000.00",
    created_at: "2026-01-01T00:00:00Z",
    last_updated: "2026-01-01T01:00:00Z",
    warning: null,
    history_status: "complete",
    ...overrides,
  };
}

describe("useWalletsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  // ---- Initial state ----

  it("starts with empty wallets array", () => {
    const store = useWalletsStore();
    expect(store.wallets).toEqual([]);
  });

  it("starts with isLoading=false", () => {
    const store = useWalletsStore();
    expect(store.isLoading).toBe(false);
  });

  it("starts with error=null", () => {
    const store = useWalletsStore();
    expect(store.error).toBeNull();
  });

  it("has limit=50", () => {
    const store = useWalletsStore();
    expect(store.limit).toBe(50);
  });

  // ---- Getters ----

  it("count returns wallets.length", () => {
    const store = useWalletsStore();
    expect(store.count).toBe(0);
    store.wallets = [makeWallet(), makeWallet({ id: "wallet-2" })];
    expect(store.count).toBe(2);
  });

  it("isLimitReached is false when under 50", () => {
    const store = useWalletsStore();
    store.wallets = Array.from({ length: 49 }, (_, i) =>
      makeWallet({ id: `w${i}` }),
    );
    expect(store.isLimitReached).toBe(false);
  });

  it("isLimitReached is true when at 50", () => {
    const store = useWalletsStore();
    store.wallets = Array.from({ length: 50 }, (_, i) =>
      makeWallet({ id: `w${i}` }),
    );
    expect(store.isLimitReached).toBe(true);
  });

  it("btcWallets returns only BTC wallets", () => {
    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "btc-1", network: "BTC" }),
      makeWallet({ id: "kas-1", network: "KAS" }),
    ];
    expect(store.btcWallets).toHaveLength(1);
    expect(store.btcWallets[0].network).toBe("BTC");
  });

  it("kasWallets returns only KAS wallets", () => {
    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "btc-1", network: "BTC" }),
      makeWallet({ id: "kas-1", network: "KAS" }),
    ];
    expect(store.kasWallets).toHaveLength(1);
    expect(store.kasWallets[0].network).toBe("KAS");
  });

  it("totalBtcBalance sums BTC wallets only", () => {
    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "btc-1", network: "BTC", balance: "1.5" }),
      makeWallet({ id: "btc-2", network: "BTC", balance: "0.5" }),
      makeWallet({ id: "kas-1", network: "KAS", balance: "1000" }),
    ];
    expect(store.totalBtcBalance).toBeCloseTo(2.0);
  });

  it("totalBtcBalance ignores null balances", () => {
    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "btc-1", network: "BTC", balance: "1.0" }),
      makeWallet({ id: "btc-2", network: "BTC", balance: null }),
    ];
    expect(store.totalBtcBalance).toBeCloseTo(1.0);
  });

  it("totalKasBalance sums KAS wallets only", () => {
    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "kas-1", network: "KAS", balance: "5000" }),
      makeWallet({ id: "kas-2", network: "KAS", balance: "3000" }),
      makeWallet({ id: "btc-1", network: "BTC", balance: "1.0" }),
    ];
    expect(store.totalKasBalance).toBeCloseTo(8000);
  });

  it("walletCount returns the same as count", () => {
    const store = useWalletsStore();
    store.wallets = [makeWallet()];
    expect(store.walletCount).toBe(1);
  });

  it("getWalletById returns matching wallet", () => {
    const store = useWalletsStore();
    const w = makeWallet({ id: "abc-123" });
    store.wallets = [w];
    expect(store.getWalletById("abc-123")).toEqual(w);
  });

  it("getWalletById returns null when not found", () => {
    const store = useWalletsStore();
    store.wallets = [makeWallet({ id: "wallet-1" })];
    expect(store.getWalletById("nonexistent")).toBeNull();
  });

  // ---- fetchWallets ----

  it("fetchWallets() populates the wallets state", async () => {
    const w1 = makeWallet({ id: "w1" });
    const w2 = makeWallet({ id: "w2", network: "KAS" });
    const api = makeApi({
      get: vi.fn().mockResolvedValue({ wallets: [w1, w2], count: 2, limit: 50 }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    await store.fetchWallets();

    expect(api.get).toHaveBeenCalledWith("/wallets/");
    expect(store.wallets).toHaveLength(2);
    expect(store.wallets[0].id).toBe("w1");
    expect(store.wallets[1].id).toBe("w2");
    expect(store.isLoading).toBe(false);
    expect(store.error).toBeNull();
  });

  it("fetchWallets() sets error state on failure", async () => {
    const api = makeApi({
      get: vi.fn().mockRejectedValue(new ApiError(500, "Internal Server Error")),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    await store.fetchWallets();

    expect(store.error).toBe("Internal Server Error");
    expect(store.isLoading).toBe(false);
  });

  // ---- addWallet ----

  it("addWallet() appends to wallets on success", async () => {
    const newWallet = makeWallet({ id: "new-w" });
    const api = makeApi({
      post: vi.fn().mockResolvedValue(newWallet),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    const result = await store.addWallet({ network: "BTC", address: "1A1zP1...", tag: null });

    expect(api.post).toHaveBeenCalledWith("/wallets/", {
      network: "BTC",
      address: "1A1zP1...",
      tag: null,
    });
    expect(store.wallets).toHaveLength(1);
    expect(store.wallets[0].id).toBe("new-w");
    expect(result).toEqual(newWallet);
  });

  it("addWallet() throws ApiError on 400 and sets error state", async () => {
    const err = new ApiError(400, "This wallet address is already being tracked.");
    const api = makeApi({
      post: vi.fn().mockRejectedValue(err),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    await expect(
      store.addWallet({ network: "BTC", address: "dup", tag: null }),
    ).rejects.toThrow("This wallet address is already being tracked.");
    expect(store.error).toBe("This wallet address is already being tracked.");
  });

  it("addWallet() throws ApiError on 409 (limit reached)", async () => {
    const err = new ApiError(409, "Wallet limit reached (50). Remove a wallet to add a new one.");
    const api = makeApi({
      post: vi.fn().mockRejectedValue(err),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    await expect(
      store.addWallet({ network: "BTC", address: "x", tag: null }),
    ).rejects.toThrow();
    expect(store.error).toContain("Wallet limit reached");
  });

  // ---- updateTag ----

  it("updateTag() updates the tag in local state on success", async () => {
    const original = makeWallet({ id: "w1", tag: "Old Tag" });
    const updated = { ...original, tag: "New Tag" };
    const api = makeApi({
      patch: vi.fn().mockResolvedValue(updated),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    store.wallets = [original];
    await store.updateTag("w1", "New Tag");

    expect(api.patch).toHaveBeenCalledWith("/wallets/w1", { tag: "New Tag" });
    expect(store.wallets[0].tag).toBe("New Tag");
  });

  it("updateTag() throws ApiError on duplicate tag and sets error", async () => {
    const err = new ApiError(400, "A wallet with this tag already exists.");
    const api = makeApi({
      patch: vi.fn().mockRejectedValue(err),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    store.wallets = [makeWallet({ id: "w1", tag: "Original" })];
    await expect(store.updateTag("w1", "Duplicate")).rejects.toThrow(
      "A wallet with this tag already exists.",
    );
    expect(store.error).toBe("A wallet with this tag already exists.");
    expect(store.wallets[0].tag).toBe("Original");
  });

  // ---- removeWallet ----

  it("removeWallet() removes the wallet from local state on success", async () => {
    const api = makeApi({
      delete: vi.fn().mockResolvedValue(undefined),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "w1" }),
      makeWallet({ id: "w2" }),
    ];
    await store.removeWallet("w1");

    expect(api.delete).toHaveBeenCalledWith("/wallets/w1");
    expect(store.wallets).toHaveLength(1);
    expect(store.wallets[0].id).toBe("w2");
  });

  it("removeWallet() sets error on failure and does not remove from state", async () => {
    const api = makeApi({
      delete: vi.fn().mockRejectedValue(new ApiError(404, "Wallet not found.")),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    store.wallets = [makeWallet({ id: "w1" })];
    await expect(store.removeWallet("w1")).rejects.toThrow("Wallet not found.");
    expect(store.error).toBe("Wallet not found.");
    expect(store.wallets).toHaveLength(1);
  });

  // ---- retryHistoryImport ----

  it("retryHistoryImport() calls POST /wallets/{id}/retry-history", async () => {
    const api = makeApi({
      post: vi.fn().mockResolvedValue({ ok: true, message: "History import started." }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    store.wallets = [makeWallet({ id: "w1", history_status: "failed" })];
    await store.retryHistoryImport("w1");

    expect(api.post).toHaveBeenCalledWith("/wallets/w1/retry-history");
  });

  it("retryHistoryImport() updates history_status to importing on success", async () => {
    const api = makeApi({
      post: vi.fn().mockResolvedValue({ ok: true }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    store.wallets = [makeWallet({ id: "w1", history_status: "failed" })];
    await store.retryHistoryImport("w1");

    expect(store.wallets[0].history_status).toBe("importing");
  });

  it("retryHistoryImport() sets error on failure and re-throws", async () => {
    const api = makeApi({
      post: vi.fn().mockRejectedValue(new ApiError(404, "Wallet not found.")),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    await expect(store.retryHistoryImport("missing")).rejects.toThrow(
      "Wallet not found.",
    );
    expect(store.error).toBe("Wallet not found.");
  });
});
