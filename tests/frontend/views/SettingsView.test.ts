import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { setActivePinia, createPinia } from "pinia";

vi.mock("@/composables/useApi", () => ({
  useApi: vi.fn(),
  ApiError: class ApiError extends Error {
    readonly status: number;
    readonly detail: string;
    constructor(status: number, detail: string) {
      super(detail);
      this.name = "ApiError";
      this.status = status;
      this.detail = detail;
    }
  },
}));

vi.mock("@/router", () => ({
  default: { push: vi.fn() },
}));

const mockPush = vi.fn();

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    useRouter: () => ({ push: mockPush }),
    useRoute: () => ({ params: {} }),
    RouterLink: { template: "<a><slot /></a>", props: ["to"] },
  };
});

vi.mock("@/components/layout/AppHeader.vue", () => ({
  default: { template: "<header />" },
}));

import { useApi } from "@/composables/useApi";
import SettingsView from "@/views/SettingsView.vue";

function makeApi(overrides: Record<string, unknown> = {}) {
  return {
    get: vi.fn().mockResolvedValue({ refresh_interval_minutes: 15, preferred_timezone: "UTC" }),
    post: vi.fn(),
    patch: vi.fn(),
    put: vi.fn().mockResolvedValue({ refresh_interval_minutes: 15, preferred_timezone: "UTC" }),
    delete: vi.fn(),
    ...overrides,
  };
}

describe("SettingsView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("navigates to / one second after a successful save", async () => {
    const api = makeApi();
    vi.mocked(useApi).mockReturnValue(api);

    const wrapper = mount(SettingsView);
    await flushPromises();

    await wrapper.find(".btn-save").trigger("click");
    await flushPromises();

    expect(mockPush).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1000);
    await wrapper.vm.$nextTick();
    expect(wrapper.find(".settings-card").classes()).toContain("fading-out");

    vi.advanceTimersByTime(400);
    await flushPromises();
    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("renders a timezone selector with UTC selected by default", async () => {
    const api = makeApi();
    vi.mocked(useApi).mockReturnValue(api);

    const wrapper = mount(SettingsView);
    await flushPromises();

    const select = wrapper.find(".tz-select");
    expect(select.exists()).toBe(true);
    expect((select.element as HTMLSelectElement).value).toBe("UTC");
  });

  it("does not navigate if save fails", async () => {
    const api = makeApi({
      put: vi.fn().mockRejectedValue(new Error("network error")),
    });
    vi.mocked(useApi).mockReturnValue(api);

    const wrapper = mount(SettingsView);
    await flushPromises();

    await wrapper.find(".btn-save").trigger("click");
    await flushPromises();

    vi.advanceTimersByTime(2000);
    expect(mockPush).not.toHaveBeenCalled();
    expect(wrapper.find(".settings-card").classes()).not.toContain("fading-out");
  });
});
