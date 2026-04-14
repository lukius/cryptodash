<template>
  <div class="derived-address-list">
    <!-- Loading state -->
    <div v-if="loading" class="derived-loading">
      <LoadingSpinner />
    </div>

    <!-- Error state (API failure for derived list) -->
    <div v-else-if="error" class="derived-error">
      Could not load address breakdown. Will retry on next refresh.
    </div>

    <!-- Empty state -->
    <div v-else-if="!addresses || addresses.length === 0" class="derived-empty">
      No transactions found for this HD wallet yet.
    </div>

    <!-- Address table -->
    <template v-else>
      <table class="derived-table">
        <thead class="derived-thead">
          <tr>
            <th class="derived-th derived-th-left">Address</th>
            <th class="derived-th derived-th-right">BTC</th>
            <th class="derived-th derived-th-right">USD</th>
          </tr>
        </thead>
        <tbody class="derived-tbody">
          <tr v-for="addr in addresses" :key="addr.address" class="derived-row">
            <td class="derived-td derived-td-addr">
              <span :title="addr.address" class="derived-addr-text">
                {{ formatAddress(addr.address) }}
              </span>
            </td>
            <td class="derived-td derived-td-right">
              {{ formatBtc(addr.balance_native) }}
            </td>
            <td class="derived-td derived-td-right derived-td-usd">
              {{ addr.balance_usd ? formatUsd(addr.balance_usd) : "N/A" }}
            </td>
          </tr>
        </tbody>
      </table>
      <!-- "Showing top N of M" note (FR-H15) -->
      <div
        v-if="
          totalAddressCount !== null && totalAddressCount > addresses.length
        "
        class="derived-caption"
      >
        Showing top {{ addresses.length }} of {{ totalAddressCount }} addresses.
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import type { DerivedAddressResponse } from "@/types/api";
import LoadingSpinner from "@/components/common/LoadingSpinner.vue";
import { formatBtc, formatUsd } from "@/utils/format";

defineProps<{
  addresses: DerivedAddressResponse[] | null;
  totalAddressCount: number | null;
  loading: boolean;
  error: boolean;
}>();

function formatAddress(addr: string): string {
  // First 8 chars + "..." + last 6 chars (FR-H09)
  return addr.length > 14 ? `${addr.slice(0, 8)}...${addr.slice(-6)}` : addr;
}
</script>

<style scoped>
.derived-address-list {
  margin-top: 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  overflow: hidden;
}

.derived-loading {
  display: flex;
  justify-content: center;
  padding: 1rem;
}

.derived-error {
  font-size: 0.875rem;
  color: #ff4444;
  padding: 0.75rem 1rem;
}

.derived-empty {
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.38);
  padding: 0.75rem 1rem;
}

.derived-table {
  width: 100%;
  font-size: 0.875rem;
  border-collapse: collapse;
}

.derived-thead {
  background: rgba(255, 255, 255, 0.04);
}

.derived-th {
  padding: 0.5rem 1rem;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(255, 255, 255, 0.38);
}

.derived-th-left {
  text-align: left;
}

.derived-th-right {
  text-align: right;
}

.derived-tbody tr + tr {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.derived-row {
  transition: background 0.15s;
}

.derived-row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.derived-td {
  padding: 0.5rem 1rem;
}

.derived-td-addr {
  font-family: monospace;
  font-size: 0.75rem;
}

.derived-td-right {
  text-align: right;
  color: rgba(255, 255, 255, 0.87);
}

.derived-td-usd {
  color: rgba(255, 255, 255, 0.6);
}

.derived-addr-text {
  cursor: help;
}

.derived-caption {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.38);
  padding: 0.5rem 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
</style>
