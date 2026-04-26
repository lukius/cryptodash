import { defineStore } from "pinia";
import { ref } from "vue";
import { useApi, ApiError } from "@/composables/useApi";
import type { SettingsResponse, SettingsUpdate } from "@/types/api";

export const useSettingsStore = defineStore("settings", () => {
  const refreshIntervalMinutes = ref<number | null>(15);
  const preferredTimezone = ref<string>("UTC");
  const isLoading = ref(false);
  const isSaving = ref(false);
  const error = ref<string | null>(null);
  const savedMessage = ref<string | null>(null);
  const loaded = ref(false);

  let savedMessageTimer: ReturnType<typeof setTimeout> | null = null;

  async function fetchSettings(): Promise<void> {
    const api = useApi();
    isLoading.value = true;
    error.value = null;
    try {
      const data = await api.get<SettingsResponse>("/settings/");
      refreshIntervalMinutes.value = data.refresh_interval_minutes;
      preferredTimezone.value = data.preferred_timezone ?? "UTC";
    } catch (err) {
      error.value = err instanceof ApiError ? err.detail : String(err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function updateSettings(payload: SettingsUpdate): Promise<void> {
    const api = useApi();
    const previousInterval = refreshIntervalMinutes.value;
    const previousTz = preferredTimezone.value;
    isSaving.value = true;
    error.value = null;
    savedMessage.value = null;
    try {
      const data = await api.put<SettingsResponse>("/settings/", payload);
      refreshIntervalMinutes.value = data.refresh_interval_minutes;
      preferredTimezone.value = data.preferred_timezone ?? "UTC";
      savedMessage.value = "Settings saved.";
      if (savedMessageTimer !== null) {
        clearTimeout(savedMessageTimer);
      }
      savedMessageTimer = setTimeout(() => {
        savedMessage.value = null;
        savedMessageTimer = null;
      }, 1500);
    } catch (err) {
      refreshIntervalMinutes.value = previousInterval;
      preferredTimezone.value = previousTz;
      error.value =
        err instanceof ApiError
          ? err.detail
          : "Could not save settings. Please try again.";
      throw err;
    } finally {
      isSaving.value = false;
    }
  }

  async function init(): Promise<void> {
    if (loaded.value) return;
    loaded.value = true;
    try {
      await fetchSettings();
    } catch {
      loaded.value = false;
    }
  }

  return {
    refreshIntervalMinutes,
    preferredTimezone,
    isLoading,
    isSaving,
    error,
    savedMessage,
    fetchSettings,
    updateSettings,
    init,
  };
});
