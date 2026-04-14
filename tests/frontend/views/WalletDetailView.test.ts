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

function makeApi(overrides: Record<string, unknown> = {}) {
  return {
    get: vi.fn().mockResolvedValue([]),
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
