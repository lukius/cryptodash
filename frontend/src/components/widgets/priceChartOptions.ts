import type { TooltipItem } from "chart.js";
import { formatUsd } from "@/utils/format";

export function makePriceChartOptions(decimals: number) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index" as const, intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "rgba(12, 18, 32, 0.95)",
        borderColor: "rgba(255,255,255,0.08)",
        borderWidth: 1,
        padding: 10,
        cornerRadius: 10,
        titleFont: { family: "'JetBrains Mono', monospace", size: 11 as const },
        bodyFont: {
          family: "'JetBrains Mono', monospace",
          size: 12 as const,
          weight: "bold" as const,
        },
        callbacks: {
          label: (ctx: TooltipItem<"line">) =>
            ` ${formatUsd(ctx.parsed.y ?? 0, decimals)}`,
        },
      },
    },
    scales: {
      x: {
        type: "time" as const,
        time: {
          tooltipFormat: "MMM d, yyyy",
          displayFormats: { day: "MMM d", week: "MMM d", month: "MMM yyyy" },
          minUnit: "day" as const,
        },
        grid: { color: "rgba(255,255,255,0.04)" },
        ticks: {
          color: "rgba(255,255,255,0.35)",
          maxRotation: 0,
          maxTicksLimit: 6,
        },
      },
      y: {
        grid: { color: "rgba(255,255,255,0.04)" },
        ticks: {
          color: "rgba(255,255,255,0.35)",
          callback: (v: number | string) =>
            formatUsd(typeof v === "string" ? parseFloat(v) : v, decimals),
        },
      },
    },
  };
}
