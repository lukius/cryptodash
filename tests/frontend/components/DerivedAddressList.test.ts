import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import type { DerivedAddressResponse } from "@/types/api";
import DerivedAddressList from "@/components/wallet/DerivedAddressList.vue";

function makeAddress(overrides: Partial<DerivedAddressResponse> = {}): DerivedAddressResponse {
  return {
    address: "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
    balance_native: "0.12345678",
    balance_usd: "8832.50",
    ...overrides,
  };
}

describe("DerivedAddressList", () => {
  // ---- Loading state ----

  it("renders a loading spinner when loading=true", () => {
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: null,
        totalAddressCount: null,
        loading: true,
        error: false,
      },
    });
    // LoadingSpinner has role="status"
    expect(wrapper.find('[role="status"]').exists()).toBe(true);
  });

  it("does not render address rows when loading=true", () => {
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: [makeAddress()],
        totalAddressCount: 1,
        loading: true,
        error: false,
      },
    });
    expect(wrapper.find("table").exists()).toBe(false);
  });

  // ---- Error state ----

  it("renders the error message when error=true and not loading", () => {
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: null,
        totalAddressCount: null,
        loading: false,
        error: true,
      },
    });
    expect(wrapper.text()).toContain(
      "Could not load address breakdown. Will retry on next refresh.",
    );
  });

  it("does not render a table when error=true", () => {
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: null,
        totalAddressCount: null,
        loading: false,
        error: true,
      },
    });
    expect(wrapper.find("table").exists()).toBe(false);
  });

  // ---- Empty state ----

  it("renders the empty message when addresses is an empty array", () => {
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: [],
        totalAddressCount: 0,
        loading: false,
        error: false,
      },
    });
    expect(wrapper.text()).toContain(
      "No transactions found for this HD wallet yet.",
    );
  });

  it("renders the empty message when addresses is null and no error", () => {
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: null,
        totalAddressCount: null,
        loading: false,
        error: false,
      },
    });
    expect(wrapper.text()).toContain(
      "No transactions found for this HD wallet yet.",
    );
  });

  it("does not render a table in empty state", () => {
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: [],
        totalAddressCount: 0,
        loading: false,
        error: false,
      },
    });
    expect(wrapper.find("table").exists()).toBe(false);
  });

  // ---- Populated table ----

  it("renders a table row for each address", () => {
    const addresses = [makeAddress(), makeAddress({ address: "bc1q9999zzz000111222333444555666777888999" })];
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses,
        totalAddressCount: 2,
        loading: false,
        error: false,
      },
    });
    const rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(2);
  });

  it("displays table header columns: Address, BTC, USD", () => {
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: [makeAddress()],
        totalAddressCount: 1,
        loading: false,
        error: false,
      },
    });
    const headerText = wrapper.find("thead").text();
    expect(headerText).toContain("Address");
    expect(headerText).toContain("BTC");
    expect(headerText).toContain("USD");
  });

  it("renders the BTC balance formatted with 8 decimals", () => {
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: [makeAddress({ balance_native: "0.12345678" })],
        totalAddressCount: 1,
        loading: false,
        error: false,
      },
    });
    expect(wrapper.text()).toContain("0.12345678 BTC");
  });

  it("renders the USD balance formatted as currency", () => {
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: [makeAddress({ balance_usd: "8832.50" })],
        totalAddressCount: 1,
        loading: false,
        error: false,
      },
    });
    expect(wrapper.text()).toContain("$8,832.50");
  });

  it("shows 'N/A' when balance_usd is null", () => {
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: [makeAddress({ balance_usd: null })],
        totalAddressCount: 1,
        loading: false,
        error: false,
      },
    });
    expect(wrapper.text()).toContain("N/A");
  });

  // ---- Address truncation (FR-H09 / ST4) ----

  it("truncates addresses to first 8 + '...' + last 6 characters", () => {
    const addr = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq";
    const expected = `${addr.slice(0, 8)}...${addr.slice(-6)}`;
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: [makeAddress({ address: addr })],
        totalAddressCount: 1,
        loading: false,
        error: false,
      },
    });
    expect(wrapper.text()).toContain(expected);
  });

  it("shows the full address as a tooltip on hover (title attribute)", () => {
    const addr = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq";
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: [makeAddress({ address: addr })],
        totalAddressCount: 1,
        loading: false,
        error: false,
      },
    });
    const span = wrapper.find("span[title]");
    expect(span.attributes("title")).toBe(addr);
  });

  it("does not truncate short addresses", () => {
    const shortAddr = "1A2B3C4D5E";
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: [makeAddress({ address: shortAddr })],
        totalAddressCount: 1,
        loading: false,
        error: false,
      },
    });
    expect(wrapper.text()).toContain(shortAddr);
    expect(wrapper.text()).not.toContain("...");
  });

  // ---- "Showing top N of M" caption (FR-H15) ----

  it("shows 'Showing top N of M addresses.' when totalAddressCount > addresses.length", () => {
    const addresses = Array.from({ length: 200 }, (_, i) =>
      makeAddress({ address: `bc1q${"a".repeat(7)}${String(i).padStart(6, "0")}` }),
    );
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses,
        totalAddressCount: 350,
        loading: false,
        error: false,
      },
    });
    expect(wrapper.text()).toContain("Showing top 200 of 350 addresses.");
  });

  it("does not show the 'Showing top N of M' note when totalAddressCount equals addresses.length", () => {
    const addresses = [makeAddress()];
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses,
        totalAddressCount: 1,
        loading: false,
        error: false,
      },
    });
    expect(wrapper.text()).not.toContain("Showing top");
  });

  it("does not show the 'Showing top N of M' note when totalAddressCount is null", () => {
    const addresses = [makeAddress()];
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses,
        totalAddressCount: null,
        loading: false,
        error: false,
      },
    });
    expect(wrapper.text()).not.toContain("Showing top");
  });

  // ---- Loading takes priority over error ----

  it("shows spinner (not error) when both loading and error are true", () => {
    const wrapper = mount(DerivedAddressList, {
      props: {
        addresses: null,
        totalAddressCount: null,
        loading: true,
        error: true,
      },
    });
    expect(wrapper.find('[role="status"]').exists()).toBe(true);
    expect(wrapper.text()).not.toContain("Could not load");
  });
});
