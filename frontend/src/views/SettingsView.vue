<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useSettingsStore } from "@/stores/settings";
import AppHeader from "@/components/layout/AppHeader.vue";

const settings = useSettingsStore();
const router = useRouter();

type IntervalOption = { label: string; value: number | null };
type TimezoneOption = { label: string; value: string };

const intervalOptions: IntervalOption[] = [
  { label: "5 minutes", value: 5 },
  { label: "15 minutes", value: 15 },
  { label: "30 minutes", value: 30 },
  { label: "1 hour", value: 60 },
  { label: "Disabled", value: null },
];

const timezoneOptions: TimezoneOption[] = [
  { label: "UTC (GMT+0)", value: "UTC" },
  { label: "London (GMT+0/+1)", value: "Europe/London" },
  { label: "Paris / Berlin (GMT+1/+2)", value: "Europe/Paris" },
  { label: "Helsinki / Kyiv (GMT+2/+3)", value: "Europe/Helsinki" },
  { label: "Moscow (GMT+3)", value: "Europe/Moscow" },
  { label: "Dubai (GMT+4)", value: "Asia/Dubai" },
  { label: "Karachi (GMT+5)", value: "Asia/Karachi" },
  { label: "Kolkata (GMT+5:30)", value: "Asia/Kolkata" },
  { label: "Bangkok (GMT+7)", value: "Asia/Bangkok" },
  { label: "Singapore / Kuala Lumpur (GMT+8)", value: "Asia/Singapore" },
  { label: "Shanghai / Beijing (GMT+8)", value: "Asia/Shanghai" },
  { label: "Tokyo (GMT+9)", value: "Asia/Tokyo" },
  { label: "Seoul (GMT+9)", value: "Asia/Seoul" },
  { label: "Sydney (GMT+10/+11)", value: "Australia/Sydney" },
  { label: "Auckland (GMT+12/+13)", value: "Pacific/Auckland" },
  { label: "Honolulu (GMT-10)", value: "Pacific/Honolulu" },
  { label: "Anchorage (GMT-9/-8)", value: "America/Anchorage" },
  { label: "Los Angeles (GMT-8/-7)", value: "America/Los_Angeles" },
  { label: "Denver (GMT-7/-6)", value: "America/Denver" },
  { label: "Mexico City (GMT-6/-5)", value: "America/Mexico_City" },
  { label: "Chicago (GMT-6/-5)", value: "America/Chicago" },
  { label: "New York / Toronto (GMT-5/-4)", value: "America/New_York" },
  { label: "São Paulo (GMT-3/-2)", value: "America/Sao_Paulo" },
  { label: "Buenos Aires (GMT-3)", value: "America/Argentina/Buenos_Aires" },
];

const selected = ref<number | null>(settings.refreshIntervalMinutes);
const selectedTimezone = ref<string>(settings.preferredTimezone);
const fadingOut = ref(false);
let dismissTimer: ReturnType<typeof setTimeout> | null = null;

onMounted(async () => {
  try {
    await settings.fetchSettings();
    selected.value = settings.refreshIntervalMinutes;
    selectedTimezone.value = settings.preferredTimezone;
  } catch {
    // error shown via store.error
  }
});

onUnmounted(() => {
  if (dismissTimer !== null) clearTimeout(dismissTimer);
});

async function save() {
  settings.error = null;
  try {
    await settings.updateSettings({
      refresh_interval_minutes: selected.value,
      preferred_timezone: selectedTimezone.value,
    });
    dismissTimer = setTimeout(() => {
      fadingOut.value = true;
      setTimeout(() => void router.push("/"), 400);
    }, 1000);
  } catch {
    // error shown via store.error
  }
}
</script>

<template>
  <div class="page">
    <AppHeader />

    <main class="main">
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
          Back to Dashboard
        </router-link>
      </div>

      <div class="settings-card" :class="{ 'fading-out': fadingOut }">
        <h2 class="settings-title">Settings</h2>

        <div v-if="settings.isLoading" class="loading-msg">Loading...</div>

        <template v-else>
          <div class="field-group">
            <label class="field-label">Auto-refresh interval</label>
            <p class="field-hint">
              How often CryptoDash automatically fetches updated balances and
              prices.
            </p>
            <div class="radio-group">
              <label
                v-for="opt in intervalOptions"
                :key="String(opt.value)"
                class="radio-option"
                :class="{ active: selected === opt.value }"
              >
                <input
                  v-model="selected"
                  type="radio"
                  name="refresh-interval"
                  :value="opt.value"
                  class="radio-input"
                />
                <span class="radio-label">{{ opt.label }}</span>
              </label>
            </div>
          </div>

          <div class="field-group">
            <label class="field-label" for="tz-select"
              >Preferred timezone</label
            >
            <p class="field-hint">
              Timestamps throughout CryptoDash will be displayed in this
              timezone.
            </p>
            <select id="tz-select" v-model="selectedTimezone" class="tz-select">
              <option
                v-for="opt in timezoneOptions"
                :key="opt.value"
                :value="opt.value"
              >
                {{ opt.label }}
              </option>
            </select>
          </div>

          <div v-if="settings.error" class="error-msg">
            {{ settings.error }}
          </div>

          <div v-if="settings.savedMessage" class="success-msg">
            {{ settings.savedMessage }}
          </div>

          <button class="btn-save" :disabled="settings.isSaving" @click="save">
            {{ settings.isSaving ? "Saving..." : "Save" }}
          </button>
        </template>
      </div>
    </main>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  background: var(--bg);
}

.main {
  max-width: 640px;
  margin: 0 auto;
  padding: 1.5rem;
}

.back-row {
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

.settings-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem;
  backdrop-filter: blur(12px);
  transition: opacity 0.4s ease;
}

.settings-card.fading-out {
  opacity: 0;
}

.settings-title {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 1.75rem;
  color: var(--text);
}

.loading-msg {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.field-group {
  margin-bottom: 1.75rem;
}

.field-label {
  display: block;
  font-size: 0.82rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-muted);
  margin-bottom: 0.4rem;
}

.field-hint {
  font-size: 0.82rem;
  color: var(--text-secondary);
  margin-bottom: 1rem;
  line-height: 1.5;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 0.9rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s;
  background: transparent;
}

.radio-option:hover {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.02);
}

.radio-option.active {
  border-color: var(--border-accent);
  background: var(--accent-dim);
}

.radio-input {
  accent-color: var(--accent);
  width: 16px;
  height: 16px;
  cursor: pointer;
  flex-shrink: 0;
}

.radio-label {
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--text);
}

.error-msg {
  font-size: 0.82rem;
  color: var(--red);
  background: var(--red-dim);
  border: 1px solid rgba(255, 68, 68, 0.2);
  border-radius: var(--radius-sm);
  padding: 0.6rem 0.9rem;
  margin-bottom: 1rem;
}

.success-msg {
  font-size: 0.82rem;
  color: var(--green);
  background: var(--green-dim);
  border: 1px solid rgba(0, 230, 118, 0.2);
  border-radius: var(--radius-sm);
  padding: 0.6rem 0.9rem;
  margin-bottom: 1rem;
}

.tz-select {
  width: 100%;
  padding: 0.6rem 0.9rem;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-family: inherit;
  font-size: 0.88rem;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  padding-right: 2.25rem;
}

.tz-select:focus {
  outline: none;
  border-color: var(--border-accent);
}

.btn-save {
  padding: 0.65rem 1.5rem;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-sm);
  color: #060b14;
  font-family: inherit;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-save:hover:not(:disabled) {
  background: #3bc4a8;
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
