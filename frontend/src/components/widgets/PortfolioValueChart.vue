<script setup lang="ts">
import { computed } from "vue";
import { Line } from "vue-chartjs";
import {
  Chart as ChartJS,
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  type TooltipItem,
} from "chart.js";
import "chartjs-adapter-date-fns";
import type { PortfolioHistoryResponse } from "@/types/api";
import TimeRangeSelector from "@/components/common/TimeRangeSelector.vue";
import { formatUsd } from "@/utils/format";

ChartJS.register(
  LinearScale,
  TimeScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

type TimeRange = "7d" | "30d" | "90d" | "1y" | "all";

const props = defineProps<{
  portfolioHistory: PortfolioHistoryResponse | null;
  selectedRange: TimeRange;
}>();

const emit = defineEmits<{
  (e: "range-change", range: TimeRange): void;
}>();

const hasData = computed(
  () => (props.portfolioHistory?.data_points?.length ?? 0) > 1,
);

const chartData = computed(() => {
  if (!hasData.value) return null;
  const points = props.portfolioHistory!.data_points;
  return {
    datasets: [
      {
        label: "Portfolio Value",
        data: points.map((p) => ({
          x: new Date(p.timestamp).getTime(),
          y: parseFloat(p.value),
        })),
        borderColor: "#49eacb",
        backgroundColor: "rgba(73, 234, 203, 0.08)",
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        fill: true,
        tension: 0.3,
      },
    ],
  };
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: "index" as const,
    intersect: false,
  },
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
        label: (ctx: TooltipItem<"line">) => ` ${formatUsd(ctx.parsed.y ?? 0)}`,
      },
    },
  },
  scales: {
    x: {
      type: "time" as const,
      time: {
        tooltipFormat: "MMM d, yyyy",
        displayFormats: { day: "MMM d", week: "MMM d", month: "MMM yyyy" },
      },
      grid: { color: "rgba(255,255,255,0.04)" },
      ticks: { color: "rgba(255,255,255,0.35)", maxRotation: 0, maxTicksLimit: 6 },
    },
    y: {
      grid: { color: "rgba(255,255,255,0.04)" },
      ticks: {
        color: "rgba(255,255,255,0.35)",
        callback: (value: number | string) => formatUsd(value),
      },
    },
  },
};
</script>

<template>
  <div class="card chart-card">
    <div class="chart-header">
      <span class="chart-title">Portfolio Value</span>
      <TimeRangeSelector
        :model-value="selectedRange"
        @update:model-value="emit('range-change', $event)"
      />
    </div>
    <div class="chart-canvas-wrap" style="height: 240px">
      <Line v-if="chartData" :key="selectedRange" :data="chartData" :options="chartOptions" />
      <div v-else class="empty-chart">Not enough data for this time range.</div>
    </div>
  </div>
</template>

<style scoped>
.chart-card {
  padding: 1.25rem;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.chart-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text);
}

.chart-canvas-wrap {
  position: relative;
}

.empty-chart {
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 0.85rem;
}
</style>
