/** Format as ₹X,XXX.XX (Indian rupee) */
export function formatCurrency(value: number): string {
  if (value == null || isNaN(value)) return "₹0.00";
  return "₹" + value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Format large numbers with K / M suffixes */
export function formatLargeNumber(n: number): string {
  if (!n || n === 0) return "–";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toString();
}

/** Format as +X.XX% or -X.XX% */
export function formatPercentage(value: number): string {
  if (value == null || isNaN(value)) return "0.00%";
  const sign = value > 0 ? "+" : "";
  return sign + value.toFixed(2) + "%";
}

/** Parse ISO timestamp → HH:MM:SS IST */
export function formatTime(isoString: string): string {
  if (!isoString) return "--:--:--";
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString("en-IN", {
      timeZone: "Asia/Kolkata",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return "--:--:--";
  }
}

/** Extract symbol from "NSE:RELIANCE-EQ" → "RELIANCE" */
export function extractSymbolName(fullSymbol: string): string {
  if (!fullSymbol) return "";
  const withoutExchange = fullSymbol.includes(":") ? fullSymbol.split(":")[1] : fullSymbol;
  return withoutExchange.replace(/-EQ$/, "");
}
