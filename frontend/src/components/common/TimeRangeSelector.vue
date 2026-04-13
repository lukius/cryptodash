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
