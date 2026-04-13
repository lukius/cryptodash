<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";
import { useRouter } from "vue-router";

const emit = defineEmits<{
  (e: "refresh"): void;
}>();

const auth = useAuthStore();
const router = useRouter();

async function onLogout() {
  await auth.logout();
  router.push("/login");
}
</script>

<template>
  <header v-if="auth.isAuthenticated" class="app-header">
    <div class="header-left">
      <router-link to="/" class="header-logo">
        <img src="/favicon.svg" alt="" class="logo-mark" />
        <span class="logo-title"><span class="logo-crypto">Crypto</span><span class="logo-dash">Dash</span></span>
      </router-link>
    </div>
    <div class="header-right">
      <button class="header-btn accent" @click="emit('refresh')">
        Refresh
      </button>
      <router-link to="/settings" class="header-btn">Settings</router-link>
      <button class="header-btn" @click="onLogout">Logout</button>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  height: var(--header-h);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  background: linear-gradient(
    90deg,
    rgba(6, 11, 20, 0.95),
    rgba(10, 18, 35, 0.95) 40%,
    rgba(20, 35, 55, 0.9)
  );
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.header-left {
  display: flex;
  align-items: center;
}

.header-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
}

.logo-mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  box-shadow: 0 0 24px var(--accent-glow);
  flex-shrink: 0;
}

.logo-title {
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.logo-crypto {
  color: var(--btc-color);
}

.logo-dash {
  color: var(--kas-color);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0.5rem 0.85rem;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
}

.header-btn:hover {
  border-color: rgba(255, 255, 255, 0.15);
  color: var(--text);
  background: rgba(255, 255, 255, 0.03);
}

.header-btn.accent {
  border-color: var(--border-accent);
  color: var(--accent);
}

.header-btn.accent:hover {
  background: var(--accent-dim);
  box-shadow: 0 0 20px rgba(73, 234, 203, 0.08);
}
</style>
