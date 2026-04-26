<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useWalletsStore } from "@/stores/wallets";
import type { WalletResponse } from "@/types/api";
import {
  formatBtc,
  formatKas,
  formatUsd,
  formatWalletAddress,
} from "@/utils/format";
import WalletStatusBadge from "@/components/wallet/WalletStatusBadge.vue";
import EditTagInput from "@/components/wallet/EditTagInput.vue";
import CoinIcon from "@/components/common/CoinIcon.vue";
import HdBadge from "@/components/wallet/HdBadge.vue";
import DerivedAddressList from "@/components/wallet/DerivedAddressList.vue";

const emit = defineEmits<{
  (e: "add-wallet"): void;
  (e: "remove-wallet", wallet: WalletResponse): void;
}>();

const router = useRouter();
const store = useWalletsStore();

type SortKey = "tag" | "network" | "address" | "balance" | "balance_usd";
type SortDir = "asc" | "desc";

const sortKey = ref<SortKey>("tag");
const sortDir = ref<SortDir>("asc");

function setSort(key: SortKey) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  } else {
    sortKey.value = key;
    sortDir.value = "asc";
  }
}

function sortArrow(key: SortKey): string {
  if (sortKey.value !== key) return "↕";
  return sortDir.value === "asc" ? "↑" : "↓";
}

const sortedWallets = computed(() => {
  const wallets = [...store.wallets];
  wallets.sort((a, b) => {
    let aVal: string | number = "";
    let bVal: string | number = "";

    switch (sortKey.value) {
      case "tag":
        aVal = a.tag.toLowerCase();
        bVal = b.tag.toLowerCase();
        break;
      case "network":
        aVal = a.network.toLowerCase();
        bVal = b.network.toLowerCase();
        break;
      case "address":
        aVal = a.address.toLowerCase();
        bVal = b.address.toLowerCase();
        break;
      case "balance":
        aVal = a.balance !== null ? parseFloat(a.balance) : -Infinity;
        bVal = b.balance !== null ? parseFloat(b.balance) : -Infinity;
        break;
      case "balance_usd":
        aVal = a.balance_usd !== null ? parseFloat(a.balance_usd) : -Infinity;
        bVal = b.balance_usd !== null ? parseFloat(b.balance_usd) : -Infinity;
        break;
    }

    if (aVal < bVal) return sortDir.value === "asc" ? -1 : 1;
    if (aVal > bVal) return sortDir.value === "asc" ? 1 : -1;
    return 0;
  });
  return wallets;
});

function formatBalance(wallet: WalletResponse): string {
  if (wallet.balance === null) return "—";
  if (wallet.network === "BTC") return formatBtc(wallet.balance);
  return formatKas(wallet.balance);
}

const expandedWalletId = ref<string | null>(null);

function toggleExpand(walletId: string) {
  expandedWalletId.value =
    expandedWalletId.value === walletId ? null : walletId;
}

function navigateToWallet(wallet: WalletResponse) {
  router.push(`/wallet/${wallet.id}`);
}
</script>

<template>
  <div class="wallet-table-card card">
    <div class="card-header">
      <h3>Wallets</h3>
      <button class="btn-add-wallet" type="button" @click="emit('add-wallet')">
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          aria-hidden="true"
        >
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        Add Wallet
      </button>
    </div>

    <div class="table-wrapper">
      <table class="wallet-table">
        <thead>
          <tr>
            <th @click="setSort('tag')">
              Tag <span class="sort-arrow">{{ sortArrow("tag") }}</span>
            </th>
            <th @click="setSort('network')">
              Network <span class="sort-arrow">{{ sortArrow("network") }}</span>
            </th>
            <th @click="setSort('address')">
              Address <span class="sort-arrow">{{ sortArrow("address") }}</span>
            </th>
            <th style="text-align: right" @click="setSort('balance')">
              Balance <span class="sort-arrow">{{ sortArrow("balance") }}</span>
            </th>
            <th style="text-align: right" @click="setSort('balance_usd')">
              Value (USD)
              <span class="sort-arrow">{{ sortArrow("balance_usd") }}</span>
            </th>
            <th style="text-align: right"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="sortedWallets.length === 0">
            <td colspan="6" class="empty-row">
              No wallets tracked. Add a wallet to get started.
            </td>
          </tr>
          <template v-for="wallet in sortedWallets" :key="wallet.id">
            <tr @click="navigateToWallet(wallet)">
              <td class="tag-cell">
                <EditTagInput :wallet-id="wallet.id" :tag="wallet.tag" />
                <HdBadge v-if="wallet.wallet_type === 'hd'" />
                <WalletStatusBadge :wallet="wallet" />
              </td>
              <td>
                <span
                  :class="[
                    'network-badge',
                    wallet.network === 'BTC' ? 'btc' : 'kas',
                  ]"
                >
                  <CoinIcon :network="wallet.network" :size="14" />
                  {{ wallet.network }}
                </span>
              </td>
              <td class="address" :title="wallet.address">
                {{ formatWalletAddress(wallet.address, wallet.wallet_type) }}
              </td>
              <td class="balance">{{ formatBalance(wallet) }}</td>
              <td class="usd-val">{{ formatUsd(wallet.balance_usd) }}</td>
              <td class="actions">
                <button
                  v-if="wallet.wallet_type === 'hd'"
                  type="button"
                  class="action-btn expand-btn"
                  :aria-label="
                    expandedWalletId === wallet.id
                      ? 'Collapse address list'
                      : 'Expand address list'
                  "
                  :aria-expanded="expandedWalletId === wallet.id"
                  @click.stop="toggleExpand(wallet.id)"
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                    :class="{ 'rotate-180': expandedWalletId === wallet.id }"
                    class="chevron-icon"
                  >
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
                <button
                  type="button"
                  class="action-btn"
                  title="Remove wallet"
                  @click.stop="emit('remove-wallet', wallet)"
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
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                    <path d="M10 11v6" />
                    <path d="M14 11v6" />
                    <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                  </svg>
                </button>
              </td>
            </tr>
            <!-- Derived address expand row for HD wallets -->
            <tr
              v-if="wallet.wallet_type === 'hd'"
              :key="wallet.id + '-expand'"
              class="expand-row"
              @click.stop
            >
              <td colspan="6" class="expand-cell">
                <Transition name="expand">
                  <DerivedAddressList
                    v-if="expandedWalletId === wallet.id"
                    :addresses="wallet.derived_addresses"
                    :total-address-count="wallet.derived_address_total"
                    :loading="wallet.hd_loading"
                    :error="
                      !wallet.hd_loading &&
                      wallet.derived_addresses === null &&
                      wallet.warning !== null
                    "
                  />
                </Transition>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.wallet-table-card {
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

.btn-add-wallet {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0.45rem 0.85rem;
  background: var(--accent-dim);
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-sm);
  color: var(--accent);
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-add-wallet:hover {
  background: rgba(73, 234, 203, 0.18);
  box-shadow: 0 0 20px rgba(73, 234, 203, 0.1);
}

.table-wrapper {
  overflow-x: auto;
}

.wallet-table {
  width: 100%;
  border-collapse: collapse;
}

.wallet-table thead th {
  padding: 0.75rem 1.5rem;
  text-align: left;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.wallet-table thead th:hover {
  color: var(--text-secondary);
}

.sort-arrow {
  opacity: 0.4;
  margin-left: 4px;
  font-size: 0.65rem;
}

.wallet-table tbody tr {
  transition: background 0.15s;
  cursor: pointer;
}

.wallet-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.025);
}

.wallet-table tbody td {
  padding: 0.85rem 1.5rem;
  font-size: 0.88rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  white-space: nowrap;
}

.empty-row {
  text-align: center;
  color: var(--text-muted);
  padding: 2rem 1.5rem !important;
  cursor: default;
  white-space: normal !important;
}

.tag-cell {
  font-weight: 600;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.network-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 0.2rem 0.55rem;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 700;
  font-family: "JetBrains Mono", monospace;
}

.network-badge.btc {
  background: rgba(247, 147, 26, 0.1);
  color: var(--btc-color);
}

.network-badge.kas {
  background: rgba(73, 234, 203, 0.08);
  color: var(--kas-color);
}

.address {
  font-family: "JetBrains Mono", monospace;
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.balance {
  font-family: "JetBrains Mono", monospace;
  font-weight: 500;
  text-align: right;
}

.usd-val {
  font-family: "JetBrains Mono", monospace;
  color: var(--text-secondary);
  text-align: right;
}

.actions {
  text-align: right;
}

.action-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
}

.action-btn:hover {
  color: var(--red);
  background: var(--red-dim);
}

.expand-btn {
  margin-right: 4px;
}

.expand-btn:hover {
  color: var(--accent);
  background: var(--accent-dim);
}

.chevron-icon {
  transition: transform 0.2s ease;
}

.chevron-icon.rotate-180 {
  transform: rotate(180deg);
}

.expand-row {
  cursor: default;
}

.expand-row:hover {
  background: transparent;
}

.expand-cell {
  padding: 0 1.5rem !important;
}

.expand-enter-active,
.expand-leave-active {
  transition:
    opacity 0.2s ease,
    max-height 0.25s ease;
  overflow: hidden;
  max-height: 600px;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

@media (max-width: 768px) {
  .card-header {
    padding: 1rem 0.75rem;
  }

  .wallet-table thead th {
    padding: 0.65rem 0.75rem;
  }

  .wallet-table tbody td {
    padding: 0.75rem 0.75rem;
  }

  .expand-cell {
    padding: 0 0.75rem !important;
  }
}
</style>
