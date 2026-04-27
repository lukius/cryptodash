<script setup lang="ts">
import { computed } from "vue";
import { Pie } from "vue-chartjs";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  type TooltipItem,
} from "chart.js";
import type { PortfolioComposition } from "@/types/api";
import { formatUsd } from "@/utils/format";

ChartJS.register(ArcElement, Tooltip, Legend);

const props = defineProps<{
  composition: PortfolioComposition | null;
}>();

const NETWORK_COLORS: Record<string, string> = {
  BTC: "#f7931a",
  KAS: "#49eacb",
};

const chartData = computed(() => {
  if (!props.composition || props.composition.segments.length === 0)
    return null;
  const segments = props.composition.segments;
  return {
    labels: segments.map((s) => s.network),
    datasets: [
      {
        data: segments.map((s) => parseFloat(s.value_usd)),
        backgroundColor: segments.map(
          (s) => NETWORK_COLORS[s.network] ?? "#888",
        ),
        borderColor: segments.map((s) => NETWORK_COLORS[s.network] ?? "#888"),
        borderWidth: 2,
        hoverOffset: 8,
      },
    ],
  };
});

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
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
        label: (ctx: TooltipItem<"pie">) => {
          const value = ctx.raw as number;
          const segment = props.composition?.segments.find(
            (s) => s.network === ctx.label,
          );
          const pct = segment
            ? `${parseFloat(segment.percentage).toFixed(1)}%`
            : "";
          return ` ${ctx.label}: ${pct} · ${formatUsd(value)}`;
        },
      },
    },
  },
}));
</script>

<template>
  <div class="card chart-card pie-card">
    <div class="chart-header">
      <span class="chart-title">Composition</span>
    </div>

    <div v-if="chartData" class="chart-canvas-wrap" style="height: 240px">
      <Pie :data="chartData" :options="chartOptions" />
    </div>
    <div v-else class="empty-chart">No composition data</div>

    <div
      v-if="composition && composition.segments.length > 0"
      class="pie-legend"
    >
      <div
        v-for="seg in composition.segments"
        :key="seg.network"
        class="pie-legend-item"
      >
        <div class="left">
          <span
            class="swatch"
            :style="{ background: NETWORK_COLORS[seg.network] ?? '#888' }"
          />
          <span class="name">{{
            seg.network === "BTC" ? "Bitcoin" : "Kaspa"
          }}</span>
        </div>
        <div class="right">
          <div class="pct">{{ parseFloat(seg.percentage).toFixed(1) }}%</div>
          <div class="usd">
            {{ formatUsd(seg.value_usd) }}
          </div>
        </div>
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
}

.chart-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text);
}

.chart-canvas-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-chart {
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.pie-legend {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}

.pie-legend-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.swatch {
  width: 12px;
  height: 12px;
  border-radius: 4px;
  display: inline-block;
}

.name {
  font-size: 0.85rem;
  font-weight: 500;
}

.right {
  text-align: right;
}

.pct {
  font-size: 0.85rem;
  font-weight: 600;
  font-family: "JetBrains Mono", monospace;
}

.usd {
  font-size: 0.72rem;
  color: var(--text-muted);
  font-family: "JetBrains Mono", monospace;
}
</style>
