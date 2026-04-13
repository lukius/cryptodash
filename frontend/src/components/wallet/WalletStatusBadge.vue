<script setup lang="ts">
import { useWalletsStore } from "@/stores/wallets";
import type { WalletResponse } from "@/types/api";

const props = defineProps<{
  wallet: WalletResponse;
}>();

const store = useWalletsStore();

async function retryImport() {
  await store.retryHistoryImport(props.wallet.id);
}
</script>

<template>
  <!-- Warning takes highest priority -->
  <span
    v-if="wallet.warning"
    class="badge badge-warning"
    :title="wallet.warning"
  >
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path
        d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
      />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
    <span class="sr-only">Warning: {{ wallet.warning }}</span>
  </span>

  <!-- Importing: spinner -->
  <span
    v-else-if="wallet.history_status === 'importing'"
    class="badge badge-importing"
    title="Importing history..."
  >
    <svg
      class="spin"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2.5"
      stroke-linecap="round"
      aria-hidden="true"
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
    <span class="sr-only">Importing history</span>
  </span>

  <!-- Pending: clock -->
  <span
    v-else-if="wallet.history_status === 'pending'"
    class="badge badge-pending"
    title="History import pending"
  >
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
    <span class="sr-only">History import pending</span>
  </span>

  <!-- Failed: error icon + retry button -->
  <span
    v-else-if="wallet.history_status === 'failed'"
    class="badge badge-failed"
  >
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      title="History import failed"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
    <button type="button" class="retry-btn" @click="retryImport">Retry</button>
  </span>

  <!-- Complete with no warning: nothing -->
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.badge-warning {
  color: #f7931a;
  cursor: default;
}

.badge-importing {
  color: rgba(255, 255, 255, 0.5);
}

.badge-pending {
  color: rgba(255, 255, 255, 0.38);
}

.badge-failed {
  color: #ff4444;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.retry-btn {
  background: transparent;
  border: 1px solid rgba(255, 68, 68, 0.4);
  border-radius: 4px;
  color: #ff4444;
  font-family: inherit;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 1px 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-btn:hover {
  background: rgba(255, 68, 68, 0.1);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
</style>
