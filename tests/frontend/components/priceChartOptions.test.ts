import { describe, it, expect } from "vitest";
import { makePriceChartOptions } from "@/components/widgets/priceChartOptions";

describe("makePriceChartOptions", () => {
  it("formats y-axis ticks with the requested decimal precision", () => {
    const tick2 = makePriceChartOptions(2).scales.y.ticks.callback;
    const tick3 = makePriceChartOptions(3).scales.y.ticks.callback;
    expect(tick2(0.034)).toBe("$0.03");
    expect(tick3(0.034)).toBe("$0.034");
    expect(tick3("0.0345")).toBe("$0.035");
  });

  it("formats tooltip labels with the requested decimal precision", () => {
    const label2 = makePriceChartOptions(2).plugins.tooltip.callbacks.label;
    const label3 = makePriceChartOptions(3).plugins.tooltip.callbacks.label;
    expect(label2({ parsed: { y: 0.034 } } as never)).toBe(" $0.03");
    expect(label3({ parsed: { y: 0.034 } } as never)).toBe(" $0.034");
  });
});
