import { defineStore } from "pinia";
import { ref } from "vue";
import { useApi, ApiError } from "@/composables/useApi";
import type {
  PortfolioSummary,
  PortfolioHistoryResponse,
  PriceHistoryResponse,
  PortfolioComposition,
  WalletHistoryResponse,
} from "@/types/api";

type TimeRange = "7d" | "30d" | "90d" | "1y" | "all";

export const useDashboardStore = defineStore("dashboard", () => {
  const summary = ref<PortfolioSummary | null>(null);
  const portfolioHistory = ref<PortfolioHistoryResponse | null>(null);
  const priceHistory = ref<PriceHistoryResponse | null>(null);
  const composition = ref<PortfolioComposition | null>(null);
  const selectedRange = ref<TimeRange>("30d");
  const portfolioUnit = ref<"usd" | "btc" | "kas">("usd");
  const isRefreshing = ref(false);
  const error = ref<string | null>(null);

  async function fetchSummary(): Promise<void> {
    const api = useApi();
    try {
      summary.value = await api.get<PortfolioSummary>("/dashboard/summary");
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
      throw err;
    }
  }

  async function fetchPortfolioHistory(range: TimeRange): Promise<void> {
    const api = useApi();
    try {
      portfolioHistory.value = await api.get<PortfolioHistoryResponse>(
        `/dashboard/portfolio-history?range=${range}&unit=${portfolioUnit.value}`,
      );
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
      throw err;
    }
  }

  async function setPortfolioUnit(unit: "usd" | "btc" | "kas"): Promise<void> {
    portfolioUnit.value = unit;
    portfolioHistory.value = null;
    await fetchPortfolioHistory(selectedRange.value);
  }

  async function fetchPriceHistory(range: TimeRange): Promise<void> {
    const api = useApi();
    try {
      priceHistory.value = await api.get<PriceHistoryResponse>(
        `/dashboard/price-history?range=${range}`,
      );
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
      throw err;
    }
  }

  async function fetchComposition(): Promise<void> {
    const api = useApi();
    try {
      composition.value = await api.get<PortfolioComposition>(
        "/dashboard/composition",
      );
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
      throw err;
    }
  }

  async function fetchWalletHistory(
    walletId: string,
    range: TimeRange,
    unit: "usd" | "native",
  ): Promise<WalletHistoryResponse> {
    const api = useApi();
    try {
      return await api.get<WalletHistoryResponse>(
        `/dashboard/wallet-history/${walletId}?range=${range}&unit=${unit}`,
      );
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
      throw err;
    }
  }

  async function triggerRefresh(): Promise<void> {
    const api = useApi();
    isRefreshing.value = true;
    error.value = null;
    try {
      await api.post("/dashboard/refresh");
      await Promise.all([
        fetchSummary(),
        fetchPortfolioHistory(selectedRange.value),
        fetchPriceHistory(selectedRange.value),
        fetchComposition(),
      ]);
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
      throw err;
    } finally {
      isRefreshing.value = false;
    }
  }

  async function setRange(range: TimeRange): Promise<void> {
    selectedRange.value = range;
    portfolioHistory.value = null;
    priceHistory.value = null;
    await Promise.allSettled([
      fetchPortfolioHistory(range),
      fetchPriceHistory(range),
    ]);
  }

  return {
    summary,
    portfolioHistory,
    priceHistory,
    composition,
    selectedRange,
    portfolioUnit,
    isRefreshing,
    error,
    fetchSummary,
    fetchPortfolioHistory,
    fetchPriceHistory,
    fetchComposition,
    fetchWalletHistory,
    triggerRefresh,
    setRange,
    setPortfolioUnit,
  };
});
