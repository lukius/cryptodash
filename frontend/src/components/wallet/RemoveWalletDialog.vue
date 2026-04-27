<script setup lang="ts">
import { ref } from "vue";
import { useWalletsStore } from "@/stores/wallets";
import type { WalletResponse } from "@/types/api";

const props = defineProps<{
  modelValue: boolean;
  wallet: WalletResponse | null;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "wallet-removed"): void;
}>();

const store = useWalletsStore();
const isRemoving = ref(false);
const error = ref<string | null>(null);

function close() {
  error.value = null;
  emit("update:modelValue", false);
}

async function confirm() {
  if (!props.wallet) return;
  isRemoving.value = true;
  error.value = null;
  try {
    await store.removeWallet(props.wallet.id);
    emit("wallet-removed");
    emit("update:modelValue", false);
  } catch (err) {
    error.value =
      err instanceof Error ? err.message : "Failed to remove wallet.";
  } finally {
    isRemoving.value = false;
  }
}
</script>

<template>
  <div v-if="modelValue && wallet" class="confirm-overlay" @click.self="close">
    <div
      class="confirm-box"
      role="dialog"
      aria-modal="true"
      aria-labelledby="remove-title"
    >
      <div class="icon" aria-hidden="true">
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <polyline points="3 6 5 6 21 6" />
          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
          <path d="M10 11v6" />
          <path d="M14 11v6" />
          <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
        </svg>
      </div>
      <h3 id="remove-title">Remove '{{ wallet.tag }}'?</h3>
      <p v-if="wallet.wallet_type === 'hd'">
        All historical data for this HD wallet will be deleted.
      </p>
      <p v-else>All historical data for this wallet will be deleted.</p>
      <div v-if="error" class="error-text">
        {{ error }}
      </div>
      <div class="btn-row">
        <button type="button" class="btn-cancel" @click="close">Cancel</button>
        <button
          type="button"
          class="btn-delete"
          :disabled="isRemoving"
          @click="confirm"
        >
          {{ isRemoving ? "Removing..." : "Remove Wallet" }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.confirm-box {
  width: 100%;
  max-width: 400px;
  background: #0c1220;
  border: 1px solid rgba(255, 68, 68, 0.15);
  border-radius: 16px;
  padding: 2rem;
  text-align: center;
}

.icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(255, 68, 68, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
  color: #ff4444;
}

h3 {
  font-size: 1.05rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: rgba(255, 255, 255, 0.87);
}

p {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 1.5rem;
  line-height: 1.5;
}

.error-text {
  font-size: 0.82rem;
  color: #ff4444;
  margin-bottom: 0.75rem;
}

.btn-row {
  display: flex;
  gap: 0.75rem;
}

.btn-cancel {
  flex: 1;
  padding: 0.7rem;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.6);
  font-family: inherit;
  font-size: 0.88rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  border-color: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.87);
}

.btn-delete {
  flex: 1;
  padding: 0.7rem;
  background: rgba(255, 68, 68, 0.15);
  border: 1px solid rgba(255, 68, 68, 0.3);
  border-radius: 10px;
  color: #ff4444;
  font-family: inherit;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-delete:hover:not(:disabled) {
  background: rgba(255, 68, 68, 0.25);
}

.btn-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
