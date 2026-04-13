<script setup lang="ts">
type TimeRange = "7d" | "30d" | "90d" | "1y" | "all";

const props = withDefaults(
  defineProps<{
    modelValue?: TimeRange;
  }>(),
  {
    modelValue: "30d",
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: TimeRange): void;
}>();

const ranges: { label: string; value: TimeRange }[] = [
  { label: "7d", value: "7d" },
  { label: "30d", value: "30d" },
  { label: "90d", value: "90d" },
  { label: "1y", value: "1y" },
  { label: "All", value: "all" },
];
</script>

<template>
  <div class="time-range">
    <button
      v-for="range in ranges"
      :key="range.value"
      :class="['time-range-btn', { active: props.modelValue === range.value }]"
      @click="emit('update:modelValue', range.value)"
    >
      {{ range.label }}
    </button>
  </div>
</template>

<style scoped>
.time-range {
  display: flex;
  gap: 2px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  padding: 3px;
}

.time-range-btn {
  padding: 0.3rem 0.6rem;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  font-family: "JetBrains Mono", monospace;
  font-size: 0.7rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.time-range-btn:hover {
  color: var(--text-secondary);
}

.time-range-btn.active {
  background: var(--accent-dim);
  color: var(--accent);
}
</style>
