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
import AddWalletDialog from "@/components/wallet/AddWalletDialog.vue";

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

function makeWallet(overrides: Record<string, unknown> = {}) {
  return {
    id: "wallet-new",
    network: "BTC",
    address: "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    tag: "BTC Wallet #1",
    balance: null,
    balance_usd: null,
    created_at: "2026-01-01T00:00:00Z",
    last_updated: null,
    warning: null,
    history_status: "pending",
    ...overrides,
  };
}

describe("AddWalletDialog", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    // Default mock: no-op api
    vi.mocked(useApi).mockReturnValue(makeApi() as ReturnType<typeof useApi>);
  });

  // ---- Rendering ----

  it("renders nothing (not visible) when modelValue=false", () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: false } });
    const overlay = wrapper.find(".modal-overlay");
    // Either not rendered or not visible
    expect(overlay.exists() ? overlay.isVisible() : false).toBe(false);
  });

  it("renders form fields when modelValue=true", () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    expect(wrapper.find("textarea, input[name='address'], [data-testid='address-input']").exists()).toBe(true);
  });

  it("renders network selection buttons for Bitcoin and Kaspa", () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const text = wrapper.text();
    expect(text).toContain("Bitcoin");
    expect(text).toContain("Kaspa");
  });

  it("renders Cancel and Add Wallet buttons", () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const buttons = wrapper.findAll("button");
    const labels = buttons.map((b) => b.text());
    expect(labels.some((l) => l.includes("Cancel"))).toBe(true);
    expect(labels.some((l) => l.includes("Add"))).toBe(true);
  });

  // ---- Validation: empty address ----

  it("shows error when submitting with empty address", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const submitBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("add"),
    );
    await submitBtn!.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toMatch(/enter.*address|address.*required/i);
  });

  // ---- Validation: invalid BTC address ----

  it("shows validation error for invalid BTC address on blur", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("not-a-real-btc-address");
    await addressInput.trigger("blur");
    expect(wrapper.text()).toContain("Invalid Bitcoin address format.");
  });

  it("shows validation error for invalid BTC address on submit", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("not-a-real-address");
    const submitBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("add"),
    );
    await submitBtn!.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Invalid Bitcoin address format.");
  });

  // ---- Cancel button ----

  it("emits update:modelValue=false when Cancel is clicked", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const cancelBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("cancel"),
    );
    await cancelBtn!.trigger("click");
    expect(wrapper.emitted("update:modelValue")).toBeTruthy();
    expect(wrapper.emitted("update:modelValue")![0]).toEqual([false]);
  });

  // ---- Successful submission ----

  it("calls wallets.addWallet with correct payload on valid BTC address", async () => {
    const newWallet = makeWallet();
    const api = makeApi({
      post: vi.fn().mockResolvedValue(newWallet),
    });
    vi.mocked(useApi).mockReturnValue(api as ReturnType<typeof useApi>);

    const store = useWalletsStore();
    const addWalletSpy = vi
      .spyOn(store, "addWallet")
      .mockResolvedValue(newWallet);

    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa");

    const submitBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("add"),
    );
    await submitBtn!.trigger("click");
    await flushPromises();

    expect(addWalletSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        network: "BTC",
        address: "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
      }),
    );
  });

  it("emits wallet-added and closes dialog on success", async () => {
    const newWallet = makeWallet();
    const store = useWalletsStore();
    vi.spyOn(store, "addWallet").mockResolvedValue(newWallet);

    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa");

    const submitBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("add"),
    );
    await submitBtn!.trigger("click");
    await flushPromises();

    expect(wrapper.emitted("wallet-added")).toBeTruthy();
    expect(wrapper.emitted("update:modelValue")).toBeTruthy();
    const closeEmits = wrapper.emitted("update:modelValue")!;
    expect(closeEmits[closeEmits.length - 1]).toEqual([false]);
  });

  // ---- API error display ----

  it("displays inline API error on duplicate address (400)", async () => {
    const store = useWalletsStore();
    vi.spyOn(store, "addWallet").mockRejectedValue(
      new ApiError(400, "This wallet address is already being tracked."),
    );

    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa");

    const submitBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("add"),
    );
    await submitBtn!.trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("This wallet address is already being tracked.");
    // Dialog should remain open
    expect(wrapper.emitted("update:modelValue")).toBeFalsy();
  });

  it("displays inline API error on duplicate tag (400)", async () => {
    const store = useWalletsStore();
    vi.spyOn(store, "addWallet").mockRejectedValue(
      new ApiError(400, "A wallet with this tag already exists."),
    );

    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa");

    const submitBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("add"),
    );
    await submitBtn!.trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("A wallet with this tag already exists.");
  });

  // ---- Input preserved on error ----

  it("preserves address input after API error", async () => {
    const store = useWalletsStore();
    vi.spyOn(store, "addWallet").mockRejectedValue(
      new ApiError(400, "This wallet address is already being tracked."),
    );

    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa");

    const submitBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("add"),
    );
    await submitBtn!.trigger("click");
    await flushPromises();

    const inputEl = addressInput.element as HTMLInputElement | HTMLTextAreaElement;
    expect(inputEl.value).toBe("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa");
  });

  // ---- Loading state ----

  it("disables Add button while submitting", async () => {
    let resolveAdd: (v: ReturnType<typeof makeWallet>) => void;
    const pendingPromise = new Promise<ReturnType<typeof makeWallet>>(
      (res) => (resolveAdd = res),
    );
    const store = useWalletsStore();
    vi.spyOn(store, "addWallet").mockReturnValue(pendingPromise);

    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa");

    const submitBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("add"),
    );
    await submitBtn!.trigger("click");
    // While pending, button should be disabled
    expect((submitBtn!.element as HTMLButtonElement).disabled).toBe(true);

    // Cleanup
    resolveAdd!(makeWallet());
    await flushPromises();
  });

  // ---- Kaspa network ----

  it("validates KAS address when Kaspa network is selected", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    // Select Kaspa network
    const kasBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("kaspa"),
    );
    await kasBtn!.trigger("click");

    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("not-a-kaspa-address");
    await addressInput.trigger("blur");

    expect(wrapper.text()).toContain("Invalid Kaspa address format");
  });

  // ---- HD wallet detection ----

  it("shows xpub helper text when network is BTC", () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    expect(wrapper.text()).toContain("extended public key");
    expect(wrapper.text()).toContain("xpub");
  });

  it("does not show xpub helper text when network is KAS", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const kasBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("kaspa"),
    );
    await kasBtn!.trigger("click");
    expect(wrapper.text()).not.toContain("extended public key");
  });

  it("BTC address input has combined placeholder text when BTC is selected", () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    const placeholder = (addressInput.element as HTMLTextAreaElement).placeholder;
    expect(placeholder).toContain("xpub");
  });

  it("changes label to 'Extended public key' after xpub is pasted", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH1234567890abcdef");
    await addressInput.trigger("paste");
    expect(wrapper.text()).toContain("Extended public key");
  });

  it("changes label to 'Extended public key' after ypub is pasted", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("ypub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH1234567890abcdef");
    await addressInput.trigger("paste");
    expect(wrapper.text()).toContain("Extended public key");
  });

  it("changes label to 'Extended public key' after zpub is pasted", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("zpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH1234567890abcdef");
    await addressInput.trigger("paste");
    expect(wrapper.text()).toContain("Extended public key");
  });

  it("keeps default label 'Wallet address' while user is typing (no paste/blur)", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    // Simulate typing character by character — only @input, no @paste or @blur
    await addressInput.setValue("xpub6CUGRUBf5");
    await addressInput.trigger("input");
    expect(wrapper.text()).toContain("Wallet address");
    expect(wrapper.text()).not.toContain("Extended public key");
  });

  it("changes label to 'Extended public key' after xpub is blurred (blur also commits)", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH1234567890abcdef");
    await addressInput.trigger("blur");
    expect(wrapper.text()).toContain("Extended public key");
  });

  it("keeps default label 'Wallet address' for a regular BTC address after paste", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa");
    await addressInput.trigger("paste");
    expect(wrapper.text()).toContain("Wallet address");
    expect(wrapper.text()).not.toContain("Extended public key");
  });

  it("clears validation error while typing once address becomes valid (no blur needed)", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    // Blur with an invalid address to trigger the error state
    await addressInput.setValue("1bad");
    await addressInput.trigger("blur");
    expect(wrapper.text()).toContain("Invalid Bitcoin address format");
    // Type a valid address character-by-character (only @input, no blur)
    await addressInput.setValue("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa");
    await addressInput.trigger("input");
    // Error should clear immediately without requiring another blur
    expect(wrapper.text()).not.toContain("Invalid Bitcoin address format");
    expect(wrapper.find(".input-error").exists()).toBe(false);
  });

  it("does not show validation error while typing for the first time (before blur)", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    // Type an invalid address but never blur
    await addressInput.setValue("1bad");
    await addressInput.trigger("input");
    expect(wrapper.text()).not.toContain("Invalid Bitcoin address format");
    expect(wrapper.find(".input-error").exists()).toBe(false);
  });

  it("clears a prior validation error when a valid zpub is pasted", async () => {
    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    // Simulate user typing a partial BTC address, blurring to trigger error
    await addressInput.setValue("1bad");
    await addressInput.trigger("blur");
    expect(wrapper.text()).toContain("Invalid Bitcoin address format");
    // Now paste a valid zpub — error should be cleared immediately after paste
    await addressInput.setValue(
      "zpub6qgBZX81kMmpeFYY5v3YssHmJXA4hHh6dL9HVpPPKr8dpBiRZXqRT2wiMyLaqkXcX5ARMkHZEk6q6tuGqgkSNoftw2ZEGsD3ok7WsZDkTBA",
    );
    await addressInput.trigger("paste");
    expect(wrapper.text()).not.toContain("Invalid Bitcoin address format");
  });

  // ---- HD wallet submission (regression: Issue 1) ----

  it("submits xpub key without client-side validation error", async () => {
    const hdWallet = makeWallet({
      address: "xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH12345678901abcde",
      tag: "BTC HD Wallet #1",
      wallet_type: "hd",
    });
    const store = useWalletsStore();
    const addWalletSpy = vi.spyOn(store, "addWallet").mockResolvedValue(hdWallet);

    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    const addressInput = wrapper.find("textarea, [data-testid='address-input']");
    await addressInput.setValue("xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH12345678901abcde");

    const submitBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("add"),
    );
    await submitBtn!.trigger("click");
    await flushPromises();

    // Must reach store.addWallet — no client-side block
    expect(addWalletSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        network: "BTC",
        address: "xpub6CUGRUBf5RVvPHfD4ADzFLmVRSG41jFjfFbM7EkFGH12345678901abcde",
      }),
    );
    // No client-side validation error visible
    expect(wrapper.text()).not.toContain("Invalid Bitcoin address format.");
  });

  // ---- Wallet limit ----

  it("shows limit message and disables submit when isLimitReached", () => {
    const store = useWalletsStore();
    store.wallets = Array.from({ length: 50 }, (_, i) =>
      ({
        id: `w${i}`,
        network: "BTC",
        address: `addr${i}`,
        tag: `Wallet ${i}`,
        balance: null,
        balance_usd: null,
        created_at: "2026-01-01T00:00:00Z",
        last_updated: null,
        warning: null,
        history_status: "complete",
      }),
    );

    const wrapper = mount(AddWalletDialog, { props: { modelValue: true } });
    expect(wrapper.text()).toContain("Wallet limit reached");
    const submitBtn = wrapper.findAll("button").find((b) =>
      b.text().toLowerCase().includes("add"),
    );
    expect((submitBtn!.element as HTMLButtonElement).disabled).toBe(true);
  });
});
