<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from "vue";
import { useDashboardStore } from "@/stores/dashboard";
import { useWalletsStore } from "@/stores/wallets";
import { useWebSocket } from "@/composables/useWebSocket";
import AppHeader from "@/components/layout/AppHeader.vue";
import AppFooter from "@/components/layout/AppFooter.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import LoadingSpinner from "@/components/common/LoadingSpinner.vue";
import AddWalletDialog from "@/components/wallet/AddWalletDialog.vue";
import RemoveWalletDialog from "@/components/wallet/RemoveWalletDialog.vue";
import TotalPortfolioValue from "@/components/widgets/TotalPortfolioValue.vue";
import TotalBtcBalance from "@/components/widgets/TotalBtcBalance.vue";
import TotalKasBalance from "@/components/widgets/TotalKasBalance.vue";
import WalletTable from "@/components/widgets/WalletTable.vue";
import PortfolioComposition from "@/components/widgets/PortfolioComposition.vue";
import PortfolioValueChart from "@/components/widgets/PortfolioValueChart.vue";
import PriceChart from "@/components/widgets/PriceChart.vue";
import WalletBalanceChart from "@/components/widgets/WalletBalanceChart.vue";
import type { WalletResponse } from "@/types/api";

type TimeRange = "7d" | "30d" | "90d" | "1y" | "all";

const dashboard = useDashboardStore();
const wallets = useWalletsStore();
const ws = useWebSocket();

const showAddWallet = ref(false);
const showRemoveWallet = ref(false);
const walletToRemove = ref<WalletResponse | null>(null);
const selectedWalletId = ref<string>("");

const selectedWallet = computed(
  () => wallets.wallets.find((w) => w.id === selectedWalletId.value) ?? null,
);

onMounted(async () => {
  ws.connect();
  await wallets.fetchWallets();
  if (wallets.wallets.length > 0 && !selectedWalletId.value) {
    selectedWalletId.value = wallets.wallets[0].id;
  }
  await Promise.allSettled([
    dashboard.fetchSummary(),
    dashboard.fetchPortfolioHistory(dashboard.selectedRange),
    dashboard.fetchComposition(),
    dashboard.fetchPriceHistory(dashboard.selectedRange),
  ]);
});

async function onRefresh() {
  await dashboard.triggerRefresh();
}

async function onRangeChange(range: TimeRange) {
  await dashboard.setRange(range);
}

function onRemoveWallet(wallet: WalletResponse) {
  walletToRemove.value = wallet;
  showRemoveWallet.value = true;
}

async function onWalletAdded() {
  await wallets.fetchWallets();
  if (!selectedWalletId.value && wallets.wallets.length > 0) {
    selectedWalletId.value = wallets.wallets[0].id;
  }
  await Promise.allSettled([
    dashboard.fetchSummary(),
    dashboard.fetchComposition(),
  ]);
}

async function onWalletRemoved() {
  await dashboard.fetchSummary();
  await dashboard.fetchComposition();
}

onUnmounted(() => {
  ws.disconnect();
});
</script>

<template>
  <div class="dashboard-layout">
    <AppHeader @refresh="onRefresh" />

    <main class="main">
      <!-- Empty state when no wallets -->
      <EmptyState
        v-if="wallets.count === 0 && !wallets.isLoading"
        message="No wallets tracked. Add a wallet to get started."
      >
        <template #action>
          <button
            class="btn-add-cta"
            type="button"
            @click="showAddWallet = true"
          >
            Add Wallet
          </button>
        </template>
      </EmptyState>

      <template v-else>
        <!-- Loading overlay for refresh -->
        <div v-if="dashboard.isRefreshing" class="refresh-indicator">
          <LoadingSpinner />
          <span>Refreshing...</span>
        </div>

        <!-- Row 1: Summary cards -->
        <div class="summary-row">
          <TotalPortfolioValue :summary="dashboard.summary" />
          <TotalBtcBalance :summary="dashboard.summary" />
          <TotalKasBalance :summary="dashboard.summary" />
        </div>

        <!-- Row 2: Portfolio chart + Composition pie -->
        <div class="charts-row">
          <PortfolioValueChart
            :portfolio-history="dashboard.portfolioHistory"
            :selected-range="dashboard.selectedRange"
            :unit="dashboard.portfolioUnit"
            @range-change="onRangeChange"
            @unit-change="dashboard.setPortfolioUnit($event)"
          />
          <PortfolioComposition :composition="dashboard.composition" />
        </div>

        <!-- Row 3: Per-wallet balance chart (W7) -->
        <div class="wallet-chart-row">
          <div class="card wallet-chart-card">
            <div class="wallet-chart-header">
              <span class="chart-section-title">Wallet Balance</span>
              <select
                v-if="wallets.wallets.length > 0"
                v-model="selectedWalletId"
                class="wallet-select"
              >
                <option v-for="w in wallets.wallets" :key="w.id" :value="w.id">
                  {{ w.tag }}
                </option>
              </select>
            </div>
            <WalletBalanceChart
              v-if="selectedWallet"
              :wallet-id="selectedWallet.id"
              :unit="'usd'"
              :network="selectedWallet.network"
            />
            <div v-else class="empty-chart-placeholder">
              No wallets to display.
            </div>
          </div>
        </div>

        <!-- Row 4: Price charts -->
        <PriceChart
          :price-history="dashboard.priceHistory"
          :selected-range="dashboard.selectedRange"
          @range-change="onRangeChange"
        />

        <!-- Row 4: Wallet Table -->
        <WalletTable
          @add-wallet="showAddWallet = true"
          @remove-wallet="onRemoveWallet"
        />
      </template>
    </main>

    <AppFooter
      :last-updated="dashboard.summary?.last_updated"
      :ws-connected="ws.isConnected.value"
    />

    <!-- Dialogs -->
    <AddWalletDialog v-model="showAddWallet" @wallet-added="onWalletAdded" />
    <RemoveWalletDialog
      v-model="showRemoveWallet"
      :wallet="walletToRemove"
      @wallet-removed="onWalletRemoved"
    />
  </div>
</template>

<style scoped>
.dashboard-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow-x: clip;
}

.main {
  flex: 1;
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.5rem;
  width: 100%;
}

.refresh-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
  color: var(--accent);
  font-size: 0.82rem;
}

.summary-row {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

.charts-row {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

.wallet-chart-row {
  margin-bottom: 1rem;
}

.wallet-chart-card {
  padding: 1.25rem;
}

.wallet-chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.chart-section-title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text);
}

.wallet-select {
  padding: 0.3rem 0.6rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-secondary);
  font-family: inherit;
  font-size: 0.8rem;
  outline: none;
  cursor: pointer;
}

.wallet-select:focus {
  border-color: var(--border-focus);
}

.wallet-select option {
  background: #0c1220;
}

.empty-chart-placeholder {
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.btn-add-cta {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #49eacb, #3bc4a8);
  border: none;
  border-radius: var(--radius-sm);
  color: #060b14;
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-add-cta:hover {
  box-shadow: 0 6px 24px rgba(73, 234, 203, 0.3);
}

@media (max-width: 1024px) {
  .summary-row {
    grid-template-columns: 1fr;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .main {
    padding: 1rem;
  }
}

@media (max-width: 480px) {
  .summary-row {
    gap: 0.75rem;
  }
}
</style>
