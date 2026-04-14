import { useAuthStore } from "@/stores/auth";
import router from "@/router";

const BASE_URL = import.meta.env.VITE_API_BASE ?? "/api";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly retryAfter?: number;

  constructor(status: number, detail: string, retryAfter?: number) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.retryAfter = retryAfter;
  }
}

export function useApi() {
  const auth = useAuthStore();

  function headers(): Record<string, string> {
    const h: Record<string, string> = { "Content-Type": "application/json" };
    if (auth.token) {
      h["Authorization"] = `Bearer ${auth.token}`;
    }
    return h;
  }

  async function request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: headers(),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    if (response.status === 401) {
      if (path !== "/auth/logout") {
        auth.logout();
        router.push("/login");
      }
      throw new ApiError(401, "Unauthorized");
    }

    if (!response.ok) {
      let detail: string;
      try {
        const data = await response.json();
        detail =
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail);
      } catch {
        detail = response.statusText;
      }

      if (response.status === 429) {
        const retryAfterHeader = response.headers.get("Retry-After");
        const retryAfter = retryAfterHeader
          ? parseInt(retryAfterHeader, 10)
          : undefined;
        throw new ApiError(
          429,
          detail,
          Number.isNaN(retryAfter) ? undefined : retryAfter,
        );
      }

      throw new ApiError(response.status, detail);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }

  return {
    get: <T>(path: string) => request<T>("GET", path),
    post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
    patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
    put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
    delete: <T>(path: string) => request<T>("DELETE", path),
  };
}
