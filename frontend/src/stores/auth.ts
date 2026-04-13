import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useApi } from "@/composables/useApi";
import router from "@/router";
import type { AuthStatusResponse, LoginResponse } from "@/types/api";

const TOKEN_KEY = "auth_token";

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(
    localStorage.getItem(TOKEN_KEY) ??
      sessionStorage.getItem(TOKEN_KEY) ??
      null,
  );
  const username = ref<string | null>(null);
  const accountExists = ref<boolean | null>(null);

  const isAuthenticated = computed(() => token.value !== null);

  function clearToken() {
    token.value = null;
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
  }

  function persistToken(newToken: string, rememberMe: boolean) {
    token.value = newToken;
    if (rememberMe) {
      localStorage.setItem(TOKEN_KEY, newToken);
      sessionStorage.removeItem(TOKEN_KEY);
    } else {
      sessionStorage.setItem(TOKEN_KEY, newToken);
      localStorage.removeItem(TOKEN_KEY);
    }
  }

  async function init() {
    if (accountExists.value !== null) return;

    const api = useApi();
    try {
      const status = await api.get<AuthStatusResponse>("/auth/status");
      accountExists.value = status.account_exists;
      if (status.authenticated) {
        username.value = status.username;
      } else {
        clearToken();
      }
    } catch {
      accountExists.value = false;
      clearToken();
    }
  }

  async function setup(
    usernameArg: string,
    password: string,
    passwordConfirm: string,
  ) {
    const api = useApi();
    const response = await api.post<LoginResponse>("/auth/setup", {
      username: usernameArg,
      password,
      password_confirm: passwordConfirm,
    });
    persistToken(response.token, false);
    username.value = usernameArg;
    accountExists.value = true;
  }

  async function login(
    usernameArg: string,
    password: string,
    rememberMe: boolean,
  ) {
    const api = useApi();
    const response = await api.post<LoginResponse>("/auth/login", {
      username: usernameArg,
      password,
      remember_me: rememberMe,
    });
    persistToken(response.token, rememberMe);
    username.value = usernameArg;
  }

  async function logout() {
    const api = useApi();
    try {
      await api.post("/auth/logout");
    } catch {
      // ignore errors on logout
    }
    clearToken();
    username.value = null;
    accountExists.value = null;
    router.push("/login");
  }

  return {
    token,
    username,
    accountExists,
    isAuthenticated,
    clearToken,
    init,
    setup,
    login,
    logout,
  };
});
