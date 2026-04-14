<script setup lang="ts">
import { ref, computed, nextTick } from "vue";
import { useWalletsStore } from "@/stores/wallets";
import {
  validateBtcAddress,
  validateKasAddress,
  detectBtcInputType,
} from "@/utils/validation";
import { ApiError } from "@/composables/useApi";

defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "wallet-added"): void;
}>();

const store = useWalletsStore();

const network = ref<"BTC" | "KAS">("BTC");
const address = ref("");
const tag = ref("");
const addressError = ref<string | null>(null);
const apiError = ref<string | null>(null);
const isSubmitting = ref(false);
const hasCommitted = ref(false);

const tagPlaceholder = computed(() => {
  const prefix = network.value === "BTC" ? "BTC" : "KAS";
  const n = store.wallets.filter((w) => w.network === network.value).length + 1;
  return `e.g. ${prefix} Wallet #${n}`;
});

const isExtendedKey = computed(
  () => network.value === "BTC" && detectBtcInputType(address.value) === "hd",
);

const addressLabel = computed(() =>
  hasCommitted.value && isExtendedKey.value
    ? "Extended public key (xpub/ypub/zpub)"
    : "Wallet address",
);

const addressPlaceholder = computed(() =>
  network.value === "BTC"
    ? "Bitcoin address or extended public key (xpub/ypub/zpub)"
    : "kaspa:...",
);

function selectNetwork(n: "BTC" | "KAS") {
  network.value = n;
  addressError.value = null;
  hasCommitted.value = false;
}

function validateAddress(): boolean {
  const raw = address.value.trim().replace(/\n/g, "").replace(/ /g, "");
  if (!raw) {
    addressError.value = "Please enter a wallet address.";
    return false;
  }
  // For BTC HD wallet inputs (xpub/ypub/zpub), skip client-side validation —
  // the backend performs full Base58Check verification (FR-H03).
  if (network.value === "BTC" && detectBtcInputType(raw) === "hd") {
    addressError.value = null;
    return true;
  }
  const err =
    network.value === "BTC" ? validateBtcAddress(raw) : validateKasAddress(raw);
  addressError.value = err;
  return err === null;
}

async function onAddressPaste() {
  hasCommitted.value = true;
  // Wait for v-model to sync the pasted value before validating, so we
  // validate the new content rather than whatever was there before the paste.
  await nextTick();
  validateAddress();
}

function onAddressBlur() {
  if (address.value.trim()) {
    hasCommitted.value = true;
    validateAddress();
  }
}

function close() {
  emit("update:modelValue", false);
}

async function submit() {
  apiError.value = null;
  if (!validateAddress()) return;

  const cleanAddress = address.value
    .trim()
    .replace(/\n/g, "")
    .replace(/ /g, "");
  const tagValue = tag.value.trim() || null;

  isSubmitting.value = true;
  try {
    await store.addWallet({
      network: network.value,
      address: cleanAddress,
      tag: tagValue,
    });
    emit("wallet-added");
    emit("update:modelValue", false);
    address.value = "";
    tag.value = "";
    addressError.value = null;
  } catch (err) {
    if (err instanceof ApiError) {
      apiError.value = err.detail;
    } else {
      apiError.value = "An unexpected error occurred.";
    }
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <div v-if="modelValue" class="modal-overlay" @click.self="close">
    <div
      class="modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      <h3 id="dialog-title">Add Wallet</h3>
      <p class="subtitle">
        Track a Bitcoin or Kaspa address. No private keys needed.
      </p>

      <div v-if="store.isLimitReached" class="limit-message">
        Wallet limit reached (50). Remove a wallet to add a new one.
      </div>

      <div class="form-group">
        <label>Network</label>
        <div class="network-select">
          <button
            type="button"
            class="pill"
            :class="{ 'active-btc': network === 'BTC' }"
            @click="selectNetwork('BTC')"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 4091.27 4091.73"
              aria-hidden="true"
            >
              <path
                fill="#F7931A"
                d="M4030.06 2540.77c-273.24,1096.01 -1383.32,1763.02 -2479.46,1489.71 -1095.68,-273.24 -1762.69,-1383.39 -1489.33,-2479.31 273.12,-1096.13 1383.2,-1763.19 2479,-1489.95 1096.06,273.24 1763.03,1383.51 1489.76,2479.57z"
              />
              <path
                fill="#FFF"
                d="M2947.77 1754.38c40.72,-272.26 -166.56,-418.61 -450,-516.24l91.95 -368.8 -224.5 -55.94 -89.51 359.09c-59.02,-14.72 -119.63,-28.59 -179.87,-42.34l90.16 -361.46 -224.36 -55.94 -92 368.68c-48.84,-11.12 -96.81,-22.11 -143.35,-33.69l0.26 -1.16 -309.59 -77.31 -59.72 239.78c0,0 166.56,38.18 163.05,40.53 90.91,22.69 107.35,82.87 104.62,130.57l-104.74 420.15c6.26,1.59 14.38,3.89 23.34,7.49 -7.49,-1.86 -15.46,-3.89 -23.73,-5.87l-146.81 588.57c-11.11,27.62 -39.31,69.07 -102.87,53.33 2.25,3.26 -163.17,-40.72 -163.17,-40.72l-111.46 256.98 292.15 72.83c54.35,13.63 107.61,27.89 160.06,41.3l-92.9 373.03 224.24 55.94 92 -369.07c61.26,16.63 120.71,31.97 178.91,46.43l-91.69 367.33 224.51 55.94 92.89 -372.33c382.82,72.45 670.67,43.24 791.83,-303.02 97.63,-278.78 -4.86,-439.58 -206.26,-544.44 146.69,-33.83 257.18,-130.31 286.64,-329.61zm-512.93 719.26c-69.38,278.78 -538.76,128.08 -690.94,90.29l123.28 -494.2c152.17,37.99 640.17,113.17 567.67,403.91zm69.43 -723.3c-63.29,253.58 -453.96,124.75 -580.69,93.16l111.77 -448.21c126.73,31.59 534.85,90.55 468.94,355.05z"
              />
            </svg>
            Bitcoin
          </button>
          <button
            type="button"
            class="pill"
            :class="{ 'active-kas': network === 'KAS' }"
            @click="selectNetwork('KAS')"
          >
            <svg
              width="14"
              height="14"
              viewBox="58 28 78 78"
              aria-hidden="true"
            >
              <path
                fill="#49EACB"
                d="M134.43,66.58c0,5.11-2.11,10.05-3.96,14.5-1.85,4.45-4.71,8.85-8.18,12.32-3.47,3.47-7.64,6.46-12.24,8.37-4.44,1.84-9.46,3.36-14.57,3.36-5.11,0-10.24-1.26-14.68-3.1-4.61-1.91-7.76-6.06-11.23-9.54-3.47-3.47-7.36-6.73-9.27-11.34-1.91-4.61-2.22-9.46-2.22-14.57 0-5.11-0.6-10.53 1.24-14.98 1.91-4.61 5.94-8.29 9.42-11.76 3.47-3.47 7.32-7.1 11.93-9.01 4.44-1.84 9.7-2.03 14.81-2.03 5.11,0 10.06,0.93 14.5,2.77 4.61,1.91 9.05,4.51 12.52,7.99 3.47,3.47 6.48,7.75 8.39,12.35 1.84,4.44 3.54,9.56 3.54,14.67z"
              />
              <polygon
                fill="#FFF"
                points="98.08,87.16 106.18,88.36 109.4,66.58 106.18,44.79 98.08,45.99 100.39,61.66 83.44,48.61 78.45,55.12 93.32,66.58 78.45,78.03 83.44,84.55 100.39,71.49"
              />
            </svg>
            Kaspa
          </button>
        </div>
      </div>

      <div class="form-group">
        <label for="wallet-address">{{ addressLabel }}</label>
        <textarea
          id="wallet-address"
          data-testid="address-input"
          v-model="address"
          :placeholder="addressPlaceholder"
          rows="2"
          :class="{ 'input-error': addressError }"
          @paste="onAddressPaste"
          @blur="onAddressBlur"
        />
        <div v-if="addressError" class="error-text">{{ addressError }}</div>
        <div v-else class="hint">
          Paste the public address you want to track
        </div>
        <div v-if="network === 'BTC'" class="hint trezor-hint">
          Find your extended public key in Trezor Suite under Account &rarr;
          Details &rarr; Show public key.
        </div>
      </div>

      <div class="form-group">
        <label for="wallet-tag">
          Tag
          <span class="optional">(optional)</span>
        </label>
        <input
          id="wallet-tag"
          v-model="tag"
          type="text"
          maxlength="50"
          :placeholder="tagPlaceholder"
        />
      </div>

      <div v-if="apiError" class="api-error">{{ apiError }}</div>

      <div class="btn-row">
        <button type="button" class="btn-cancel" @click="close">Cancel</button>
        <button
          type="button"
          class="btn-submit"
          :disabled="isSubmitting || store.isLimitReached"
          @click="submit"
        >
          {{ isSubmitting ? "Adding..." : "Add Wallet" }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
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

.modal {
  width: 100%;
  max-width: 460px;
  background: #0c1220;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 2rem;
  animation: fadeInUp 0.3s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

h3 {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 0.35rem;
  color: rgba(255, 255, 255, 0.87);
}

.subtitle {
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 1.5rem;
}

.limit-message {
  background: rgba(255, 68, 68, 0.1);
  border: 1px solid rgba(255, 68, 68, 0.3);
  border-radius: 10px;
  padding: 0.6rem 0.9rem;
  font-size: 0.82rem;
  color: #ff4444;
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

label {
  display: block;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 0.45rem;
}

.optional {
  text-transform: none;
  letter-spacing: 0;
  font-weight: 400;
}

input,
textarea {
  width: 100%;
  padding: 0.7rem 0.9rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.87);
  font-family: inherit;
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.2s;
  resize: none;
}

input:focus,
textarea:focus {
  border-color: rgba(73, 234, 203, 0.4);
}

.input-error {
  border-color: rgba(255, 68, 68, 0.5) !important;
}

.error-text {
  font-size: 0.72rem;
  color: #ff4444;
  margin-top: 0.3rem;
}

.hint {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.38);
  margin-top: 0.3rem;
}

.trezor-hint {
  margin-top: 0.5rem;
}

.api-error {
  background: rgba(255, 68, 68, 0.1);
  border: 1px solid rgba(255, 68, 68, 0.3);
  border-radius: 10px;
  padding: 0.6rem 0.9rem;
  font-size: 0.82rem;
  color: #ff4444;
  margin-bottom: 1rem;
}

.network-select {
  display: flex;
  gap: 0.5rem;
}

.pill {
  flex: 1;
  padding: 0.7rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.6);
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
}

.pill:hover {
  border-color: rgba(255, 255, 255, 0.12);
}

.pill.active-btc {
  border-color: rgba(247, 147, 26, 0.5);
  color: #f7931a;
  background: rgba(247, 147, 26, 0.06);
}

.pill.active-kas {
  border-color: rgba(73, 234, 203, 0.5);
  color: #49eacb;
  background: rgba(73, 234, 203, 0.06);
}

.btn-row {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.5rem;
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

.btn-submit {
  flex: 1;
  padding: 0.7rem;
  background: linear-gradient(135deg, #49eacb, #3bc4a8);
  border: none;
  border-radius: 10px;
  color: #060b14;
  font-family: inherit;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-submit:hover:not(:disabled) {
  box-shadow: 0 6px 24px rgba(73, 234, 203, 0.3);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
