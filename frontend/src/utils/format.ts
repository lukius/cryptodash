export function formatUsd(
  value: string | number | null | undefined,
  decimals = 2,
): string {
  if (value === null || value === undefined) return "N/A";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "N/A";
  const abs = Math.abs(num);
  const formatted = abs.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return num < 0 ? `-$${formatted}` : `$${formatted}`;
}

export function formatBtc(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "N/A";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "N/A";
  return `${num.toFixed(8)} BTC`;
}

export function formatKas(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "N/A";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "N/A";
  return `${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} KAS`;
}

export function formatPercent(
  value: string | number | null | undefined,
): string {
  if (value === null || value === undefined) return "N/A";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "N/A";
  const sign = num >= 0 ? "+" : "";
  return `${sign}${num.toFixed(2)}%`;
}

export function formatTimestamp(
  iso: string | null | undefined,
  timeZone = "UTC",
): string {
  if (iso === null || iso === undefined) return "N/A";
  try {
    const date = new Date(iso);
    return date.toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone,
    });
  } catch {
    return "N/A";
  }
}

export function formatTimestampCompact(
  iso: string | null | undefined,
  timeZone = "UTC",
): string {
  if (!iso) return "N/A";
  try {
    const d = new Date(iso);
    const fmt = new Intl.DateTimeFormat("en-US", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone,
    });
    const parts = fmt.formatToParts(d);
    const get = (type: string) =>
      parts.find((p) => p.type === type)?.value ?? "00";
    return `${get("month")}/${get("day")} ${get("hour")}:${get("minute")}`;
  } catch {
    return "N/A";
  }
}

export function truncateAddress(addr: string, start = 6, end = 4): string {
  if (addr.length <= start + end) return addr;
  return `${addr.slice(0, start)}...${addr.slice(-end)}`;
}

export function formatWalletAddress(
  address: string,
  walletType: "individual" | "hd",
): string {
  if (walletType === "hd") {
    // First 10 chars + "..." + last 6 chars (FR-H09)
    return address.length > 16
      ? `${address.slice(0, 10)}...${address.slice(-6)}`
      : address;
  }
  // Individual address: first 8 + "..." + last 6
  return address.length > 14
    ? `${address.slice(0, 8)}...${address.slice(-6)}`
    : address;
}
