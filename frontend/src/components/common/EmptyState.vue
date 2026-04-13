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

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 5rem 1rem;
  text-align: center;
}

.empty-message {
  color: var(--text-secondary);
  font-size: 0.95rem;
  margin: 0 0 1.5rem;
}

.empty-action {
  display: flex;
  justify-content: center;
}
</style>
