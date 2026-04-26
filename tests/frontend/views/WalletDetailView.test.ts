import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";

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

const mockPush = vi.fn();
const mockRouteParams = { id: "hd-wallet-1" };

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    useRouter: () => ({ push: mockPush }),
    useRoute: () => ({ params: mockRouteParams }),
    RouterLink: {
      template: "<a><slot /></a>",
      props: ["to"],
    },
  };
});

import { useApi } from "@/composables/useApi";
import { useWalletsStore } from "@/stores/wallets";
import WalletDetailView from "@/views/WalletDetailView.vue";

function makeTransactionPage(overrides: Record<string, unknown> = {}) {
  return {
    transactions: [],
    total: 0,
    page: 1,
    page_size: 50,
    total_pages: 1,
    ...overrides,
  };
}

function makeTx(overrides: Record<string, unknown> = {}) {
  return {
    id: "tx-1",
    tx_hash: "abc123def456",
    amount: "0.001",
    balance_after: "1.001",
    block_height: 800000,
    timestamp: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function makeApi(overrides: Record<string, unknown> = {}) {
  return {
    get: vi.fn().mockImplementation((url: string) => {
      if (url.includes("/history")) return Promise.resolve({ data_points: [], snapshots: [] });
      return Promise.resolve(makeTransactionPage());
    }),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    ...overrides,
  };
}

function makeHdWallet(overrides: Record<string, unknown> = {}) {
  return {
    id: "hd-wallet-1",
    network: "BTC",
    address: "xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH12345678901abcde",
    tag: "BTC HD Wallet #1",
    wallet_type: "hd",
    extended_key_type: "xpub",
    balance: "1.50000000",
    balance_usd: "107400.00",
    created_at: "2026-01-01T00:00:00Z",
    last_updated: "2026-01-02T00:00:00Z",
    warning: null,
    history_status: "done",
    hd_loading: false,
    derived_addresses: [],
    derived_address_count: 0,
    derived_address_total: 0,
    ...overrides,
  };
}

function makeIndividualWallet(overrides: Record<string, unknown> = {}) {
  return {
    id: "hd-wallet-1",
    network: "BTC",
    address: "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
    tag: "Cold Storage",
    wallet_type: "individual",
    extended_key_type: null,
    balance: "0.50000000",
    balance_usd: "35000.00",
    created_at: "2026-01-01T00:00:00Z",
    last_updated: "2026-01-02T00:00:00Z",
    warning: null,
    history_status: "done",
    hd_loading: false,
    derived_addresses: null,
    derived_address_count: null,
    derived_address_total: null,
    ...overrides,
  };
}

describe("WalletDetailView — transaction reload on store changes", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockPush.mockClear();
  });

  it("reloads transactions when wallet balance changes after a refresh", async () => {
    const api = makeApi();
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    const wallet = makeIndividualWallet({ network: "KAS", balance: "1000.00" });
    store.wallets = [wallet] as ReturnType<typeof makeIndividualWallet>[];

    mount(WalletDetailView);
    await flushPromises();

    const callsAfterMount = (api.get as ReturnType<typeof vi.fn>).mock.calls.length;

    // Simulate wallets.fetchWallets() updating the balance (post refresh:completed)
    store.wallets = [{ ...wallet, balance: "1100.00" }] as ReturnType<typeof makeIndividualWallet>[];
    await flushPromises();

    expect((api.get as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(callsAfterMount);
  });

  it("does not reload transactions when balance is unchanged", async () => {
    const api = makeApi();
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    const wallet = makeIndividualWallet({ network: "KAS", balance: "1000.00" });
    store.wallets = [wallet] as ReturnType<typeof makeIndividualWallet>[];

    mount(WalletDetailView);
    await flushPromises();

    const callsAfterMount = (api.get as ReturnType<typeof vi.fn>).mock.calls.length;

    // Same balance — no reload expected
    store.wallets = [{ ...wallet, balance: "1000.00" }] as ReturnType<typeof makeIndividualWallet>[];
    await flushPromises();

    expect((api.get as ReturnType<typeof vi.fn>).mock.calls.length).toBe(callsAfterMount);
  });

  it("reloads transactions when history_status transitions to 'complete'", async () => {
    const api = makeApi();
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    const wallet = makeIndividualWallet({ history_status: "importing" });
    store.wallets = [wallet] as ReturnType<typeof makeIndividualWallet>[];

    mount(WalletDetailView);
    await flushPromises();

    const callsAfterMount = (api.get as ReturnType<typeof vi.fn>).mock.calls.length;

    // Simulate history import completing
    store.wallets = [{ ...wallet, history_status: "complete" }] as ReturnType<typeof makeIndividualWallet>[];
    await flushPromises();

    expect((api.get as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(callsAfterMount);
  });

  it("does not reload transactions when history_status is already 'complete' and doesn't change", async () => {
    const api = makeApi();
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    const wallet = makeIndividualWallet({ history_status: "complete" });
    store.wallets = [wallet] as ReturnType<typeof makeIndividualWallet>[];

    mount(WalletDetailView);
    await flushPromises();

    const callsAfterMount = (api.get as ReturnType<typeof vi.fn>).mock.calls.length;

    // No status change
    store.wallets = [{ ...wallet, history_status: "complete" }] as ReturnType<typeof makeIndividualWallet>[];
    await flushPromises();

    expect((api.get as ReturnType<typeof vi.fn>).mock.calls.length).toBe(callsAfterMount);
  });
});

describe("WalletDetailView — address display", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockPush.mockClear();
    vi.mocked(useApi).mockReturnValue(makeApi() as ReturnType<typeof useApi>);
  });

  it("displays an HD wallet address as first 10 + '...' + last 6 chars (FR-H09)", async () => {
    const store = useWalletsStore();
    const wallet = makeHdWallet();
    store.wallets = [wallet] as ReturnType<typeof makeHdWallet>[];

    const wrapper = mount(WalletDetailView);
    await flushPromises();

    // address: "xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH12345678901abcde"
    // first 10: "xpub6CUGRUB" — wait, let's count: x-p-u-b-6-C-U-G-R-U = 10 chars = "xpub6CUGRU"
    // last 6:   "1abcde"
    const addressEl = wrapper.find(".wallet-address");
    expect(addressEl.exists()).toBe(true);
    expect(addressEl.text()).toBe("xpub6CUGRU...1abcde");
  });

  it("does not use the 12+8 truncation for an HD wallet address", async () => {
    const store = useWalletsStore();
    const wallet = makeHdWallet();
    store.wallets = [wallet] as ReturnType<typeof makeHdWallet>[];

    const wrapper = mount(WalletDetailView);
    await flushPromises();

    const addressEl = wrapper.find(".wallet-address");
    expect(addressEl.exists()).toBe(true);
    // The old (wrong) behavior was truncateAddress(address, 12, 8):
    // first 12: "xpub6CUGRUBf", last 8: "01abcde" — wait 8 from end: "01abcde" is 7, let's count
    // "xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH12345678901abcde"
    // last 8: "01abcde" — the string ends in "01abcde" that's 7... count from end:
    // e-d-c-b-a-1-0-9 => "901abcde" is 8 chars
    // first 12: "xpub6CUGRUBf"
    // Wrong format would be "xpub6CUGRUBf...901abcde"
    expect(addressEl.text()).not.toBe("xpub6CUGRUBf...901abcde");
  });

  it("displays an individual wallet address as first 8 + '...' + last 6 chars", async () => {
    const store = useWalletsStore();
    const wallet = makeIndividualWallet();
    store.wallets = [wallet] as ReturnType<typeof makeIndividualWallet>[];

    const wrapper = mount(WalletDetailView);
    await flushPromises();

    // address: "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
    // first 8: "bc1qar0s", last 6: "f5mdq" — count from end: q-d-m-5-f-w => "wf5mdq" is 6
    const addressEl = wrapper.find(".wallet-address");
    expect(addressEl.exists()).toBe(true);
    expect(addressEl.text()).toBe("bc1qar0s...wf5mdq");
  });
});

describe("WalletDetailView — pagination scroll fix", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockPush.mockClear();
  });

  it("shows loading message on initial load (txPageChanging is false)", async () => {
    let resolveInitial!: (v: ReturnType<typeof makeTransactionPage>) => void;
    const pending = new Promise<ReturnType<typeof makeTransactionPage>>((res) => { resolveInitial = res; });

    const api = {
      ...makeApi(),
      get: vi.fn().mockImplementation((url: string) => {
        if (url.includes("/transactions")) return pending;
        return Promise.resolve({ data_points: [] });
      }),
    };
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    store.wallets = [makeIndividualWallet()];

    const wrapper = mount(WalletDetailView);
    await vi.waitFor(() => expect(wrapper.find(".tx-empty").exists()).toBe(true));

    expect(wrapper.find(".tx-empty").text()).toContain("Loading");
    expect(wrapper.find(".tx-table").exists()).toBe(false);

    resolveInitial(makeTransactionPage());
    await flushPromises();
  });

  it("table stays visible with tx-table-loading class during page navigation", async () => {
    let txCallCount = 0;
    let resolveNav!: (v: ReturnType<typeof makeTransactionPage>) => void;

    const api = {
      ...makeApi(),
      get: vi.fn().mockImplementation((url: string) => {
        if (!url.includes("/transactions")) return Promise.resolve({ data_points: [] });
        txCallCount++;
        if (txCallCount === 1) {
          return Promise.resolve(makeTransactionPage({
            transactions: [makeTx()],
            total: 20,
            page: 1,
            page_size: 10,
            total_pages: 2,
          }));
        }
        return new Promise<ReturnType<typeof makeTransactionPage>>((res) => { resolveNav = res; });
      }),
    };
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    store.wallets = [makeIndividualWallet()];

    const wrapper = mount(WalletDetailView);
    await flushPromises();

    // Table rendered after initial load
    expect(wrapper.find(".tx-table").exists()).toBe(true);

    // Click the next-page button (▶)
    const nextBtn = wrapper.findAll(".nav-btn").find((b) => b.text() === "▶");
    await nextBtn!.trigger("click");

    // During navigation: table stays visible with loading class, no loading message
    expect(wrapper.find(".tx-table").exists()).toBe(true);
    expect(wrapper.find(".tx-table").classes()).toContain("tx-table-loading");
    expect(wrapper.find(".tx-empty").exists()).toBe(false);

    // Resolve navigation and verify clean state
    resolveNav(makeTransactionPage({ transactions: [makeTx({ id: "tx-2" })], total: 20, page: 2, total_pages: 2 }));
    await flushPromises();

    expect(wrapper.find(".tx-table").exists()).toBe(true);
    expect(wrapper.find(".tx-table").classes()).not.toContain("tx-table-loading");
  });

  it("table stays visible with loading class when changing page size", async () => {
    let txCallCount = 0;
    let resolveNav!: (v: ReturnType<typeof makeTransactionPage>) => void;

    const api = {
      ...makeApi(),
      get: vi.fn().mockImplementation((url: string) => {
        if (!url.includes("/transactions")) return Promise.resolve({ data_points: [] });
        txCallCount++;
        if (txCallCount === 1) {
          return Promise.resolve(makeTransactionPage({
            transactions: [makeTx()],
            total: 5,
            page: 1,
            page_size: 50,
            total_pages: 1,
          }));
        }
        return new Promise<ReturnType<typeof makeTransactionPage>>((res) => { resolveNav = res; });
      }),
    };
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    store.wallets = [makeIndividualWallet()];

    const wrapper = mount(WalletDetailView);
    await flushPromises();

    expect(wrapper.find(".tx-table").exists()).toBe(true);

    // Click the "10" rows-per-page button
    const tenBtn = wrapper.findAll(".page-size-btn").find((b) => b.text() === "10");
    await tenBtn!.trigger("click");

    // During size change: table still visible, loading class applied
    expect(wrapper.find(".tx-table").exists()).toBe(true);
    expect(wrapper.find(".tx-table").classes()).toContain("tx-table-loading");
    expect(wrapper.find(".tx-empty").exists()).toBe(false);

    resolveNav(makeTransactionPage({ transactions: [makeTx()], total: 5, page: 1, page_size: 10, total_pages: 1 }));
    await flushPromises();

    expect(wrapper.find(".tx-table").classes()).not.toContain("tx-table-loading");
  });
});

describe("WalletDetailView — copy address feedback", () => {
  let writeTextMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: writeTextMock },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows 'Copied!' label after clicking the copy button", async () => {
    vi.useFakeTimers();
    const api = makeApi();
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);
    const store = useWalletsStore();
    store.wallets = [makeIndividualWallet()];

    const wrapper = mount(WalletDetailView);
    await flushPromises();

    const feedback = wrapper.find(".copy-feedback");
    expect(feedback.classes()).not.toContain("visible");

    await wrapper.find(".copy-btn").trigger("click");
    await flushPromises();

    expect(feedback.classes()).toContain("visible");
    expect(writeTextMock).toHaveBeenCalledWith("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq");
  });

  it("hides 'Copied!' label after 1500 ms", async () => {
    vi.useFakeTimers();
    const api = makeApi();
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);
    const store = useWalletsStore();
    store.wallets = [makeIndividualWallet()];

    const wrapper = mount(WalletDetailView);
    await flushPromises();

    await wrapper.find(".copy-btn").trigger("click");
    await flushPromises();

    expect(wrapper.find(".copy-feedback").classes()).toContain("visible");

    vi.advanceTimersByTime(1500);
    await flushPromises();

    expect(wrapper.find(".copy-feedback").classes()).not.toContain("visible");
  });
});
