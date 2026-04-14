import { defineStore } from "pinia";
import { ref } from "vue";
import { useApi, ApiError } from "@/composables/useApi";
import type { SettingsResponse, SettingsUpdate } from "@/types/api";

export const useSettingsStore = defineStore("settings", () => {
  const refreshIntervalMinutes = ref<number | null>(15);
  const isLoading = ref(false);
  const isSaving = ref(false);
  const error = ref<string | null>(null);
  const savedMessage = ref<string | null>(null);

  let savedMessageTimer: ReturnType<typeof setTimeout> | null = null;

  async function fetchSettings(): Promise<void> {
    const api = useApi();
    isLoading.value = true;
    error.value = null;
    try {
      const data = await api.get<SettingsResponse>("/settings/");
      refreshIntervalMinutes.value = data.refresh_interval_minutes;
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function updateSettings(payload: SettingsUpdate): Promise<void> {
    const api = useApi();
    const previous = refreshIntervalMinutes.value;
    isSaving.value = true;
    error.value = null;
    savedMessage.value = null;
    try {
      const data = await api.put<SettingsResponse>("/settings/", payload);
      refreshIntervalMinutes.value = data.refresh_interval_minutes;
      savedMessage.value = "Settings saved.";
      if (savedMessageTimer !== null) {
        clearTimeout(savedMessageTimer);
      }
      savedMessageTimer = setTimeout(() => {
        savedMessage.value = null;
        savedMessageTimer = null;
      }, 1500);
    } catch (err) {
      refreshIntervalMinutes.value = previous;
      error.value =
        err instanceof ApiError
          ? err.detail
          : "Could not save settings. Please try again.";
      throw err;
    } finally {
      isSaving.value = false;
    }
  }

  return {
    refreshIntervalMinutes,
    isLoading,
    isSaving,
    error,
    savedMessage,
    fetchSettings,
    updateSettings,
  };
});
