import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useSettingsStore } from "@/stores/settings";

vi.mock("@/composables/useApi", () => ({
  useApi: vi.fn(),
  ApiError: class ApiError extends Error {
    readonly status: number;
    readonly detail: string;
    constructor(status: number, detail: string) {
      super(detail);
      this.name = "ApiError";
      this.status = status;
      this.detail = detail;
    }
  },
}));

vi.mock("@/router", () => ({
  default: { push: vi.fn() },
}));

import { useApi, ApiError } from "@/composables/useApi";

function makeApi(overrides: Record<string, unknown> = {}) {
  return {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    ...overrides,
  };
}

describe("useSettingsStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("has default state", () => {
    const store = useSettingsStore();
    expect(store.refreshIntervalMinutes).toBe(15);
    expect(store.isLoading).toBe(false);
    expect(store.isSaving).toBe(false);
    expect(store.error).toBeNull();
    expect(store.savedMessage).toBeNull();
  });

  describe("fetchSettings", () => {
    it("updates refreshIntervalMinutes on success", async () => {
      const api = makeApi({ get: vi.fn().mockResolvedValue({ refresh_interval_minutes: 30 }) });
      vi.mocked(useApi).mockReturnValue(api);

      const store = useSettingsStore();
      await store.fetchSettings();

      expect(api.get).toHaveBeenCalledWith("/settings/");
      expect(store.refreshIntervalMinutes).toBe(30);
      expect(store.isLoading).toBe(false);
      expect(store.error).toBeNull();
    });

    it("sets refreshIntervalMinutes to null when disabled", async () => {
      const api = makeApi({ get: vi.fn().mockResolvedValue({ refresh_interval_minutes: null }) });
      vi.mocked(useApi).mockReturnValue(api);

      const store = useSettingsStore();
      await store.fetchSettings();

      expect(store.refreshIntervalMinutes).toBeNull();
    });

    it("sets error and re-throws on failure", async () => {
      const api = makeApi({ get: vi.fn().mockRejectedValue(new ApiError(500, "Server error")) });
      vi.mocked(useApi).mockReturnValue(api);

      const store = useSettingsStore();
      await expect(store.fetchSettings()).rejects.toThrow("Server error");
      expect(store.error).toBe("Server error");
      expect(store.isLoading).toBe(false);
    });
  });

  describe("updateSettings", () => {
    it("updates state and shows savedMessage on success", async () => {
      const api = makeApi({ put: vi.fn().mockResolvedValue({ refresh_interval_minutes: 5 }) });
      vi.mocked(useApi).mockReturnValue(api);

      const store = useSettingsStore();
      await store.updateSettings({ refresh_interval_minutes: 5 });

      expect(api.put).toHaveBeenCalledWith("/settings/", { refresh_interval_minutes: 5 });
      expect(store.refreshIntervalMinutes).toBe(5);
      expect(store.savedMessage).toBe("Settings saved.");
      expect(store.isSaving).toBe(false);
    });

    it("clears savedMessage after 3 seconds", async () => {
      const api = makeApi({ put: vi.fn().mockResolvedValue({ refresh_interval_minutes: 15 }) });
      vi.mocked(useApi).mockReturnValue(api);

      const store = useSettingsStore();
      await store.updateSettings({ refresh_interval_minutes: 15 });

      expect(store.savedMessage).toBe("Settings saved.");
      vi.advanceTimersByTime(3000);
      expect(store.savedMessage).toBeNull();
    });

    it("reverts to previous value and sets error on failure", async () => {
      const api = makeApi({ put: vi.fn().mockRejectedValue(new ApiError(500, "DB error")) });
      vi.mocked(useApi).mockReturnValue(api);

      const store = useSettingsStore();
      store.refreshIntervalMinutes = 15;

      await expect(store.updateSettings({ refresh_interval_minutes: 5 })).rejects.toThrow();
      expect(store.refreshIntervalMinutes).toBe(15);
      expect(store.error).toBe("DB error");
      expect(store.isSaving).toBe(false);
    });

    it("sets refreshIntervalMinutes to null (disabled) on success", async () => {
      const api = makeApi({ put: vi.fn().mockResolvedValue({ refresh_interval_minutes: null }) });
      vi.mocked(useApi).mockReturnValue(api);

      const store = useSettingsStore();
      store.refreshIntervalMinutes = 15;

      await store.updateSettings({ refresh_interval_minutes: null });

      expect(api.put).toHaveBeenCalledWith("/settings/", { refresh_interval_minutes: null });
      expect(store.refreshIntervalMinutes).toBeNull();
      expect(store.savedMessage).toBe("Settings saved.");
    });
  });
});
