import { describe, it, expect, beforeEach, vi } from "vitest";
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
vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    useRouter: () => ({ push: mockPush }),
  };
});

import { useApi } from "@/composables/useApi";
import { useWalletsStore } from "@/stores/wallets";
import WalletTable from "@/components/widgets/WalletTable.vue";

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
    address: "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
    tag: "Cold Storage",
    balance: "1.50000000",
    balance_usd: "107400.00",
    created_at: "2026-01-01T00:00:00Z",
    last_updated: "2026-01-02T00:00:00Z",
    warning: null,
    history_status: "done",
    wallet_type: "individual",
    hd_loading: false,
    derived_addresses: null,
    derived_address_count: null,
    derived_address_total: null,
    ...overrides,
  };
}

function makeHdWallet(overrides: Record<string, unknown> = {}) {
  return makeWallet({
    id: "hd-wallet-1",
    address: "xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH12345678901abcde",
    tag: "BTC HD Wallet #1",
    wallet_type: "hd",
    extended_key_type: "xpub",
    hd_loading: false,
    derived_addresses: [],
    derived_address_count: 0,
    derived_address_total: 0,
    ...overrides,
  });
}

describe("WalletTable", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockPush.mockClear();
    vi.mocked(useApi).mockReturnValue(makeApi() as ReturnType<typeof useApi>);
  });

  it("renders wallet rows correctly", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "w1", tag: "Cold Storage", network: "BTC" }),
      makeWallet({
        id: "w2",
        tag: "Mining Rewards",
        network: "KAS",
        balance: "393964.62",
        balance_usd: "12803.80",
        address: "kaspa:qpamxxxxxxxxxxxxxxxxv8dkf7",
      }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    const rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(2);
    // Check network badges are present
    expect(wrapper.text()).toContain("BTC");
    expect(wrapper.text()).toContain("KAS");
    // Check balances
    expect(wrapper.text()).toContain("1.50000000 BTC");
    expect(wrapper.text()).toContain("393,964.62 KAS");
  });

  it("shows empty state when wallets is empty", async () => {
    const store = useWalletsStore();
    store.wallets = [];

    const wrapper = mount(WalletTable);

    // The empty row is a tr with colspan, so there IS a tr, but it shows no wallet data
    expect(wrapper.text()).toContain("No wallets");
    // No wallet balance data
    expect(wrapper.text()).not.toContain("BTC");
    expect(wrapper.text()).not.toContain("KAS");
  });

  it("default sort is by tag ascending", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "w1", tag: "Zebra Wallet", network: "BTC", balance: "0.10000000" }),
      makeWallet({ id: "w2", tag: "Alpha Wallet", network: "BTC", balance: "0.20000000" }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    const rows = wrapper.findAll("tbody tr");
    // Alpha Wallet has balance 0.20000000, Zebra has 0.10000000
    // Alpha should appear first (alphabetical sort by tag)
    expect(rows[0].text()).toContain("0.20000000 BTC");
    expect(rows[1].text()).toContain("0.10000000 BTC");
  });

  it("clicking a column header changes sort order", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "w1", tag: "Alpha", network: "BTC", balance: "0.50000000", balance_usd: "35000.00" }),
      makeWallet({ id: "w2", tag: "Beta", network: "BTC", balance: "1.00000000", balance_usd: "70000.00" }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    // Initial sort is tag ascending: Alpha first
    let rows = wrapper.findAll("tbody tr");
    expect(rows[0].text()).toContain("0.50000000 BTC");
    expect(rows[1].text()).toContain("1.00000000 BTC");

    // Click Balance header to sort by balance
    const headers = wrapper.findAll("thead th");
    const balanceHeader = headers.find((h) => h.text().includes("Balance") && !h.text().includes("USD"));
    await balanceHeader!.trigger("click");
    await flushPromises();

    rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(2);
    // Ascending by balance: 0.5 first, then 1.0
    expect(rows[0].text()).toContain("0.50000000 BTC");
    expect(rows[1].text()).toContain("1.00000000 BTC");
  });

  it("clicking the same column header twice reverses sort order", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "w1", tag: "Alpha", balance: "0.50000000", balance_usd: "35000.00" }),
      makeWallet({ id: "w2", tag: "Beta", balance: "1.00000000", balance_usd: "70000.00" }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    // Initial: tag asc — Alpha first (0.5 BTC)
    let rows = wrapper.findAll("tbody tr");
    expect(rows[0].text()).toContain("0.50000000 BTC");

    // Click Tag header to reverse (desc)
    const headers = wrapper.findAll("thead th");
    const tagHeader = headers.find((h) => h.text().includes("Tag"));
    await tagHeader!.trigger("click");
    await flushPromises();

    rows = wrapper.findAll("tbody tr");
    // Now Beta first (1.0 BTC)
    expect(rows[0].text()).toContain("1.00000000 BTC");
    expect(rows[1].text()).toContain("0.50000000 BTC");
  });

  it("clicking the edit icon does not trigger row navigation", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "wallet-abc" }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    const editBtn = wrapper.find(".edit-btn");
    await editBtn.trigger("click");

    expect(mockPush).not.toHaveBeenCalled();
  });

  it("clicking a row navigates to /wallet/:id", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "wallet-abc" }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    const row = wrapper.find("tbody tr");
    await row.trigger("click");

    expect(mockPush).toHaveBeenCalledWith("/wallet/wallet-abc");
  });

  // ---- HD wallet features ----

  it("renders HD badge for HD wallets", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeHdWallet({ id: "hd-1" }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    // HdBadge renders "HD" text
    expect(wrapper.text()).toContain("HD");
  });

  it("does not render HD badge for individual wallets", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeWallet({ id: "ind-1", wallet_type: "individual" }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    // Should not have an element with the hd-badge class
    expect(wrapper.find(".hd-badge").exists()).toBe(false);
  });

  it("expand button has aria-expanded=false initially", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeHdWallet({ id: "hd-1" }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    const expandBtn = wrapper.find(".expand-btn");
    expect(expandBtn.exists()).toBe(true);
    expect(expandBtn.attributes("aria-expanded")).toBe("false");
  });

  it("clicking expand button toggles aria-expanded to true", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeHdWallet({ id: "hd-1" }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    const expandBtn = wrapper.find(".expand-btn");
    await expandBtn.trigger("click");
    await flushPromises();

    expect(expandBtn.attributes("aria-expanded")).toBe("true");
  });

  it("clicking expand button again collapses (toggles aria-expanded back to false)", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeHdWallet({ id: "hd-1" }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    const expandBtn = wrapper.find(".expand-btn");
    await expandBtn.trigger("click");
    await flushPromises();
    await expandBtn.trigger("click");
    await flushPromises();

    expect(expandBtn.attributes("aria-expanded")).toBe("false");
  });

  it("DerivedAddressList is shown when HD wallet row is expanded", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeHdWallet({ id: "hd-1", derived_addresses: [] }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    // Before expand: DerivedAddressList not rendered
    expect(wrapper.find(".derived-address-list").exists()).toBe(false);

    const expandBtn = wrapper.find(".expand-btn");
    await expandBtn.trigger("click");
    await flushPromises();

    // After expand: DerivedAddressList is rendered
    expect(wrapper.find(".derived-address-list").exists()).toBe(true);
  });

  it("expand button does not trigger row navigation", async () => {
    const store = useWalletsStore();
    store.wallets = [
      makeHdWallet({ id: "hd-nav-test" }),
    ] as ReturnType<typeof makeWallet>[];

    const wrapper = mount(WalletTable);

    const expandBtn = wrapper.find(".expand-btn");
    await expandBtn.trigger("click");

    expect(mockPush).not.toHaveBeenCalled();
  });
});
