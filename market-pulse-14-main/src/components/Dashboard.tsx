import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import StockTable from "@/components/StockTable";
import ShortlistTable from "@/components/ShortlistTable";
import StatsCards from "@/components/StatsCards";
import ControlsBar from "@/components/ControlsBar";
import { useWebSocket } from "@/hooks/useWebSocket";
import { Stock, SortField, StockLimit } from "@/types";
import { AlertTriangle, Clock } from "lucide-react";

function getIST(): string {
  return new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false });
}

function getSessionStatus(): { text: string; color: string } | null {
  const ist = getIST();
  if (ist >= "09:00:00" && ist <= "09:08:00") return { text: "Pre-Open Session", color: "text-yellow-400" };
  if (ist > "09:08:00" && ist < "09:15:00") return { text: "Snapshot Frozen", color: "text-amber-400" };
  if (ist >= "09:15:00" && ist <= "15:30:00") return { text: "Market Open", color: "text-success" };
  return { text: "Market Closed", color: "text-muted-foreground" };
}

function exportCSV(stocks: Stock[]) {
  const headers = [
    "Symbol",
    "IEP",
    "Prev Close",
    "IEP Gap ₹",
    "IEP Gap %",
    "Buy Qty",
    "Sell Qty",
    "B/S Ratio",
    "Signal",
    "Ind. Volume",
    "Last Updated",
  ];
  const rows = stocks.map((s) => [
    s.symbol,
    s.iep,
    s.prev_close,
    s.iep_gap_inr,
    s.iep_gap_pct,
    s.buy_qty,
    s.sell_qty,
    s.bs_ratio,
    s.signal,
    s.volume,
    s.last_updated,
  ]);
  const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `preopen_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function Dashboard() {
  const navigate = useNavigate();
  const token = localStorage.getItem("access_token") || "";

  const [sortBy, setSortBy] = useState<SortField>("iep_gap_pct");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [limit, setLimit] = useState<StockLimit>(50);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshIntervalSeconds, setRefreshIntervalSeconds] = useState(5);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<"all" | "gainers" | "losers">("all");
  const [istTime, setIstTime] = useState(getIST());
  const [showStaleBanner, setShowStaleBanner] = useState(false);

  useEffect(() => {
    const t = setInterval(() => setIstTime(getIST()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (!token) navigate("/");
  }, [token, navigate]);

  const { stocks, shortlist, connected, lastUpdate, isFrozen, freezeMessage } = useWebSocket(
    autoRefresh,
    refreshIntervalSeconds,
  );

  // Stale snapshot banner
  useEffect(() => {
    const hasStale = stocks.some((s: any) => s.is_stale === true);
    setShowStaleBanner(hasStale);
  }, [stocks]);

  // ── Filtering pipeline ─────────────────────────────────────────────────────

  // Parse search input — supports both single ("RELIANCE") and multi ("RELIANCE, TCS, INFY")
  const parsedSymbols = searchQuery.trim()
    ? searchQuery
        .split(/[,\s]+/)
        .map((s) => s.trim().toUpperCase())
        .filter((s) => s.length > 0)
    : [];

  const isMultiSymbol = parsedSymbols.length > 1;
  const isSingleSymbol = parsedSymbols.length === 1;

  // Step 1: Symbol filter
  // Multi-symbol → exact match ONLY those symbols (watchlist mode)
  // Single symbol → substring match (partial typing support e.g. "RELI" finds RELIANCE)
  const afterSearch =
    parsedSymbols.length === 0
      ? stocks
      : isMultiSymbol
        ? stocks.filter((s) => parsedSymbols.includes(s.symbol.toUpperCase()))
        : stocks.filter((s) => s.symbol.toUpperCase().includes(parsedSymbols[0]));

  // Step 2: Gainers / Losers filter
  const afterFilter =
    filterType === "gainers"
      ? afterSearch.filter((s) => (s.iep_gap_pct ?? 0) > 0)
      : filterType === "losers"
        ? afterSearch.filter((s) => (s.iep_gap_pct ?? 0) < 0)
        : afterSearch;

  // Step 3: Sort
  const sorted = [...afterFilter].sort((a, b) => {
    const av = (a as any)[sortBy] ?? 0;
    const bv = (b as any)[sortBy] ?? 0;
    return sortOrder === "desc" ? bv - av : av - bv;
  });

  // Step 4: Limit — bypassed in multi-symbol watchlist mode (always show all matches)
  const displayed = isMultiSymbol ? sorted : sorted.slice(0, limit);

  // Symbols typed but not found in live data (only relevant in multi-symbol mode)
  const missingSymbols = isMultiSymbol
    ? parsedSymbols.filter((sym) => !stocks.find((s) => s.symbol.toUpperCase() === sym))
    : [];

  const sessionStatus = getSessionStatus();
  const isPreopen = getIST() >= "09:00:00" && getIST() <= "09:08:00";

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Topbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-card border-b border-border">
        <span className="text-primary font-bold text-lg tracking-wide">NSE Pre-Open Scanner</span>
        <div className="flex items-center gap-4">
          <span className="text-muted-foreground text-sm font-mono">{istTime} IST</span>
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full animate-pulse ${connected ? "bg-success" : "bg-destructive"}`} />
            <span className={`text-xs ${connected ? "text-success" : "text-destructive"}`}>
              {connected ? "Connected" : "Disconnected"}
            </span>
          </div>
          <button
            onClick={handleLogout}
            className="text-xs text-muted-foreground hover:text-foreground border border-border px-2 py-1 rounded transition-colors"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Stale snapshot warning — only during 9:00–9:08 */}
      {showStaleBanner && isPreopen && (
        <div className="flex items-center gap-2 px-4 py-2 bg-amber-900/50 border-b border-amber-700 text-amber-300 text-sm">
          <AlertTriangle size={15} className="shrink-0 text-amber-400" />
          <span>
            <strong>First snapshot (9:00 AM)</strong> — Data may reflect previous day carry-forward prices from NSE.
            Live pre-open data begins at <strong>~9:01 AM IST</strong>.
          </span>
          <button
            onClick={() => setShowStaleBanner(false)}
            className="ml-auto text-amber-500 hover:text-foreground text-base leading-none"
          >
            ✕
          </button>
        </div>
      )}

      {/* Stats cards */}
      <div className="p-4">
        <StatsCards
          stocks={stocks}
          lastUpdate={lastUpdate}
          filterType={filterType}
          setFilterType={setFilterType}
          sessionStatus={sessionStatus}
        />
      </div>

      {/* Controls bar */}
      <div className="px-4 pb-4">
        <ControlsBar
          sortBy={sortBy}
          setSortBy={setSortBy}
          sortOrder={sortOrder}
          setSortOrder={setSortOrder}
          limit={limit}
          setLimit={setLimit}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          autoRefresh={autoRefresh}
          setAutoRefresh={setAutoRefresh}
          refreshIntervalSeconds={refreshIntervalSeconds}
          setRefreshIntervalSeconds={setRefreshIntervalSeconds}
          onExportCSV={() => exportCSV(displayed)}
        />
      </div>

      {/* Client output: simple shortlist table */}
      <div className="px-4 pb-4">
        <ShortlistTable stocks={shortlist} isFrozen={isFrozen} freezeMessage={freezeMessage} />
      </div>

      {/* Watchlist info strip — multi-symbol mode only */}
      {isMultiSymbol && (
        <div className="flex items-center gap-2 px-4 py-1.5 bg-primary/5 border-b border-primary/20 text-primary text-xs">
          <Clock size={12} />
          <span>
            Watchlist mode — showing {displayed.length} / {parsedSymbols.length} symbols
          </span>
          {missingSymbols.length > 0 && (
            <span className="text-amber-400 ml-1">
              · Not in data: <strong>{missingSymbols.join(", ")}</strong>
            </span>
          )}
        </div>
      )}

      {/* Single symbol filter strip */}
      {isSingleSymbol && (
        <div className="flex items-center gap-2 px-4 py-1.5 bg-primary/5 border-b border-primary/20 text-primary text-xs">
          <Clock size={12} />
          <span>
            Filtering by "{parsedSymbols[0]}" — {displayed.length} result{displayed.length !== 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* Table */}
      <div className="flex-1 overflow-auto px-4 pb-4">
        <StockTable stocks={displayed} loading={!connected && stocks.length === 0} searchQuery={searchQuery} />
      </div>

      {/* Footer */}
      <div className="text-center text-muted-foreground text-xs py-2 border-t border-border">
        NSE Pre-Open Scanner — IFA &nbsp;|&nbsp; Data refreshes every ~30–60 seconds during 9:00–9:07 AM IST
      </div>
    </div>
  );
}
