import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";

vi.mock("chart.js", () => ({
  Chart: class { static register() {} },
  LinearScale: {},
  TimeScale: {},
  PointElement: {},
  LineElement: {},
  Title: {},
  Tooltip: {},
  Legend: {},
  Filler: {},
}));
vi.mock("chartjs-adapter-date-fns", () => ({}));
vi.mock("vue-chartjs", () => ({
  Line: { template: "<canvas />" },
}));

import PriceChart from "@/components/widgets/PriceChart.vue";

function makePrices(btcCount: number, kasCount: number) {
  const makePoints = (count: number) =>
    Array.from({ length: count }, (_, i) => ({
      timestamp: `2026-01-${String(i + 1).padStart(2, "0")}T00:00:00Z`,
      value: String(50000 + i),
    }));
  return { btc: makePoints(btcCount), kas: makePoints(kasCount) };
}

describe("PriceChart", () => {
  it("shows loading for both charts when priceHistory is null", () => {
    const wrapper = mount(PriceChart, {
      props: { priceHistory: null, selectedRange: "30d" },
    });
    const loadingMessages = wrapper.findAll(".empty-chart");
    expect(loadingMessages).toHaveLength(2);
    loadingMessages.forEach((el) => {
      expect(el.text()).toContain("Loading, please wait...");
    });
  });

  it("shows not-enough-data for both charts when btc and kas have 0 points", () => {
    const wrapper = mount(PriceChart, {
      props: { priceHistory: makePrices(0, 0), selectedRange: "30d" },
    });
    const emptyMessages = wrapper.findAll(".empty-chart");
    expect(emptyMessages).toHaveLength(2);
    emptyMessages.forEach((el) => {
      expect(el.text()).toContain("Not enough data for this time range.");
    });
  });

  it("shows not-enough-data when both datasets have exactly 1 point", () => {
    const wrapper = mount(PriceChart, {
      props: { priceHistory: makePrices(1, 1), selectedRange: "30d" },
    });
    const emptyMessages = wrapper.findAll(".empty-chart");
    expect(emptyMessages).toHaveLength(2);
    emptyMessages.forEach((el) => {
      expect(el.text()).toContain("Not enough data for this time range.");
    });
  });

  it("renders charts (no empty messages) when both datasets have 2+ points", () => {
    const wrapper = mount(PriceChart, {
      props: { priceHistory: makePrices(2, 2), selectedRange: "30d" },
    });
    expect(wrapper.find(".empty-chart").exists()).toBe(false);
    expect(wrapper.findAll("canvas")).toHaveLength(2);
  });

  it("shows not-enough-data for btc only when only kas has data", () => {
    const wrapper = mount(PriceChart, {
      props: { priceHistory: makePrices(0, 2), selectedRange: "30d" },
    });
    const emptyMessages = wrapper.findAll(".empty-chart");
    expect(emptyMessages).toHaveLength(1);
    expect(emptyMessages[0].text()).toContain("Not enough data for this time range.");
    expect(wrapper.findAll("canvas")).toHaveLength(1);
  });
});
