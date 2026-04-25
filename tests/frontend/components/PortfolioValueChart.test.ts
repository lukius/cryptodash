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

import PortfolioValueChart from "@/components/widgets/PortfolioValueChart.vue";

function makeHistory(pointCount: number) {
  const points = Array.from({ length: pointCount }, (_, i) => ({
    timestamp: `2026-01-${String(i + 1).padStart(2, "0")}T00:00:00Z`,
    value: String(50000 + i * 100),
  }));
  return { data_points: points, start_date: "2026-01-01", end_date: "2026-01-31" };
}

describe("PortfolioValueChart", () => {
  it("shows loading message when portfolioHistory is null", () => {
    const wrapper = mount(PortfolioValueChart, {
      props: { portfolioHistory: null, selectedRange: "30d", unit: "usd" },
    });
    expect(wrapper.text()).toContain("Loading, please wait...");
    expect(wrapper.text()).not.toContain("Not enough data");
  });

  it("shows not-enough-data when history has 0 points", () => {
    const wrapper = mount(PortfolioValueChart, {
      props: { portfolioHistory: makeHistory(0), selectedRange: "30d", unit: "usd" },
    });
    expect(wrapper.text()).toContain("Not enough data for this time range.");
    expect(wrapper.text()).not.toContain("Loading");
  });

  it("shows not-enough-data when history has exactly 1 point", () => {
    const wrapper = mount(PortfolioValueChart, {
      props: { portfolioHistory: makeHistory(1), selectedRange: "30d", unit: "usd" },
    });
    expect(wrapper.text()).toContain("Not enough data for this time range.");
    expect(wrapper.text()).not.toContain("Loading");
  });

  it("renders the chart (no empty message) when history has 2+ points", () => {
    const wrapper = mount(PortfolioValueChart, {
      props: { portfolioHistory: makeHistory(2), selectedRange: "30d", unit: "usd" },
    });
    expect(wrapper.text()).not.toContain("Loading");
    expect(wrapper.text()).not.toContain("Not enough data");
    expect(wrapper.find("canvas").exists()).toBe(true);
  });

  it("shows USD, BTC, KAS toggle buttons", () => {
    const wrapper = mount(PortfolioValueChart, {
      props: { portfolioHistory: null, selectedRange: "30d", unit: "usd" },
    });
    const buttons = wrapper.findAll(".unit-toggle button");
    const labels = buttons.map((b) => b.text());
    expect(labels).toContain("USD");
    expect(labels).toContain("BTC");
    expect(labels).toContain("KAS");
  });

  it("marks the active unit button", () => {
    const wrapper = mount(PortfolioValueChart, {
      props: { portfolioHistory: null, selectedRange: "30d", unit: "btc" },
    });
    const buttons = wrapper.findAll(".unit-toggle button");
    const activeBtn = buttons.find((b) => b.classes("active"));
    expect(activeBtn?.text()).toBe("BTC");
  });

  it("emits unit-change when a toggle button is clicked", async () => {
    const wrapper = mount(PortfolioValueChart, {
      props: { portfolioHistory: null, selectedRange: "30d", unit: "usd" },
    });
    const buttons = wrapper.findAll(".unit-toggle button");
    const kasBtn = buttons.find((b) => b.text() === "KAS");
    await kasBtn?.trigger("click");
    expect(wrapper.emitted("unit-change")).toBeTruthy();
    expect(wrapper.emitted("unit-change")![0]).toEqual(["kas"]);
  });
});
