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
import { formatUsd, formatBtc, formatKas } from "@/utils/format";

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
type Unit = "usd" | "btc" | "kas";

const props = defineProps<{
  portfolioHistory: PortfolioHistoryResponse | null;
  selectedRange: TimeRange;
  unit: Unit;
}>();

const emit = defineEmits<{
  (e: "range-change", range: TimeRange): void;
  (e: "unit-change", unit: Unit): void;
}>();

const hasData = computed(
  () => (props.portfolioHistory?.data_points?.length ?? 0) > 1,
);

function formatValue(v: number): string {
  if (props.unit === "btc") return formatBtc(v);
  if (props.unit === "kas") return formatKas(v);
  return formatUsd(v);
}

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

const chartOptions = computed(() => ({
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
        label: (ctx: TooltipItem<"line">) =>
          ` ${formatValue(ctx.parsed.y ?? 0)}`,
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
        callback: (value: number | string) =>
          formatValue(typeof value === "string" ? parseFloat(value) : value),
      },
    },
  },
}));
</script>

<template>
  <div class="card chart-card">
    <div class="chart-header">
      <span class="chart-title">Portfolio Value</span>
      <div class="chart-controls">
        <div class="unit-toggle">
          <button
            :class="{ active: unit === 'usd' }"
            @click="emit('unit-change', 'usd')"
          >
            USD
          </button>
          <button
            :class="{ active: unit === 'btc' }"
            @click="emit('unit-change', 'btc')"
          >
            BTC
          </button>
          <button
            :class="{ active: unit === 'kas' }"
            @click="emit('unit-change', 'kas')"
          >
            KAS
          </button>
        </div>
        <TimeRangeSelector
          :model-value="selectedRange"
          @update:model-value="emit('range-change', $event)"
        />
      </div>
    </div>
    <div class="chart-canvas-wrap" style="height: 240px">
      <Line
        v-if="chartData"
        :key="`${selectedRange}-${unit}`"
        :data="chartData"
        :options="chartOptions"
      />
      <div v-else class="empty-chart">
        {{
          portfolioHistory === null
            ? "Loading, please wait..."
            : "Not enough data for this time range."
        }}
      </div>
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
  flex-wrap: wrap;
  gap: 0.75rem;
}

.chart-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text);
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.unit-toggle {
  display: flex;
  gap: 2px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  padding: 3px;
}

.unit-toggle button {
  padding: 0.3rem 0.55rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  font-family: "JetBrains Mono", monospace;
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.unit-toggle button.active {
  background: var(--accent-dim);
  color: var(--accent);
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
