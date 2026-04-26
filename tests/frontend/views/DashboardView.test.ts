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

vi.mock("@/router", () => ({ default: { push: vi.fn() } }));

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    useRouter: () => ({ push: vi.fn() }),
    useRoute: () => ({ params: {} }),
    RouterLink: { template: "<a><slot /></a>", props: ["to"] },
  };
});

vi.mock("@/composables/useWebSocket", () => ({
  useWebSocket: () => ({ connect: vi.fn(), disconnect: vi.fn(), isConnected: { value: false } }),
}));

// Stub all heavy child components to avoid canvas / chart errors
vi.mock("@/components/layout/AppHeader.vue", () => ({ default: { template: "<header />" } }));
vi.mock("@/components/layout/AppFooter.vue", () => ({ default: { template: "<footer />" } }));
vi.mock("@/components/common/EmptyState.vue", () => ({ default: { template: "<div />" } }));
vi.mock("@/components/common/LoadingSpinner.vue", () => ({ default: { template: "<div />" } }));
vi.mock("@/components/wallet/AddWalletDialog.vue", () => ({ default: { template: "<div />" } }));
vi.mock("@/components/wallet/RemoveWalletDialog.vue", () => ({ default: { template: "<div />" } }));
vi.mock("@/components/widgets/TotalPortfolioValue.vue", () => ({ default: { template: "<div />" } }));
vi.mock("@/components/widgets/TotalBtcBalance.vue", () => ({ default: { template: "<div />" } }));
vi.mock("@/components/widgets/TotalKasBalance.vue", () => ({ default: { template: "<div />" } }));
vi.mock("@/components/widgets/WalletTable.vue", () => ({ default: { template: "<div />" } }));
vi.mock("@/components/widgets/PortfolioComposition.vue", () => ({ default: { template: "<div />" } }));
vi.mock("@/components/widgets/PortfolioValueChart.vue", () => ({ default: { template: "<div />" } }));
vi.mock("@/components/widgets/PriceChart.vue", () => ({ default: { template: "<div />" } }));
vi.mock("@/components/widgets/WalletBalanceChart.vue", () => ({ default: { template: "<div />" } }));

import { useApi } from "@/composables/useApi";
import { useSettingsStore } from "@/stores/settings";
import DashboardView from "@/views/DashboardView.vue";

function makeApi(overrides: Record<string, unknown> = {}) {
  return {
    get: vi.fn().mockResolvedValue({ wallets: [], count: 0, limit: 20 }),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    ...overrides,
  };
}

describe("DashboardView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("uses the preferred timezone already loaded by the router guard", async () => {
    const api = makeApi({
      get: vi.fn().mockResolvedValue({ wallets: [], count: 0, limit: 20 }),
    });
    vi.mocked(useApi).mockReturnValue(api);

    // Simulate the router guard having already loaded settings
    const store = useSettingsStore();
    store.preferredTimezone = "America/Sao_Paulo";

    mount(DashboardView);
    await flushPromises();

    expect(store.preferredTimezone).toBe("America/Sao_Paulo");
  });
});
