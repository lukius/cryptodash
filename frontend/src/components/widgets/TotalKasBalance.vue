<script setup lang="ts">
import type { PortfolioSummary } from "@/types/api";
import { formatKas, formatUsd } from "@/utils/format";

defineProps<{
  summary: PortfolioSummary | null;
}>();
</script>

<template>
  <div class="card coin-total">
    <div class="card-label">
      <svg
        class="crypto-icon"
        width="18"
        height="18"
        viewBox="58 28 78 78"
        aria-hidden="true"
      >
        <path
          fill="#49EACB"
          d="M134.43,66.58c0,5.11-2.11,10.05-3.96,14.5-1.85,4.45-4.71,8.85-8.18,12.32-3.47,3.47-7.64,6.46-12.24,8.37-4.44,1.84-9.46,3.36-14.57,3.36-5.11,0-10.24-1.26-14.68-3.1-4.61-1.91-7.76-6.06-11.23-9.54-3.47-3.47-7.36-6.73-9.27-11.34-1.91-4.61-2.22-9.46-2.22-14.57 0-5.11-0.6-10.53 1.24-14.98 1.91-4.61 5.94-8.29 9.42-11.76 3.47-3.47 7.32-7.1 11.93-9.01 4.44-1.84 9.7-2.03 14.81-2.03 5.11,0 10.06,0.93 14.5,2.77 4.61,1.91 9.05,4.51 12.52,7.99 3.47,3.47 6.48,7.75 8.39,12.35 1.84,4.44 3.54,9.56 3.54,14.67z"
        />
        <polygon
          fill="#FFF"
          points="98.08,87.16 106.18,88.36 109.4,66.58 106.18,44.79 98.08,45.99 100.39,61.66 83.44,48.61 78.45,55.12 93.32,66.58 78.45,78.03 83.44,84.55 100.39,71.49"
        />
      </svg>
      Kaspa
    </div>
    <div class="value">
      {{ summary ? formatKas(summary.total_kas) : "0.00 KAS" }}
    </div>
    <div class="sub-value">
      {{ summary ? formatUsd(summary.kas_value_usd) : "N/A" }}
    </div>
    <div class="price-line">
      <span>KAS/USD</span>
      <span class="price">{{
        summary ? formatUsd(summary.kas_price_usd, 3) : "N/A"
      }}</span>
    </div>
  </div>
</template>

<style scoped>
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

.value {
  font-size: 1.5rem;
  font-weight: 700;
  font-family: "JetBrains Mono", monospace;
  letter-spacing: -0.02em;
  color: #fff;
}

.sub-value {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-family: "JetBrains Mono", monospace;
  margin-top: 0.25rem;
}

.price-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
  font-size: 0.78rem;
  color: var(--text-muted);
}

.price {
  color: var(--text-secondary);
  font-family: "JetBrains Mono", monospace;
}
</style>
