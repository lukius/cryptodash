<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
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
import type { WalletHistoryResponse } from "@/types/api";
import { useDashboardStore } from "@/stores/dashboard";
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

const props = withDefaults(
  defineProps<{
    walletId: string;
    unit: "usd" | "native";
    network?: string;
    showUnitToggle?: boolean;
  }>(),
  { showUnitToggle: false },
);

const emit = defineEmits<{
  (e: "update:unit", value: "usd" | "native"): void;
}>();

const store = useDashboardStore();
const selectedRange = ref<TimeRange>("30d");
const historyData = ref<WalletHistoryResponse | null>(null);
const isLoading = ref(false);

async function loadHistory() {
  isLoading.value = true;
  try {
    historyData.value = await store.fetchWalletHistory(
      props.walletId,
      selectedRange.value,
      props.unit,
    );
  } catch {
    historyData.value = null;
  } finally {
    isLoading.value = false;
  }
}

onMounted(loadHistory);

watch([() => props.walletId, () => props.unit, selectedRange], loadHistory);

const hasData = computed(
  () => (historyData.value?.data_points?.length ?? 0) > 1,
);

function formatValue(v: number): string {
  if (props.unit === "usd") return formatUsd(v);
  if (props.network === "BTC") return formatBtc(v);
  return formatKas(v);
}

const chartData = computed(() => {
  if (!hasData.value) return null;
  const points = historyData.value!.data_points;
  const color = props.network === "BTC" ? "#f7931a" : "#49eacb";
  return {
    datasets: [
      {
        label: "Balance",
        data: points.map((p) => ({
          x: new Date(p.timestamp).getTime(),
          y: parseFloat(p.value),
        })),
        borderColor: color,
        backgroundColor: `${color}14`,
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
          ` ${formatValue(ctx.parsed.y ?? 0)}`,
      },
    },
  },
  scales: {
    x: {
      type: "time" as const,
      time: { tooltipFormat: "MMM d, yyyy" },
      grid: { color: "rgba(255,255,255,0.04)" },
      ticks: { color: "rgba(255,255,255,0.35)", maxRotation: 0 },
    },
    y: {
      grid: { color: "rgba(255,255,255,0.04)" },
      ticks: {
        color: "rgba(255,255,255,0.35)",
        callback: (v: number | string) =>
          formatValue(typeof v === "string" ? parseFloat(v) : v),
      },
    },
  },
}));
</script>

<template>
  <div class="card chart-card">
    <div class="chart-header">
      <span class="chart-title">Balance Over Time</span>
      <div class="chart-controls">
        <div v-if="showUnitToggle" class="unit-toggle">
          <button
            :class="{ active: unit === 'native' }"
            @click="emit('update:unit', 'native')"
          >
            Native
          </button>
          <button
            :class="{ active: unit === 'usd' }"
            @click="emit('update:unit', 'usd')"
          >
            USD
          </button>
        </div>
        <TimeRangeSelector v-model="selectedRange" />
      </div>
    </div>
    <div class="chart-canvas-wrap" style="height: 240px">
      <Line v-if="chartData" :key="selectedRange" :data="chartData" :options="chartOptions" />
      <div v-else class="empty-chart">
        {{ isLoading ? "Loading..." : "Not enough data for this time range." }}
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
