import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/setup",
      name: "setup",
      component: () => import("@/views/SetupView.vue"),
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
    },
    {
      path: "/",
      name: "dashboard",
      component: () => import("@/views/DashboardView.vue"),
    },
    {
      path: "/wallet/:id",
      name: "wallet-detail",
      component: () => import("@/views/WalletDetailView.vue"),
    },
    {
      path: "/settings",
      name: "settings",
      component: () => import("@/views/SettingsView.vue"),
    },
  ],
});

const PUBLIC_ROUTES = ["/setup", "/login"];

router.beforeEach(async (to) => {
  const auth = useAuthStore();

  // Ensure auth state is initialized (fetches /api/auth/status once per app load)
  await auth.init();

  // No account exists — redirect everything to /setup
  if (auth.accountExists === false && to.path !== "/setup") {
    return "/setup";
  }

  // FR-059: account exists but unauthenticated user navigates to /setup — redirect to /login
  if (
    auth.accountExists === true &&
    !auth.isAuthenticated &&
    to.path === "/setup"
  ) {
    return "/login";
  }

  // Account exists but not authenticated — redirect to /login unless already on public route
  if (
    auth.accountExists === true &&
    !auth.isAuthenticated &&
    !PUBLIC_ROUTES.includes(to.path)
  ) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }

  // Authenticated users should not access /login or /setup
  if (auth.isAuthenticated && PUBLIC_ROUTES.includes(to.path)) {
    return "/";
  }
});

export default router;
