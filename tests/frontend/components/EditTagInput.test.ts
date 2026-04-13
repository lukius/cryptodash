import { describe, it, expect, beforeEach, vi } from "vitest";
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

import { useApi, ApiError } from "@/composables/useApi";
import { useWalletsStore } from "@/stores/wallets";
import EditTagInput from "@/components/wallet/EditTagInput.vue";

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

describe("EditTagInput", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.mocked(useApi).mockReturnValue(makeApi() as ReturnType<typeof useApi>);
  });

  // ---- Default (view) mode ----

  it("renders tag text in view mode", () => {
    const wrapper = mount(EditTagInput, {
      props: { walletId: "w1", tag: "Cold Storage" },
    });
    expect(wrapper.text()).toContain("Cold Storage");
    expect(wrapper.find("input").exists()).toBe(false);
  });

  it("shows edit icon button in view mode", () => {
    const wrapper = mount(EditTagInput, {
      props: { walletId: "w1", tag: "Cold Storage" },
    });
    const btn = wrapper.find("button[aria-label='Edit tag']");
    expect(btn.exists()).toBe(true);
  });

  // ---- Entering edit mode ----

  it("clicking edit icon enters edit mode and shows input", async () => {
    const wrapper = mount(EditTagInput, {
      props: { walletId: "w1", tag: "Cold Storage" },
    });
    await wrapper.find("button[aria-label='Edit tag']").trigger("click");
    expect(wrapper.find("input").exists()).toBe(true);
  });

  it("input is pre-filled with current tag when edit mode starts", async () => {
    const wrapper = mount(EditTagInput, {
      props: { walletId: "w1", tag: "Cold Storage" },
    });
    await wrapper.find("button[aria-label='Edit tag']").trigger("click");
    const input = wrapper.find("input");
    expect((input.element as HTMLInputElement).value).toBe("Cold Storage");
  });

  // ---- Pressing Enter confirms ----

  it("pressing Enter calls wallets.updateTag with new value", async () => {
    const store = useWalletsStore();
    const updateTagSpy = vi.spyOn(store, "updateTag").mockResolvedValue();

    const wrapper = mount(EditTagInput, {
      props: { walletId: "w1", tag: "Old Tag" },
    });
    await wrapper.find("button[aria-label='Edit tag']").trigger("click");

    const input = wrapper.find("input");
    await input.setValue("New Tag");
    await input.trigger("keydown", { key: "Enter" });
    await flushPromises();

    expect(updateTagSpy).toHaveBeenCalledWith("w1", "New Tag");
  });

  it("pressing Enter exits edit mode on success", async () => {
    const store = useWalletsStore();
    vi.spyOn(store, "updateTag").mockResolvedValue();

    const wrapper = mount(EditTagInput, {
      props: { walletId: "w1", tag: "Old Tag" },
    });
    await wrapper.find("button[aria-label='Edit tag']").trigger("click");

    const input = wrapper.find("input");
    await input.setValue("New Tag");
    await input.trigger("keydown", { key: "Enter" });
    await flushPromises();

    expect(wrapper.find("input").exists()).toBe(false);
  });

  // ---- Pressing Escape cancels ----

  it("pressing Escape cancels and reverts to original tag", async () => {
    const wrapper = mount(EditTagInput, {
      props: { walletId: "w1", tag: "Original" },
    });
    await wrapper.find("button[aria-label='Edit tag']").trigger("click");

    const input = wrapper.find("input");
    await input.setValue("Changed");
    await input.trigger("keydown", { key: "Escape" });

    expect(wrapper.find("input").exists()).toBe(false);
    expect(wrapper.text()).toContain("Original");
  });

  it("pressing Escape does not call updateTag", async () => {
    const store = useWalletsStore();
    const updateTagSpy = vi.spyOn(store, "updateTag").mockResolvedValue();

    const wrapper = mount(EditTagInput, {
      props: { walletId: "w1", tag: "Original" },
    });
    await wrapper.find("button[aria-label='Edit tag']").trigger("click");
    await wrapper.find("input").trigger("keydown", { key: "Escape" });

    expect(updateTagSpy).not.toHaveBeenCalled();
  });

  // ---- Empty tag validation ----

  it("shows inline error when tag is cleared to empty and Enter pressed", async () => {
    const store = useWalletsStore();
    const updateTagSpy = vi.spyOn(store, "updateTag").mockResolvedValue();

    const wrapper = mount(EditTagInput, {
      props: { walletId: "w1", tag: "Some Tag" },
    });
    await wrapper.find("button[aria-label='Edit tag']").trigger("click");

    const input = wrapper.find("input");
    await input.setValue("");
    await input.trigger("keydown", { key: "Enter" });
    await flushPromises();

    expect(wrapper.text()).toContain("Tag cannot be empty.");
    expect(updateTagSpy).not.toHaveBeenCalled();
    // Remains in edit mode
    expect(wrapper.find("input").exists()).toBe(true);
  });

  it("shows inline error for whitespace-only tag", async () => {
    const store = useWalletsStore();
    const updateTagSpy = vi.spyOn(store, "updateTag").mockResolvedValue();

    const wrapper = mount(EditTagInput, {
      props: { walletId: "w1", tag: "Some Tag" },
    });
    await wrapper.find("button[aria-label='Edit tag']").trigger("click");

    const input = wrapper.find("input");
    await input.setValue("   ");
    await input.trigger("keydown", { key: "Enter" });
    await flushPromises();

    expect(wrapper.text()).toContain("Tag cannot be empty.");
    expect(updateTagSpy).not.toHaveBeenCalled();
  });

  // ---- Duplicate tag error from server ----

  it("renders inline error when store throws ApiError for duplicate tag", async () => {
    const store = useWalletsStore();
    vi.spyOn(store, "updateTag").mockRejectedValue(
      new ApiError(400, "A wallet with this tag already exists."),
    );

    const wrapper = mount(EditTagInput, {
      props: { walletId: "w1", tag: "Original" },
    });
    await wrapper.find("button[aria-label='Edit tag']").trigger("click");

    const input = wrapper.find("input");
    await input.setValue("Duplicate");
    await input.trigger("keydown", { key: "Enter" });
    await flushPromises();

    expect(wrapper.text()).toContain("A wallet with this tag already exists.");
    // Stays in edit mode
    expect(wrapper.find("input").exists()).toBe(true);
  });

  // ---- No-op when tag unchanged ----

  it("pressing Enter without changing tag exits edit mode without calling updateTag", async () => {
    const store = useWalletsStore();
    const updateTagSpy = vi.spyOn(store, "updateTag").mockResolvedValue();

    const wrapper = mount(EditTagInput, {
      props: { walletId: "w1", tag: "Same" },
    });
    await wrapper.find("button[aria-label='Edit tag']").trigger("click");
    // Don't change the value
    await wrapper.find("input").trigger("keydown", { key: "Enter" });
    await flushPromises();

    expect(updateTagSpy).not.toHaveBeenCalled();
    expect(wrapper.find("input").exists()).toBe(false);
  });
});
