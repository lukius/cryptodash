import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

// Mock useApi — the router calls auth.init() which calls useApi internally
vi.mock("@/composables/useApi", () => ({
  useApi: vi.fn(),
}));

import { useApi } from "@/composables/useApi";

function makeApi(overrides: Record<string, unknown> = {}) {
  return {
    get: vi.fn(),
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

  it("redirects unauthenticated user from /setup to /login when account exists (FR-059)", async () => {
    const api = makeApi({
      get: vi.fn().mockResolvedValue({
        account_exists: true,
        authenticated: false,
        username: null,
      }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const router = buildRouter();
    await router.push("/setup");

    expect(router.currentRoute.value.path).toBe("/login");
  });

  it("redirects unauthenticated user from protected route to /login with ?redirect param", async () => {
    const api = makeApi({
      get: vi.fn().mockResolvedValue({
        account_exists: true,
        authenticated: false,
        username: null,
      }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const router = buildRouter();
    await router.push("/");

    expect(router.currentRoute.value.path).toBe("/login");
    expect(router.currentRoute.value.query.redirect).toBe("/");
  });

  it("redirects authenticated user from /login to /", async () => {
    localStorage.setItem("auth_token", "valid-tok");
    const api = makeApi({
      get: vi.fn().mockResolvedValue({
        account_exists: true,
        authenticated: true,
        username: "satoshi",
      }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const router = buildRouter();
    await router.push("/login");

    expect(router.currentRoute.value.path).toBe("/");
  });

  it("redirects any route to /setup when no account exists", async () => {
    const api = makeApi({
      get: vi.fn().mockResolvedValue({
        account_exists: false,
        authenticated: false,
        username: null,
      }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const router = buildRouter();
    await router.push("/");

    expect(router.currentRoute.value.path).toBe("/setup");
  });

  it("allows authenticated user to access /settings", async () => {
    localStorage.setItem("auth_token", "valid-tok");
    const api = makeApi({
      get: vi.fn().mockResolvedValue({
        account_exists: true,
        authenticated: true,
        username: "satoshi",
      }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const router = buildRouter();
    await router.push("/settings");

    expect(router.currentRoute.value.path).toBe("/settings");
  });
});
