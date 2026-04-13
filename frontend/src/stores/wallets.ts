import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useApi, ApiError } from "@/composables/useApi";
import type {
  WalletResponse,
  WalletCreate,
  WalletListResponse,
} from "@/types/api";

export const useWalletsStore = defineStore("wallets", () => {
  const wallets = ref<WalletResponse[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const limit = ref(50);

  // Getters
  const count = computed(() => wallets.value.length);
  const isLimitReached = computed(() => count.value >= limit.value);
  const walletCount = computed(() => wallets.value.length);

  const btcWallets = computed(() =>
    wallets.value.filter((w) => w.network === "BTC"),
  );
  const kasWallets = computed(() =>
    wallets.value.filter((w) => w.network === "KAS"),
  );

  const totalBtcBalance = computed(() =>
    btcWallets.value.reduce((sum, w) => {
      const b = w.balance !== null ? parseFloat(w.balance) : 0;
      return sum + (isNaN(b) ? 0 : b);
    }, 0),
  );

  const totalKasBalance = computed(() =>
    kasWallets.value.reduce((sum, w) => {
      const b = w.balance !== null ? parseFloat(w.balance) : 0;
      return sum + (isNaN(b) ? 0 : b);
    }, 0),
  );

  function getWalletById(id: string): WalletResponse | null {
    return wallets.value.find((w) => w.id === id) ?? null;
  }

  // Actions
  async function fetchWallets(): Promise<void> {
    const api = useApi();
    isLoading.value = true;
    error.value = null;
    try {
      const data = await api.get<WalletListResponse>("/wallets/");
      wallets.value = data.wallets;
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
    } finally {
      isLoading.value = false;
    }
  }

  async function addWallet(payload: WalletCreate): Promise<WalletResponse> {
    const api = useApi();
    error.value = null;
    try {
      const wallet = await api.post<WalletResponse>("/wallets/", payload);
      wallets.value.push(wallet);
      return wallet;
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
      throw err;
    }
  }

  async function updateTag(walletId: string, tag: string): Promise<void> {
    const api = useApi();
    error.value = null;
    try {
      const updated = await api.patch<WalletResponse>(`/wallets/${walletId}`, {
        tag,
      });
      const idx = wallets.value.findIndex((w) => w.id === walletId);
      if (idx !== -1) {
        wallets.value[idx] = updated;
      }
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
      throw err;
    }
  }

  async function removeWallet(walletId: string): Promise<void> {
    const api = useApi();
    error.value = null;
    try {
      await api.delete<void>(`/wallets/${walletId}`);
      wallets.value = wallets.value.filter((w) => w.id !== walletId);
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
      throw err;
    }
  }

  async function retryHistoryImport(walletId: string): Promise<void> {
    const api = useApi();
    error.value = null;
    try {
      await api.post(`/wallets/${walletId}/retry-history`);
      const idx = wallets.value.findIndex((w) => w.id === walletId);
      if (idx !== -1) {
        wallets.value[idx] = {
          ...wallets.value[idx],
          history_status: "importing",
        };
      }
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
      throw err;
    }
  }

  // Hooks for T16 WebSocket integration
  function onWalletAdded(wallet: WalletResponse): void {
    if (!wallets.value.find((w) => w.id === wallet.id)) {
      wallets.value.push(wallet);
    }
  }

  function onWalletRemoved(walletId: string): void {
    wallets.value = wallets.value.filter((w) => w.id !== walletId);
  }

  function onWalletUpdated(wallet: WalletResponse): void {
    const idx = wallets.value.findIndex((w) => w.id === wallet.id);
    if (idx !== -1) {
      wallets.value[idx] = wallet;
    }
  }

  return {
    wallets,
    isLoading,
    error,
    limit,
    count,
    isLimitReached,
    walletCount,
    btcWallets,
    kasWallets,
    totalBtcBalance,
    totalKasBalance,
    getWalletById,
    fetchWallets,
    addWallet,
    updateTag,
    removeWallet,
    retryHistoryImport,
    onWalletAdded,
    onWalletRemoved,
    onWalletUpdated,
  };
});
