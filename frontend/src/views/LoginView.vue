<template>
  <div class="bg-effects">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
  </div>

  <div class="page">
    <div class="logo">
      <img src="/favicon.svg" alt="" class="logo-icon" />
      <div class="logo-text">
        <span class="cr">Crypto</span><span class="da">Dash</span>
      </div>
    </div>

    <div class="auth-card">
      <h2>Welcome back</h2>
      <p class="subtitle">Enter your credentials to access your dashboard.</p>

      <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>
      <div v-if="rateLimitMessage" class="rate-limit-banner">
        Too many failed attempts. Please wait
        <strong>{{ countdown }} second{{ countdown !== 1 ? "s" : "" }}</strong>
        before trying again.
      </div>

      <form @submit.prevent="handleSubmit" novalidate>
        <div class="form-group">
          <label for="login-username">Username</label>
          <input
            id="login-username"
            v-model="form.username"
            type="text"
            placeholder="Enter your username"
            autocomplete="username"
            :disabled="rateLimitActive"
          />
        </div>

        <div class="form-group">
          <label for="login-password">Password</label>
          <input
            id="login-password"
            v-model="form.password"
            type="password"
            placeholder="Enter your password"
            autocomplete="current-password"
            :disabled="rateLimitActive"
          />
        </div>

        <div class="form-options">
          <label class="checkbox-wrapper">
            <input v-model="form.rememberMe" type="checkbox" />
            <span>Remember me for 30 days</span>
          </label>
        </div>

        <button
          type="submit"
          class="btn-primary"
          :disabled="submitting || rateLimitActive"
        >
          {{ submitting ? "Signing in…" : "Sign In" }}
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
import { ref, computed, onUnmounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { ApiError } from "@/composables/useApi";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const form = ref({ username: "", password: "", rememberMe: false });
const errorMessage = ref("");
const rateLimitMessage = ref(false);
const countdown = ref(0);
const submitting = ref(false);

let countdownTimer: ReturnType<typeof setInterval> | null = null;

const rateLimitActive = computed(
  () => rateLimitMessage.value && countdown.value > 0,
);

function startCountdown(seconds: number) {
  countdown.value = seconds;
  rateLimitMessage.value = true;
  if (countdownTimer) clearInterval(countdownTimer);
  countdownTimer = setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) {
      if (countdownTimer) clearInterval(countdownTimer);
      rateLimitMessage.value = false;
    }
  }, 1000);
}

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer);
});

async function handleSubmit() {
  errorMessage.value = "";
  submitting.value = true;

  try {
    await auth.login(
      form.value.username,
      form.value.password,
      form.value.rememberMe,
    );

    const redirect = route.query.redirect;
    const target = typeof redirect === "string" && redirect ? redirect : "/";
    await router.push(target);
  } catch (err: unknown) {
    form.value.password = "";

    if (err instanceof ApiError && err.status === 429) {
      startCountdown(err.retryAfter ?? 30);
    } else {
      errorMessage.value = "Invalid username or password.";
    }
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
.form-group input[type="text"],
.form-group input[type="password"] {
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
.form-group input[type="text"]::placeholder,
.form-group input[type="password"]::placeholder {
  color: var(--text-muted);
}
.form-group input[type="text"]:focus,
.form-group input[type="password"]:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px rgba(73, 234, 203, 0.08);
}
.form-group input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.75rem;
}
.checkbox-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--text-secondary);
}
.checkbox-wrapper input[type="checkbox"] {
  appearance: none;
  width: 18px;
  height: 18px;
  border: 1px solid var(--border);
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.04);
  cursor: pointer;
  position: relative;
  transition: all 0.2s;
  flex-shrink: 0;
}
.checkbox-wrapper input[type="checkbox"]:checked {
  background: var(--accent);
  border-color: var(--accent);
}
.checkbox-wrapper input[type="checkbox"]:checked::after {
  content: "✓";
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  font-weight: 700;
  color: var(--bg);
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

.rate-limit-banner {
  background: rgba(247, 147, 26, 0.08);
  border: 1px solid rgba(247, 147, 26, 0.2);
  border-radius: var(--radius-sm);
  padding: 0.75rem 1rem;
  margin-bottom: 1.25rem;
  font-size: 0.85rem;
  color: var(--orange);
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
