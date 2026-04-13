<script setup lang="ts">
defineProps<{
  message: string;
}>();
</script>

<template>
  <div class="empty-state">
    <div class="empty-icon">
      <slot name="icon" />
    </div>
    <p class="empty-message">{{ message }}</p>
    <div v-if="$slots.action" class="empty-action">
      <slot name="action" />
    </div>
  </div>
</template>
