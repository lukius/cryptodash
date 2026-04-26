<script setup lang="ts">
import { formatTimestamp } from "@/utils/format";
import { useSettingsStore } from "@/stores/settings";

const props = defineProps<{
  lastUpdated?: string | null;
  wsConnected?: boolean;
}>();

const settings = useSettingsStore();
</script>

<template>
  <footer class="app-footer">
    <span class="last-updated">
      Last updated: {{ formatTimestamp(props.lastUpdated, settings.preferredTimezone) }}
    </span>
    <span
      class="ws-indicator"
      :class="props.wsConnected ? 'connected' : 'disconnected'"
    >
      <span class="ws-dot" />
    </span>
  </footer>
</template>

<style scoped>
.app-footer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-top: 1px solid var(--border);
}

.last-updated {
  font-size: 0.72rem;
  color: var(--text-muted);
  font-family: "JetBrains Mono", monospace;
}

.ws-indicator {
  display: inline-flex;
  align-items: center;
}

.ws-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.connected .ws-dot {
  background-color: #22c55e;
}

.disconnected .ws-dot {
  background-color: #ef4444;
}
</style>
