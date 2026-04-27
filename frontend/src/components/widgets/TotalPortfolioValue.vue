<script setup lang="ts">
import { computed } from "vue";
import type { PortfolioSummary } from "@/types/api";
import { formatUsd, formatPercent } from "@/utils/format";

const props = defineProps<{
  summary: PortfolioSummary | null;
}>();

const change24hUsd = computed(() => {
  if (!props.summary?.change_24h_usd) return null;
  return parseFloat(props.summary.change_24h_usd);
});

const change24hPct = computed(() => {
  if (!props.summary?.change_24h_pct) return null;
  return parseFloat(props.summary.change_24h_pct);
});

const isPositive = computed(() => (change24hUsd.value ?? 0) >= 0);
</script>

<template>
  <div class="card portfolio-value">
    <div class="card-label">
      <div class="dot" style="background: var(--accent)" />
      Total Portfolio Value
    </div>
    <div class="value">
      {{ summary ? formatUsd(summary.total_value_usd) : "N/A" }}
    </div>
    <div v-if="change24hUsd !== null && change24hPct !== null">
      <span :class="['change', isPositive ? 'positive' : 'negative']">
        <span class="arrow">{{ isPositive ? "▲" : "▼" }}</span>
        {{ formatUsd(change24hUsd) }}
        ({{ formatPercent(change24hPct) }})
        <span style="font-weight: 400; opacity: 0.6; margin-left: 4px"
          >24h</span
        >
      </span>
    </div>
    <div v-else class="change-na">24h change: N/A</div>
  </div>
</template>

<style scoped>
.portfolio-value {
  border-color: var(--border-accent);
}

.card-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.value {
  font-size: 2.5rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #fff;
  text-shadow: 0 0 60px rgba(73, 234, 203, 0.15);
  font-family: "JetBrains Mono", monospace;
}

.change {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 0.5rem;
  padding: 0.3rem 0.65rem;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  font-family: "JetBrains Mono", monospace;
}

.change.positive {
  background: var(--green-dim);
  color: var(--green);
}

.change.negative {
  background: var(--red-dim);
  color: var(--red);
}

.change-na {
  margin-top: 0.5rem;
  font-size: 0.82rem;
  color: var(--text-muted);
  font-family: "JetBrains Mono", monospace;
}

@media (max-width: 768px) {
  .value {
    font-size: 1.8rem;
  }
}
</style>
