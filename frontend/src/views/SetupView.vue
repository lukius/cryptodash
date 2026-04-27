<template>
  <div class="bg-effects">
    <div class="orb orb-1" />
    <div class="orb orb-2" />
    <div class="orb orb-3" />
  </div>

  <div class="page">
    <div class="logo">
      <img src="/favicon.svg" alt="" class="logo-icon" />
      <div class="logo-text">
        <span class="cr">Crypto</span><span class="da">Dash</span>
      </div>
    </div>

    <div class="auth-card">
      <h2>Create your account</h2>
      <p class="subtitle">
        Set up CryptoDash for the first time. This is the only account — choose
        a strong password.
      </p>

      <div v-if="apiError" class="error-banner">
        {{ apiError }}
      </div>

      <form novalidate @submit.prevent="handleSubmit">
        <div class="form-group" :class="{ error: errors.username }">
          <label for="setup-username">Username</label>
          <input
            id="setup-username"
            v-model="form.username"
            type="text"
            placeholder="Choose a username"
            autocomplete="username"
          />
          <span v-if="errors.username" class="error-msg">{{
            errors.username
          }}</span>
        </div>

        <div class="form-group" :class="{ error: errors.password }">
          <label for="setup-password">Password</label>
          <input
            id="setup-password"
            v-model="form.password"
            type="password"
            placeholder="At least 8 characters"
            autocomplete="new-password"
            @input="onPasswordInput"
          />
          <div class="pw-strength">
            <div class="bar" :class="strengthBarClass(1)" />
            <div class="bar" :class="strengthBarClass(2)" />
            <div class="bar" :class="strengthBarClass(3)" />
            <div class="bar" :class="strengthBarClass(4)" />
          </div>
          <div class="pw-strength-label" :style="{ color: strengthColor }">
            {{ strengthLabel }}
          </div>
          <span v-if="errors.password" class="error-msg">{{
            errors.password
          }}</span>
        </div>

        <div class="form-group" :class="{ error: errors.passwordConfirm }">
          <label for="setup-password-confirm">Confirm Password</label>
          <input
            id="setup-password-confirm"
            v-model="form.passwordConfirm"
            type="password"
            placeholder="Re-enter your password"
            autocomplete="new-password"
          />
          <span v-if="errors.passwordConfirm" class="error-msg">{{
            errors.passwordConfirm
          }}</span>
        </div>

        <button
          type="submit"
          class="btn-primary"
          :disabled="submitting"
          style="margin-top: 0.5rem"
        >
          {{ submitting ? "Creating account…" : "Create Account" }}
        </button>
      </form>
    </div>

    <div class="auth-footer">
      Self-hosted crypto portfolio tracker &middot; No private keys, no third
      parties
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();

const form = ref({ username: "", password: "", passwordConfirm: "" });
const errors = ref({ username: "", password: "", passwordConfirm: "" });
const apiError = ref("");
const submitting = ref(false);

// ---- Password strength ----

const strengthScore = computed(() => {
  const pw = form.value.password;
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
  if (/[0-9]/.test(pw) || /[^a-zA-Z0-9]/.test(pw)) score++;
  return score;
});

const strengthLevels = [
  { label: "Password strength", color: "var(--text-muted)", cls: "" },
  { label: "Weak", color: "var(--red)", cls: "weak" },
  { label: "Fair", color: "var(--orange)", cls: "medium" },
  { label: "Good", color: "var(--green)", cls: "strong" },
  { label: "Strong", color: "var(--green)", cls: "strong" },
];

const strengthLabel = computed(() => strengthLevels[strengthScore.value].label);
const strengthColor = computed(() => strengthLevels[strengthScore.value].color);

function strengthBarClass(barIndex: number) {
  if (strengthScore.value === 0) return "";
  if (barIndex <= strengthScore.value) {
    return strengthLevels[strengthScore.value].cls;
  }
  return "";
}

function onPasswordInput() {
  if (errors.value.password) errors.value.password = "";
}

// ---- Validation ----

function validate(): boolean {
  errors.value = { username: "", password: "", passwordConfirm: "" };

  let valid = true;

  if (!form.value.username.trim()) {
    errors.value.username = "Username is required.";
    valid = false;
  }

  if (form.value.password.length < 8) {
    errors.value.password = "Password must be at least 8 characters.";
    valid = false;
  }

  if (form.value.password !== form.value.passwordConfirm) {
    errors.value.passwordConfirm = "Passwords do not match.";
    valid = false;
  }

  return valid;
}

// ---- Submit ----

async function handleSubmit() {
  apiError.value = "";
  if (!validate()) return;

  submitting.value = true;
  try {
    await auth.setup(
      form.value.username,
      form.value.password,
      form.value.passwordConfirm,
    );
    await router.push("/");
  } catch (err: unknown) {
    apiError.value =
      err instanceof Error
        ? err.message
        : "An error occurred. Please try again.";
    form.value.password = "";
    form.value.passwordConfirm = "";
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.bg-effects {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
}
.bg-effects::after {
  content: "";
  position: absolute;
  inset: 0;
  background-image: radial-gradient(
    rgba(255, 255, 255, 0.03) 1px,
    transparent 1px
  );
  background-size: 30px 30px;
  pointer-events: none;
}
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.35;
  animation: orbFloat 20s ease-in-out infinite alternate;
}
.orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(
    circle,
    rgba(73, 234, 203, 0.18),
    transparent 70%
  );
  top: -200px;
  right: -100px;
}
.orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(
    circle,
    rgba(73, 100, 234, 0.12),
    transparent 70%
  );
  bottom: -200px;
  left: -100px;
  animation-delay: -10s;
}
.orb-3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(
    circle,
    rgba(247, 147, 26, 0.08),
    transparent 70%
  );
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: -5s;
}
@keyframes orbFloat {
  0% {
    transform: translate(0, 0) scale(1);
  }
  33% {
    transform: translate(30px, -20px) scale(1.05);
  }
  66% {
    transform: translate(-20px, 30px) scale(0.95);
  }
  100% {
    transform: translate(10px, -10px) scale(1.02);
  }
}

.page {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 2rem;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 2.5rem;
  animation: fadeInDown 0.8s ease-out;
}
.logo-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  box-shadow:
    0 0 40px var(--accent-glow),
    0 0 80px rgba(73, 234, 203, 0.15);
}
.logo-text {
  font-size: 1.75rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: #fff;
}
.logo-text .cr {
  color: var(--orange);
}
.logo-text .da {
  color: var(--accent);
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2.5rem;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  animation: fadeInUp 0.6s ease-out;
}
.auth-card h2 {
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 0.35rem;
}
.auth-card .subtitle {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 2rem;
  line-height: 1.5;
}

.form-group {
  margin-bottom: 1.25rem;
}
.form-group label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}
.form-group input {
  width: 100%;
  padding: 0.8rem 1rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-family: inherit;
  font-size: 0.95rem;
  outline: none;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}
.form-group input::placeholder {
  color: var(--text-muted);
}
.form-group input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px rgba(73, 234, 203, 0.08);
}
.form-group.error input {
  border-color: rgba(255, 68, 68, 0.5);
}
.error-msg {
  display: block;
  font-size: 0.78rem;
  color: var(--red);
  margin-top: 0.4rem;
}

.error-banner {
  background: rgba(255, 68, 68, 0.08);
  border: 1px solid rgba(255, 68, 68, 0.2);
  border-radius: var(--radius-sm);
  padding: 0.75rem 1rem;
  margin-bottom: 1.25rem;
  font-size: 0.85rem;
  color: #ff6b6b;
}

.pw-strength {
  display: flex;
  gap: 4px;
  margin-top: 0.5rem;
}
.pw-strength .bar {
  flex: 1;
  height: 3px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.06);
  transition: background 0.3s;
}
.pw-strength .bar.weak {
  background: var(--red);
}
.pw-strength .bar.medium {
  background: var(--orange);
}
.pw-strength .bar.strong {
  background: var(--green);
}
.pw-strength-label {
  font-size: 0.72rem;
  margin-top: 0.35rem;
  transition: color 0.3s;
}

.btn-primary {
  width: 100%;
  padding: 0.85rem;
  background: linear-gradient(135deg, var(--accent), #3bc4a8);
  border: none;
  border-radius: var(--radius-sm);
  color: var(--bg);
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.25s;
}
.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow:
    0 8px 30px rgba(73, 234, 203, 0.3),
    0 0 60px rgba(73, 234, 203, 0.1);
}
.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-footer {
  margin-top: 2rem;
  text-align: center;
  font-size: 0.78rem;
  color: var(--text-muted);
  animation: fadeInUp 0.6s ease-out 0.2s both;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 480px) {
  .auth-card {
    padding: 1.75rem;
  }
  .logo-text {
    font-size: 1.5rem;
  }
}
</style>
