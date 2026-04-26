import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useSettingsStore } from "@/stores/settings";

// Mock useApi — the router calls auth.init() and settings.init() which call useApi internally
vi.mock("@/composables/useApi", () => ({
  useApi: vi.fn(),
}));

import { useApi } from "@/composables/useApi";

function makeApi(overrides: Record<string, unknown> = {}) {
  return {
    get: vi.fn().mockImplementation((url: string) => {
      if (url === "/settings/")
        return Promise.resolve({ refresh_interval_minutes: 15, preferred_timezone: "UTC" });
      return Promise.resolve({});
    }),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    ...overrides,
  };
}

// Build a router wired up with the real guard logic (copy of src/router/index.ts guard)
// We recreate the router here rather than importing the singleton so tests remain isolated.
function buildRouter() {
  const r = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/setup", name: "setup", component: { template: "<div/>" } },
      { path: "/login", name: "login", component: { template: "<div/>" } },
      { path: "/", name: "dashboard", component: { template: "<div/>" } },
      { path: "/wallet/:id", name: "wallet-detail", component: { template: "<div/>" } },
      { path: "/settings", name: "settings", component: { template: "<div/>" } },
    ],
  });

  const PUBLIC_ROUTES = ["/setup", "/login"];

  r.beforeEach(async (to) => {
    const auth = useAuthStore();
    await auth.init();

    if (auth.accountExists === false && to.path !== "/setup") {
      return "/setup";
    }

    // FR-059: account exists, unauthenticated, navigating to /setup → redirect to /login
    if (auth.accountExists === true && !auth.isAuthenticated && to.path === "/setup") {
      return "/login";
    }

    if (
      auth.accountExists === true &&
      !auth.isAuthenticated &&
      !PUBLIC_ROUTES.includes(to.path)
    ) {
      return { path: "/login", query: { redirect: to.fullPath } };
    }

    if (auth.isAuthenticated && PUBLIC_ROUTES.includes(to.path)) {
      return "/";
    }

    if (auth.isAuthenticated) {
      await useSettingsStore().init();
    }
  });

  return r;
}

describe("Router auth guard", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  function authApi(authStatus: Record<string, unknown>) {
    return makeApi({
      get: vi.fn().mockImplementation((url: string) => {
        if (url === "/auth/status") return Promise.resolve(authStatus);
        if (url === "/settings/")
          return Promise.resolve({ refresh_interval_minutes: 15, preferred_timezone: "UTC" });
        return Promise.resolve({});
      }),
    });
  }

  it("redirects unauthenticated user from /setup to /login when account exists (FR-059)", async () => {
    vi.mocked(useApi).mockReturnValue(
      authApi({ account_exists: true, authenticated: false, username: null }) as ReturnType<typeof useApi>
    );
    const router = buildRouter();
    await router.push("/setup");
    expect(router.currentRoute.value.path).toBe("/login");
  });

  it("redirects unauthenticated user from protected route to /login with ?redirect param", async () => {
    vi.mocked(useApi).mockReturnValue(
      authApi({ account_exists: true, authenticated: false, username: null }) as ReturnType<typeof useApi>
    );
    const router = buildRouter();
    await router.push("/");
    expect(router.currentRoute.value.path).toBe("/login");
    expect(router.currentRoute.value.query.redirect).toBe("/");
  });

  it("redirects authenticated user from /login to /", async () => {
    localStorage.setItem("auth_token", "valid-tok");
    vi.mocked(useApi).mockReturnValue(
      authApi({ account_exists: true, authenticated: true, username: "satoshi" }) as ReturnType<typeof useApi>
    );
    const router = buildRouter();
    await router.push("/login");
    expect(router.currentRoute.value.path).toBe("/");
  });

  it("redirects any route to /setup when no account exists", async () => {
    vi.mocked(useApi).mockReturnValue(
      authApi({ account_exists: false, authenticated: false, username: null }) as ReturnType<typeof useApi>
    );
    const router = buildRouter();
    await router.push("/");
    expect(router.currentRoute.value.path).toBe("/setup");
  });

  it("allows authenticated user to access /settings", async () => {
    localStorage.setItem("auth_token", "valid-tok");
    vi.mocked(useApi).mockReturnValue(
      authApi({ account_exists: true, authenticated: true, username: "satoshi" }) as ReturnType<typeof useApi>
    );
    const router = buildRouter();
    await router.push("/settings");
    expect(router.currentRoute.value.path).toBe("/settings");
  });

  it("loads preferred timezone before any authenticated page renders", async () => {
    localStorage.setItem("auth_token", "valid-tok");
    vi.mocked(useApi).mockReturnValue(
      makeApi({
        get: vi.fn().mockImplementation((url: string) => {
          if (url === "/auth/status")
            return Promise.resolve({ account_exists: true, authenticated: true, username: "satoshi" });
          if (url === "/settings/")
            return Promise.resolve({ refresh_interval_minutes: 15, preferred_timezone: "America/Sao_Paulo" });
          return Promise.resolve({});
        }),
      }) as ReturnType<typeof useApi>
    );

    const settingsStore = useSettingsStore();
    const router = buildRouter();

    await router.push("/wallet/abc");

    expect(router.currentRoute.value.path).toBe("/wallet/abc");
    expect(settingsStore.preferredTimezone).toBe("America/Sao_Paulo");
  });

  it("calls settings.init() only once across multiple navigations", async () => {
    localStorage.setItem("auth_token", "valid-tok");
    const getApi = vi.fn().mockImplementation((url: string) => {
      if (url === "/auth/status")
        return Promise.resolve({ account_exists: true, authenticated: true, username: "satoshi" });
      if (url === "/settings/")
        return Promise.resolve({ refresh_interval_minutes: 15, preferred_timezone: "UTC" });
      return Promise.resolve({});
    });
    vi.mocked(useApi).mockReturnValue(makeApi({ get: getApi }) as ReturnType<typeof useApi>);

    const router = buildRouter();
    await router.push("/");
    await router.push("/settings");
    await router.push("/wallet/abc");

    const settingsCalls = getApi.mock.calls.filter(([url]) => url === "/settings/");
    expect(settingsCalls).toHaveLength(1);
  });
});
