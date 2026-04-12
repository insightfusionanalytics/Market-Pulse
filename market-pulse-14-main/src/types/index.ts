export interface Stock {
  symbol: string;

  // ── Core pre-open fields ──────────────────────────────────────────────────
  iep: number; // Indicative Equilibrium Price
  prev_close: number;
  iep_gap_inr: number; // IEP - Prev Close (₹)
  iep_gap_pct: number; // % gap from prev close
  buy_qty: number;
  sell_qty: number;
  bs_ratio: number; // buy_qty / sell_qty
  signal: string; // "BUY BIAS" | "SELL BIAS" | "NEUTRAL"
  volume: number; // NSE Indicative Matched Quantity (non-zero from Redis)
  last_updated: string; // e.g. "09:01"

  // ── Derived / computed ────────────────────────────────────────────────────
  alert_level: string; // "HIGH" | "MEDIUM" | "NORMAL"
  phase: string;
  change: number; // alias for iep_gap_inr (frontend compat)
  change_pct: number; // alias for iep_gap_pct (frontend compat)

  // ── Legacy / compat fields (kept so nothing else breaks) ─────────────────
  ltp: number;
  proxy_vol: number;
  high: number;
  low: number;
  open: number;
  lower_ckt: number;
  upper_ckt: number;
  flagged?: boolean;
  tick_count?: number;
  timestamp: string;

  // ── Phase B (future — not yet active) ────────────────────────────────────
  avg_vol_20d?: number;
  vol_spike_ratio?: number;
  avg_vol_at_time?: number; // 20-day avg pre-open volume at same time

  // ── Rule-based shortlist fields ───────────────────────────────────────────
  preopen_activity_metric?: number;
  activity_20d_avg?: number;
  activity_vs_20d?: number;
  gap_20d_avg?: number;
  liquidity_20d_avg?: number;
  baseline_sample_days?: number;
  mandatory_activity_pass?: boolean;
  mandatory_gap_pass?: boolean;
  optional_matches?: number;
  optional_required?: number;
  optional_pass?: boolean;
  qualified?: boolean;
  qualification_reasons?: string[];
}

export interface WebSocketMessage {
  type: string;
  data: Stock[];
  timestamp: string;
  phase?: string;
  stats?: {
    total: number;
    gainers: number;
    losers: number;
    high_alerts: number;
    shortlisted?: number;
  };
  shortlist?: Stock[];
  is_frozen?: boolean;
  freeze_message?: string | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export type SortField =
  | "iep_gap_pct"
  | "iep_gap_inr"
  | "iep"
  | "bs_ratio"
  | "buy_qty"
  | "sell_qty"
  | "volume"
  | "change_pct" // compat alias
  | "ltp" // compat alias
  | "proxy_vol"; // compat alias

export type SortOrder = "asc" | "desc";
export type StockLimit = 10 | 25 | 50 | 500;
