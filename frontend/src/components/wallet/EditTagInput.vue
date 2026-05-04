<script setup lang="ts">
import { ref, nextTick } from "vue";
import { useWalletsStore } from "@/stores/wallets";
import { ApiError } from "@/composables/useApi";

const props = defineProps<{
  walletId: string;
  tag: string;
}>();

const store = useWalletsStore();

const editing = ref(false);
const inputValue = ref(props.tag);
const error = ref<string | null>(null);
const inputRef = ref<HTMLInputElement | null>(null);

async function startEditing() {
  inputValue.value = props.tag;
  error.value = null;
  editing.value = true;
  await nextTick();
  inputRef.value?.focus();
  inputRef.value?.select();
}

function cancel() {
  editing.value = false;
  inputValue.value = props.tag;
  error.value = null;
}

async function confirm() {
  const newTag = inputValue.value.trim();

  if (newTag.length === 0) {
    error.value = "Tag cannot be empty.";
    return;
  }

  if (newTag.length > 50) {
    error.value = "Tag must be 50 characters or fewer.";
    return;
  }

  if (newTag === props.tag) {
    editing.value = false;
    error.value = null;
    return;
  }

  try {
    await store.updateTag(props.walletId, newTag);
    editing.value = false;
    error.value = null;
  } catch (err) {
    if (err instanceof ApiError) {
      error.value = err.detail;
    } else {
      error.value = "Failed to update tag.";
    }
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Enter") {
    event.preventDefault();
    confirm();
  } else if (event.key === "Escape") {
    cancel();
  }
}
</script>

<template>
  <span class="edit-tag-input">
    <template v-if="!editing">
      <span class="tag-display">
        <span class="tag-text">{{ tag }}</span>
        <button
          type="button"
          class="edit-btn"
          title="Edit tag"
          aria-label="Edit tag"
          @click.stop="startEditing"
        >
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path
              d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
            />
            <path
              d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"
            />
          </svg>
        </button>
      </span>
    </template>
    <template v-else>
      <input
        ref="inputRef"
        v-model="inputValue"
        type="text"
        maxlength="50"
        class="tag-input"
        :class="{ 'tag-input-error': error }"
        @keydown="onKeydown"
        @blur="confirm"
      />
      <button
        type="button"
        class="confirm-btn"
        title="Confirm"
        aria-label="Confirm tag"
        @mousedown.prevent="confirm"
      >
        <svg
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </button>
      <button
        type="button"
        class="cancel-btn"
        title="Cancel"
        aria-label="Cancel edit"
        @mousedown.prevent="cancel"
      >
        <svg
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
      <span v-if="error" class="inline-error">{{ error }}</span>
    </template>
  </span>
</template>

<style scoped>
.edit-tag-input {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.tag-display {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  flex-wrap: nowrap;
}

.tag-text {
  color: rgba(255, 255, 255, 0.87);
  font-weight: 500;
}

.edit-btn {
  background: transparent;
  border: none;
  padding: 2px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.38);
  display: inline-flex;
  align-items: center;
  border-radius: 4px;
  transition: color 0.2s;
}

.edit-btn:hover {
  color: rgba(73, 234, 203, 0.8);
}

.tag-input {
  padding: 0.3rem 0.5rem;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(73, 234, 203, 0.4);
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.87);
  font-family: inherit;
  font-size: inherit;
  outline: none;
  min-width: 120px;
}

.tag-input-error {
  border-color: rgba(255, 68, 68, 0.5);
}

.confirm-btn,
.cancel-btn {
  background: transparent;
  border: none;
  padding: 2px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  border-radius: 4px;
  transition: color 0.2s;
}

.confirm-btn {
  color: #49eacb;
}

.confirm-btn:hover {
  color: #3bc4a8;
}

.cancel-btn {
  color: rgba(255, 255, 255, 0.38);
}

.cancel-btn:hover {
  color: #ff4444;
}

.inline-error {
  font-size: 0.72rem;
  color: #ff4444;
  width: 100%;
}
</style>
