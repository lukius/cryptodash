import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "@/stores/auth";

// Mock useApi and router
vi.mock("@/composables/useApi", () => ({
  useApi: vi.fn(),
}));

vi.mock("@/router", () => ({
  default: {
    push: vi.fn(),
  },
}));

import { useApi } from "@/composables/useApi";
import router from "@/router";

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

describe("useAuthStore", () => {
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

  // ---- Initial state ----

  it("has token as null initially", () => {
    const store = useAuthStore();
    expect(store.token).toBeNull();
  });

  it("has username as null initially", () => {
    const store = useAuthStore();
    expect(store.username).toBeNull();
  });

  it("has accountExists as null initially", () => {
    const store = useAuthStore();
    expect(store.accountExists).toBeNull();
  });

  it("has isAuthenticated as false when token is null", () => {
    const store = useAuthStore();
    expect(store.isAuthenticated).toBe(false);
  });

  // ---- Token persistence on init ----

  it("reads token from localStorage on init", () => {
    localStorage.setItem("auth_token", "tok-local");
    const store = useAuthStore();
    expect(store.token).toBe("tok-local");
  });

  it("reads token from sessionStorage when localStorage is empty on init", () => {
    sessionStorage.setItem("auth_token", "tok-session");
    const store = useAuthStore();
    expect(store.token).toBe("tok-session");
  });

  it("prefers localStorage over sessionStorage on init", () => {
    localStorage.setItem("auth_token", "tok-local");
    sessionStorage.setItem("auth_token", "tok-session");
    const store = useAuthStore();
    expect(store.token).toBe("tok-local");
  });

  // ---- init() action ----

  it("init() sets accountExists=false and isAuthenticated=false when account does not exist", async () => {
    const api = makeApi({
      get: vi.fn().mockResolvedValue({
        account_exists: false,
        authenticated: false,
        username: null,
      }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    await store.init();

    expect(store.accountExists).toBe(false);
    expect(store.isAuthenticated).toBe(false);
    expect(store.username).toBeNull();
  });

  it("init() sets accountExists=true, username, and isAuthenticated based on response", async () => {
    localStorage.setItem("auth_token", "existing-tok");
    const api = makeApi({
      get: vi.fn().mockResolvedValue({
        account_exists: true,
        authenticated: true,
        username: "satoshi",
      }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    await store.init();

    expect(store.accountExists).toBe(true);
    expect(store.username).toBe("satoshi");
    expect(store.isAuthenticated).toBe(true);
  });

  it("init() clears token when server says not authenticated", async () => {
    localStorage.setItem("auth_token", "stale-tok");
    const api = makeApi({
      get: vi.fn().mockResolvedValue({
        account_exists: true,
        authenticated: false,
        username: null,
      }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    await store.init();

    expect(store.token).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(localStorage.getItem("auth_token")).toBeNull();
    expect(sessionStorage.getItem("auth_token")).toBeNull();
  });

  it("init() skips fetch if accountExists is already set", async () => {
    const api = makeApi({ get: vi.fn() });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    store.accountExists = true; // pre-set
    await store.init();

    expect(api.get).not.toHaveBeenCalled();
  });

  // ---- setup() action ----

  it("setup() calls POST /auth/setup and stores token in sessionStorage by default", async () => {
    const api = makeApi({
      post: vi.fn().mockResolvedValue({ token: "new-tok", expires_at: "2030-01-01T00:00:00Z" }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    await store.setup("alice", "password123", "password123");

    expect(api.post).toHaveBeenCalledWith("/auth/setup", {
      username: "alice",
      password: "password123",
      password_confirm: "password123",
    });
    expect(store.token).toBe("new-tok");
    expect(store.isAuthenticated).toBe(true);
    expect(store.accountExists).toBe(true);
    expect(sessionStorage.getItem("auth_token")).toBe("new-tok");
    expect(localStorage.getItem("auth_token")).toBeNull();
  });

  it("setup() throws if API call fails", async () => {
    const api = makeApi({
      post: vi.fn().mockRejectedValue(new Error("Account already exists")),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    await expect(store.setup("alice", "pass", "pass")).rejects.toThrow("Account already exists");
    expect(store.isAuthenticated).toBe(false);
  });

  // ---- login() action ----

  it("login() success stores token in sessionStorage when rememberMe=false", async () => {
    const api = makeApi({
      post: vi.fn().mockResolvedValue({ token: "sess-tok", expires_at: "2030-01-01T00:00:00Z" }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    await store.login("alice", "password123", false);

    expect(store.token).toBe("sess-tok");
    expect(store.isAuthenticated).toBe(true);
    expect(sessionStorage.getItem("auth_token")).toBe("sess-tok");
    expect(localStorage.getItem("auth_token")).toBeNull();
  });

  it("login() with rememberMe=true stores token in localStorage", async () => {
    const api = makeApi({
      post: vi.fn().mockResolvedValue({ token: "local-tok", expires_at: "2030-01-01T00:00:00Z" }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    await store.login("alice", "password123", true);

    expect(store.token).toBe("local-tok");
    expect(store.isAuthenticated).toBe(true);
    expect(localStorage.getItem("auth_token")).toBe("local-tok");
    expect(sessionStorage.getItem("auth_token")).toBeNull();
  });

  it("login() throws on 401 and clears token", async () => {
    const api = makeApi({
      post: vi.fn().mockRejectedValue(new Error("Invalid username or password")),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    await expect(store.login("alice", "wrong", false)).rejects.toThrow();
    expect(store.isAuthenticated).toBe(false);
    expect(store.token).toBeNull();
  });

  it("login() calls POST /auth/login with correct body", async () => {
    const api = makeApi({
      post: vi.fn().mockResolvedValue({ token: "tok", expires_at: "2030-01-01T00:00:00Z" }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    await store.login("satoshi", "mypassword", true);

    expect(api.post).toHaveBeenCalledWith("/auth/login", {
      username: "satoshi",
      password: "mypassword",
      remember_me: true,
    });
  });

  // ---- logout() action ----

  it("logout() clears token from both storages and resets state", async () => {
    localStorage.setItem("auth_token", "local-tok");
    sessionStorage.setItem("auth_token", "session-tok");

    const api = makeApi({
      post: vi.fn().mockResolvedValue({ ok: true }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    store.token = "local-tok";
    store.username = "alice";

    await store.logout();

    expect(store.token).toBeNull();
    expect(store.username).toBeNull();
    expect(localStorage.getItem("auth_token")).toBeNull();
    expect(sessionStorage.getItem("auth_token")).toBeNull();
  });

  it("logout() calls POST /auth/logout", async () => {
    const api = makeApi({
      post: vi.fn().mockResolvedValue({ ok: true }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    store.token = "some-tok";
    await store.logout();

    expect(api.post).toHaveBeenCalledWith("/auth/logout");
  });

  it("logout() resets accountExists to null", async () => {
    const api = makeApi({
      post: vi.fn().mockResolvedValue({ ok: true }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    store.token = "tok";
    store.accountExists = true;
    await store.logout();

    expect(store.accountExists).toBeNull();
  });

  // ---- Issue 4: stale-token reactivity ----

  it("stale token in localStorage makes isAuthenticated=true before init, then false after init says unauthenticated", async () => {
    localStorage.setItem("auth_token", "stale-tok");

    const api = makeApi({
      get: vi.fn().mockResolvedValue({
        account_exists: true,
        authenticated: false,
        username: null,
      }),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useAuthStore();
    // Before init: token read from storage, so isAuthenticated is true
    expect(store.isAuthenticated).toBe(true);

    await store.init();

    // After init: server says not authenticated, token must be cleared
    expect(store.isAuthenticated).toBe(false);
    expect(store.token).toBeNull();
  });
});
