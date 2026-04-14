import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";
import type { WalletResponse } from "@/types/api";

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

import { useApi } from "@/composables/useApi";
import RemoveWalletDialog from "@/components/wallet/RemoveWalletDialog.vue";

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

function makeWallet(overrides: Partial<WalletResponse> = {}): WalletResponse {
  return {
    id: "wallet-1",
    network: "bitcoin",
    address: "bc1qtest",
    tag: "My Wallet",
    wallet_type: "individual",
    extended_key_type: null,
    balance: "0.5",
    balance_usd: "20000",
    created_at: "2024-01-01T00:00:00Z",
    last_updated: null,
    derived_address_count: null,
    derived_address_total: null,
    hd_loading: false,
    ...overrides,
  };
}

describe("RemoveWalletDialog", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.mocked(useApi).mockReturnValue(makeApi() as ReturnType<typeof useApi>);
  });

  describe("dialog body text", () => {
    it("shows individual wallet text when wallet_type is 'individual'", () => {
      const wallet = makeWallet({ wallet_type: "individual", tag: "Hot Wallet" });
      const wrapper = mount(RemoveWalletDialog, {
        props: { modelValue: true, wallet },
      });
      expect(wrapper.text()).toContain(
        "All historical data for this wallet will be deleted.",
      );
      expect(wrapper.text()).not.toContain("HD wallet");
    });

    it("shows HD wallet text when wallet_type is 'hd'", () => {
      const wallet = makeWallet({
        wallet_type: "hd",
        tag: "My HD Wallet",
        extended_key_type: "xpub",
      });
      const wrapper = mount(RemoveWalletDialog, {
        props: { modelValue: true, wallet },
      });
      expect(wrapper.text()).toContain(
        "All historical data for this HD wallet will be deleted.",
      );
    });

    it("HD wallet body text does not include the bare 'this wallet' phrasing", () => {
      const wallet = makeWallet({ wallet_type: "hd", tag: "My xpub" });
      const wrapper = mount(RemoveWalletDialog, {
        props: { modelValue: true, wallet },
      });
      // The rendered text should say "HD wallet", not "this wallet will be deleted"
      // without "HD" before it.
      const text = wrapper.text();
      expect(text).toContain("this HD wallet will be deleted");
      expect(text).not.toMatch(/this wallet will be deleted/);
    });
  });

  describe("dialog title", () => {
    it("renders the wallet tag in the title", () => {
      const wallet = makeWallet({ tag: "Cold Storage" });
      const wrapper = mount(RemoveWalletDialog, {
        props: { modelValue: true, wallet },
      });
      expect(wrapper.text()).toContain("Remove 'Cold Storage'?");
    });
  });

  describe("visibility", () => {
    it("does not render dialog when modelValue is false", () => {
      const wallet = makeWallet();
      const wrapper = mount(RemoveWalletDialog, {
        props: { modelValue: false, wallet },
      });
      expect(wrapper.find("[role='dialog']").exists()).toBe(false);
    });

    it("does not render dialog when wallet is null", () => {
      const wrapper = mount(RemoveWalletDialog, {
        props: { modelValue: true, wallet: null },
      });
      expect(wrapper.find("[role='dialog']").exists()).toBe(false);
    });
  });
});
