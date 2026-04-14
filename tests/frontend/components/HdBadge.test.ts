import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import HdBadge from "@/components/wallet/HdBadge.vue";

describe("HdBadge", () => {
  it("renders the text 'HD'", () => {
    const wrapper = mount(HdBadge);
    expect(wrapper.text()).toBe("HD");
  });

  it("has aria-label='HD Wallet'", () => {
    const wrapper = mount(HdBadge);
    const span = wrapper.find("span");
    expect(span.attributes("aria-label")).toBe("HD Wallet");
  });

  it("has a title attribute with full description", () => {
    const wrapper = mount(HdBadge);
    const span = wrapper.find("span");
    expect(span.attributes("title")).toBe(
      "Hierarchical Deterministic Wallet (xpub/ypub/zpub)",
    );
  });

  it("renders as a span element", () => {
    const wrapper = mount(HdBadge);
    expect(wrapper.element.tagName.toLowerCase()).toBe("span");
  });
});
