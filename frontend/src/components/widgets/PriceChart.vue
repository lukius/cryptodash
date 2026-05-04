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
} from "chart.js";
import "chartjs-adapter-date-fns";
import type { PriceHistoryResponse } from "@/types/api";
import TimeRangeSelector from "@/components/common/TimeRangeSelector.vue";
import { makePriceChartOptions } from "@/components/widgets/priceChartOptions";

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
  priceHistory: PriceHistoryResponse | null;
  selectedRange: TimeRange;
}>();

const emit = defineEmits<{
  (e: "range-change", range: TimeRange): void;
}>();

const hasBtcData = computed(() => (props.priceHistory?.btc?.length ?? 0) > 1);
const hasKasData = computed(() => (props.priceHistory?.kas?.length ?? 0) > 1);

const btcChartData = computed(() => {
  if (!hasBtcData.value) return null;
  return {
    datasets: [
      {
        label: "BTC/USD",
        data: props.priceHistory!.btc.map((p) => ({
          x: new Date(p.timestamp).getTime(),
          y: parseFloat(p.value),
        })),
        borderColor: "#f7931a",
        backgroundColor: "rgba(247, 147, 26, 0.08)",
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        fill: true,
        tension: 0.3,
      },
    ],
  };
});

const kasChartData = computed(() => {
  if (!hasKasData.value) return null;
  return {
    datasets: [
      {
        label: "KAS/USD",
        data: props.priceHistory!.kas.map((p) => ({
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

const btcOptions = makePriceChartOptions(2);
const kasOptions = makePriceChartOptions(3);
</script>

<template>
  <div class="price-row">
    <!-- BTC/USD chart -->
    <div class="card chart-card">
      <div class="chart-header">
        <span class="chart-title">BTC / USD</span>
        <TimeRangeSelector
          :model-value="selectedRange"
          @update:model-value="emit('range-change', $event)"
        />
      </div>
      <div class="chart-canvas-wrap" style="height: 180px">
        <Line
          v-if="btcChartData"
          :key="selectedRange"
          :data="btcChartData"
          :options="btcOptions"
        />
        <div v-else class="empty-chart">
          {{
            priceHistory === null
              ? "Loading, please wait..."
              : "Not enough data for this time range."
          }}
        </div>
      </div>
    </div>

    <!-- KAS/USD chart -->
    <div class="card chart-card">
      <div class="chart-header">
        <span class="chart-title">KAS / USD</span>
      </div>
      <div class="chart-canvas-wrap" style="height: 180px">
        <Line
          v-if="kasChartData"
          :key="selectedRange"
          :data="kasChartData"
          :options="kasOptions"
        />
        <div v-else class="empty-chart">
          {{
            priceHistory === null
              ? "Loading, please wait..."
              : "Not enough data for this time range."
          }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.price-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

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
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 0.85rem;
}

@media (max-width: 1024px) {
  .price-row {
    grid-template-columns: 1fr;
  }
}
</style>
