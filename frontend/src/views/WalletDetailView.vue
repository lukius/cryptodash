<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useWalletsStore } from "@/stores/wallets";
import { useApi, ApiError } from "@/composables/useApi";
import AppHeader from "@/components/layout/AppHeader.vue";
import CoinIcon from "@/components/common/CoinIcon.vue";
import LoadingSpinner from "@/components/common/LoadingSpinner.vue";
import WalletBalanceChart from "@/components/widgets/WalletBalanceChart.vue";
import EditTagInput from "@/components/wallet/EditTagInput.vue";
import RemoveWalletDialog from "@/components/wallet/RemoveWalletDialog.vue";
import type { TransactionResponse, WalletResponse } from "@/types/api";
import {
  formatUsd,
  formatBtc,
  formatKas,
  formatTimestamp,
  truncateAddress,
} from "@/utils/format";

const route = useRoute();
const router = useRouter();
const walletsStore = useWalletsStore();

const walletId = computed(() => route.params.id as string);
const wallet = computed<WalletResponse | null>(() =>
  walletsStore.getWalletById(walletId.value),
);

const unit = ref<"usd" | "native">("native");
const showRemoveDialog = ref(false);
const transactions = ref<TransactionResponse[]>([]);
const txLoading = ref(false);
const txError = ref<string | null>(null);
const isRetrying = ref(false);

function formatNativeBalance(w: WalletResponse): string {
  if (w.balance === null) return "Pending";
  return w.network === "BTC" ? formatBtc(w.balance) : formatKas(w.balance);
}

function formatAddedDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return "N/A";
  }
}

async function loadTransactions() {
  if (!wallet.value) return;
  txLoading.value = true;
  txError.value = null;
  const api = useApi();
  try {
    transactions.value = await api.get<TransactionResponse[]>(
      `/wallets/${walletId.value}/transactions`,
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      transactions.value = [];
    } else {
      txError.value =
        err instanceof ApiError ? err.detail : "Failed to load transactions.";
    }
  } finally {
    txLoading.value = false;
  }
}

async function retryHistoryImport() {
  isRetrying.value = true;
  try {
    await walletsStore.retryHistoryImport(walletId.value);
  } finally {
    isRetrying.value = false;
  }
}

async function copyAddress() {
  if (!wallet.value) return;
  await navigator.clipboard.writeText(wallet.value.address);
}

function explorerUrl(txHash: string, network: string): string {
  if (network === "BTC") {
    return `https://mempool.space/tx/${txHash}`;
  }
  return `https://explorer.kaspa.org/txs/${txHash}`;
}

function txType(amount: string): "in" | "out" {
  return parseFloat(amount) >= 0 ? "in" : "out";
}

function txAmountClass(amount: string): string {
  return parseFloat(amount) >= 0 ? "inflow" : "outflow";
}

function formatAmount(amount: string, network: string): string {
  const n = parseFloat(amount);
  const sign = n >= 0 ? "+" : "";
  if (network === "BTC") return `${sign}${formatBtc(Math.abs(n))}`;
  return `${sign}${formatKas(Math.abs(n))}`;
}

onMounted(async () => {
  if (!walletsStore.wallets.length) {
    await walletsStore.fetchWallets();
  }
  await loadTransactions();
});

function onWalletRemoved() {
  router.push("/");
}
</script>

<template>
  <div class="page">
    <AppHeader />

    <main class="main">
      <!-- Loading state -->
      <div v-if="walletsStore.isLoading" class="spinner-wrap">
        <LoadingSpinner />
      </div>

      <!-- Not found (only shown once loading is done) -->
      <template v-else-if="!wallet">
        <div class="not-found">
          <p class="not-found-msg">Wallet not found.</p>
          <router-link to="/" class="back-link">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Back to Dashboard
          </router-link>
        </div>
      </template>

      <template v-else>
        <!-- Back row -->
        <div class="back-row">
          <router-link to="/" class="back-link">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Back
          </router-link>
          <span class="breadcrumb"
            >/ <span>{{ wallet.tag }}</span></span
          >
        </div>

        <!-- Wallet hero -->
        <div class="wallet-hero">
          <div class="wallet-info">
            <div class="tag-row">
              <span class="wallet-tag-wrap">
                <EditTagInput :wallet-id="wallet.id" :tag="wallet.tag" />
              </span>
              <span
                class="network-badge"
                :class="wallet.network === 'BTC' ? 'btc' : 'kas'"
              >
                <CoinIcon :network="wallet.network" :size="14" />
                {{ wallet.network }}
              </span>
            </div>

            <div class="wallet-address-row">
              <span class="wallet-address" :title="wallet.address">{{
                truncateAddress(wallet.address, 12, 8)
              }}</span>
              <button
                class="copy-btn"
                title="Copy address"
                aria-label="Copy address"
                @click="copyAddress"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path
                    d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
                  />
                </svg>
              </button>
            </div>

            <div class="wallet-stats">
              <div class="stat-item">
                <div class="stat-label">Balance</div>
                <div class="stat-value">{{ formatNativeBalance(wallet) }}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">Value (USD)</div>
                <div class="stat-value">
                  {{
                    wallet.balance_usd !== null
                      ? formatUsd(wallet.balance_usd)
                      : "N/A"
                  }}
                </div>
              </div>
              <div class="stat-item">
                <div class="stat-label">Transactions</div>
                <div class="stat-value">
                  {{ txLoading ? "..." : transactions.length }}
                </div>
              </div>
              <div class="stat-item">
                <div class="stat-label">Added</div>
                <div class="stat-value stat-value-sm">
                  {{ formatAddedDate(wallet.created_at) }}
                </div>
              </div>
            </div>

            <div v-if="wallet.warning" class="warning-badge">
              {{ wallet.warning }}
            </div>
          </div>

          <div class="wallet-actions">
            <button
              v-if="wallet.history_status === 'failed'"
              class="btn-retry"
              :disabled="isRetrying"
              @click="retryHistoryImport"
            >
              {{ isRetrying ? "Retrying..." : "Retry History Import" }}
            </button>
            <button class="btn-danger" @click="showRemoveDialog = true">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                <path d="M10 11v6" />
                <path d="M14 11v6" />
                <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
              </svg>
              Delete Wallet
            </button>
          </div>
        </div>

        <!-- Balance chart — unit toggle lives inside the chart card header -->
        <WalletBalanceChart
          v-model:unit="unit"
          :wallet-id="wallet.id"
          :network="wallet.network"
          :show-unit-toggle="true"
        />

        <!-- Transaction timeline -->
        <div class="card tx-card">
          <div class="card-header">
            <h3>Transaction History</h3>
            <span v-if="!txLoading && !txError" class="tx-count">
              {{ transactions.length }}
              transaction{{ transactions.length !== 1 ? "s" : "" }}
            </span>
          </div>

          <div v-if="txLoading" class="tx-empty">Loading transactions...</div>
          <div v-else-if="txError" class="tx-empty tx-error">{{ txError }}</div>
          <div v-else-if="transactions.length === 0" class="tx-empty">
            No transactions yet.
          </div>
          <table v-else class="tx-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Transaction</th>
                <th>Type</th>
                <th class="text-right">Amount</th>
                <th class="text-right">Balance After</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tx in transactions" :key="tx.id">
                <td class="tx-date">{{ formatTimestamp(tx.timestamp) }}</td>
                <td>
                  <a
                    class="tx-hash"
                    :href="explorerUrl(tx.tx_hash, wallet.network)"
                    target="_blank"
                    rel="noopener noreferrer"
                    >{{ truncateAddress(tx.tx_hash, 8, 8) }}</a
                  >
                </td>
                <td>
                  <span :class="['tx-type-badge', txType(tx.amount)]">
                    {{ txType(tx.amount) === "in" ? "↑ IN" : "↓ OUT" }}
                  </span>
                </td>
                <td :class="['tx-amount', txAmountClass(tx.amount)]">
                  {{ formatAmount(tx.amount, wallet.network) }}
                </td>
                <td class="tx-balance">
                  {{
                    wallet.network === "BTC"
                      ? formatBtc(tx.balance_after)
                      : formatKas(tx.balance_after)
                  }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </main>

    <RemoveWalletDialog
      v-model="showRemoveDialog"
      :wallet="wallet"
      @wallet-removed="onWalletRemoved"
    />
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--bg);
}

.main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1.5rem;
}

.spinner-wrap {
  display: flex;
  justify-content: center;
  padding: 4rem 0;
}

.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 4rem 0;
}

.not-found-msg {
  font-size: 1.1rem;
  color: var(--text-secondary);
}

.back-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 1.5rem;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 0.82rem;
  font-weight: 500;
  text-decoration: none;
  transition: color 0.2s;
}

.back-link:hover {
  color: var(--accent);
}

.back-link svg {
  width: 16px;
  height: 16px;
}

.breadcrumb {
  color: var(--text-muted);
  font-size: 0.82rem;
}

.breadcrumb span {
  color: var(--text-secondary);
}

.wallet-hero {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem;
  backdrop-filter: blur(12px);
  margin-bottom: 1rem;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2rem;
  align-items: start;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.wallet-tag-wrap {
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #fff;
}

.network-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0.25rem 0.65rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 700;
  font-family: "JetBrains Mono", monospace;
}

.network-badge.btc {
  background: rgba(247, 147, 26, 0.1);
  color: var(--btc-color);
}

.network-badge.kas {
  background: rgba(73, 234, 203, 0.1);
  color: var(--kas-color);
}

.wallet-address-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 1.25rem;
}

.wallet-address {
  font-family: "JetBrains Mono", monospace;
  font-size: 0.82rem;
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.03);
  padding: 0.4rem 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--border);
  cursor: default;
}

.copy-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.35rem 0.5rem;
  transition: all 0.2s;
  display: flex;
  align-items: center;
}

.copy-btn:hover {
  color: var(--accent);
  border-color: var(--border-accent);
}

.copy-btn svg {
  width: 14px;
  height: 14px;
}

.wallet-stats {
  display: flex;
  gap: 2.5rem;
  flex-wrap: wrap;
}

.stat-item .stat-label {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 0.35rem;
}

.stat-item .stat-value {
  font-size: 1.3rem;
  font-weight: 700;
  font-family: "JetBrains Mono", monospace;
  color: #fff;
}

.stat-item .stat-value-sm {
  font-size: 1rem;
}

.warning-badge {
  margin-top: 0.75rem;
  font-size: 0.78rem;
  color: #f7931a;
  background: rgba(247, 147, 26, 0.08);
  border: 1px solid rgba(247, 147, 26, 0.2);
  border-radius: 6px;
  padding: 0.35rem 0.65rem;
  display: inline-block;
}

.wallet-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.btn-retry {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0.5rem 0.85rem;
  background: transparent;
  border: 1px solid rgba(73, 234, 203, 0.2);
  border-radius: var(--radius-sm);
  color: var(--accent);
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-retry:hover:not(:disabled) {
  background: var(--accent-dim);
  border-color: rgba(73, 234, 203, 0.4);
}

.btn-retry:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-danger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0.5rem 0.85rem;
  background: transparent;
  border: 1px solid rgba(255, 68, 68, 0.2);
  border-radius: var(--radius-sm);
  color: var(--red);
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-danger:hover {
  background: var(--red-dim);
  border-color: rgba(255, 68, 68, 0.4);
}

.btn-danger svg {
  width: 14px;
  height: 14px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  backdrop-filter: blur(12px);
  margin-bottom: 1rem;
}

.tx-card {
  padding: 0;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border);
}

.card-header h3 {
  font-size: 0.95rem;
  font-weight: 600;
}

.tx-count {
  font-size: 0.78rem;
  color: var(--text-muted);
  font-family: "JetBrains Mono", monospace;
}

.tx-empty {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.85rem;
}

.tx-error {
  color: var(--red);
}

.tx-table {
  width: 100%;
  border-collapse: collapse;
}

.tx-table thead th {
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
}

.tx-table thead th.text-right {
  text-align: right;
}

.tx-table tbody tr {
  transition: background 0.15s;
}

.tx-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.tx-table tbody td {
  padding: 0.85rem 1rem;
  font-size: 0.85rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  vertical-align: middle;
}

.tx-hash {
  font-family: "JetBrains Mono", monospace;
  font-size: 0.78rem;
  color: var(--accent);
  text-decoration: none;
}

.tx-hash:hover {
  text-decoration: underline;
}

.tx-date {
  font-family: "JetBrains Mono", monospace;
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.tx-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0.2rem 0.5rem;
  border-radius: 6px;
  font-size: 0.7rem;
  font-weight: 600;
  font-family: "JetBrains Mono", monospace;
}

.tx-type-badge.in {
  background: var(--green-dim);
  color: var(--green);
}

.tx-type-badge.out {
  background: var(--red-dim);
  color: var(--red);
}

.tx-amount {
  font-family: "JetBrains Mono", monospace;
  font-weight: 600;
  text-align: right;
}

.tx-amount.inflow {
  color: var(--green);
}

.tx-amount.outflow {
  color: var(--red);
}

.tx-balance {
  font-family: "JetBrains Mono", monospace;
  font-size: 0.82rem;
  color: var(--text-secondary);
  text-align: right;
}

@media (max-width: 768px) {
  .wallet-hero {
    grid-template-columns: 1fr;
  }

  .wallet-actions {
    align-items: flex-start;
    flex-direction: row;
    flex-wrap: wrap;
  }

  .wallet-stats {
    gap: 1.5rem;
  }

  .tx-card {
    overflow-x: auto;
  }
}
</style>
