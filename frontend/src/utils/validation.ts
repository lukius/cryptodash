const BASE58_CHARS =
  "[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]";
const BECH32_CHARS = "[023456789acdefghjklmnpqrstuvwxyz]";

export function validateBtcAddress(address: string): string | null {
  address = address.trim().replace(/\n/g, "").replace(/ /g, "");

  if (!address) return "Invalid Bitcoin address format.";

  if (address.startsWith("1")) {
    if (
      address.length >= 25 &&
      address.length <= 34 &&
      new RegExp(`^${BASE58_CHARS}+$`).test(address)
    ) {
      return null;
    }
    return "Invalid Bitcoin address format.";
  }

  if (address.startsWith("3")) {
    if (
      address.length >= 25 &&
      address.length <= 34 &&
      new RegExp(`^${BASE58_CHARS}+$`).test(address)
    ) {
      return null;
    }
    return "Invalid Bitcoin address format.";
  }

  if (address.toLowerCase().startsWith("bc1q")) {
    const lower = address.toLowerCase();
    if (
      (lower.length === 42 || lower.length === 62) &&
      new RegExp(`^bc1q${BECH32_CHARS}+$`).test(lower)
    ) {
      return null;
    }
    return "Invalid Bitcoin address format.";
  }

  if (address.toLowerCase().startsWith("bc1p")) {
    const lower = address.toLowerCase();
    if (
      lower.length === 62 &&
      new RegExp(`^bc1p${BECH32_CHARS}+$`).test(lower)
    ) {
      return null;
    }
    return "Invalid Bitcoin address format.";
  }

  return "Invalid Bitcoin address format.";
}

export function validateKasAddress(address: string): string | null {
  address = address.trim().replace(/\n/g, "").replace(/ /g, "");

  if (!address.startsWith("kaspa:")) {
    return "Invalid Kaspa address format. Kaspa addresses start with 'kaspa:'.";
  }

  const remainder = address.slice(6);
  if (
    remainder.length >= 61 &&
    remainder.length <= 63 &&
    new RegExp(`^${BECH32_CHARS}+$`).test(remainder)
  ) {
    return null;
  }

  return "Invalid Kaspa address format. Kaspa addresses start with 'kaspa:'.";
}
