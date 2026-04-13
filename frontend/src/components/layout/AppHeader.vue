<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";
import { useRouter } from "vue-router";

const emit = defineEmits<{
  (e: "refresh"): void;
}>();

const auth = useAuthStore();
const router = useRouter();

function onLogout() {
  auth.logout();
  router.push("/login");
}
</script>

<template>
  <header v-if="auth.isAuthenticated" class="app-header">
    <div class="header-left">
      <router-link to="/" class="header-logo">
        <span class="logo-mark">CD</span>
        <span class="logo-title">CryptoDash</span>
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
