import { useState, useEffect, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import StockTable from "@/components/StockTable";
import ShortlistTable from "@/components/ShortlistTable";
import StatsCards from "@/components/StatsCards";
import ControlsBar from "@/components/ControlsBar";
import HistoryPanel from "@/components/HistoryPanel";
import { useWebSocket } from "@/hooks/useWebSocket";
import { Stock, SortField, StockLimit } from "@/types";
import { AlertTriangle, Clock, Wifi, WifiOff, LogOut } from "lucide-react";

function getIST(): string {
  return new Date().toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false });
}

function getSessionStatus(): { text: string; color: string; bg: string } | null {
  const ist = getIST();
  if (ist >= "09:00:00" && ist <= "09:08:00") return { text: "Pre-Open", color: "text-amber-400", bg: "bg-amber-400/10 border-amber-400/30" };
  if (ist > "09:08:00" && ist < "09:15:00") return { text: "Frozen", color: "text-amber-400", bg: "bg-amber-400/10 border-amber-400/30" };
  if (ist >= "09:15:00" && ist <= "15:30:00") return { text: "Market Open", color: "text-success", bg: "bg-success/10 border-success/30" };
  return { text: "Closed", color: "text-muted-foreground", bg: "bg-muted/30 border-border" };
}

function exportCSV(stocks: Stock[]) {
  const headers = [
    "Symbol", "IEP", "Prev Close", "IEP Gap ₹", "IEP Gap %",
    "Buy Qty", "Sell Qty", "B/S Ratio", "Signal", "Ind. Volume", "Last Updated",
  ];
  const rows = stocks.map((s) => [
    s.symbol, s.iep, s.prev_close, s.iep_gap_inr, s.iep_gap_pct,
    s.buy_qty, s.sell_qty, s.bs_ratio, s.signal, s.volume, s.last_updated,
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

  // ── Memoized filtering pipeline ──────────────────────────────────────────
  const parsedSymbols = useMemo(() => {
    return searchQuery.trim()
      ? searchQuery.split(/[,\s]+/).map((s) => s.trim().toUpperCase()).filter((s) => s.length > 0)
      : [];
  }, [searchQuery]);

  const isMultiSymbol = parsedSymbols.length > 1;
  const isSingleSymbol = parsedSymbols.length === 1;

  const displayed = useMemo(() => {
    // Step 1: Symbol filter
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

    // Step 4: Limit — bypassed in multi-symbol watchlist mode
    return isMultiSymbol ? sorted : sorted.slice(0, limit);
  }, [stocks, parsedSymbols, isMultiSymbol, filterType, sortBy, sortOrder, limit]);

  const missingSymbols = useMemo(() => {
    return isMultiSymbol
      ? parsedSymbols.filter((sym) => !stocks.find((s) => s.symbol.toUpperCase() === sym))
      : [];
  }, [isMultiSymbol, parsedSymbols, stocks]);

  const sessionStatus = getSessionStatus();
  const isPreopen = getIST() >= "09:00:00" && getIST() <= "09:08:00";

  const handleLogout = useCallback(() => {
    localStorage.removeItem("access_token");
    navigate("/");
  }, [navigate]);

  const handleExportCSV = useCallback(() => exportCSV(displayed), [displayed]);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* ── Topbar ────────────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-30 flex items-center justify-between px-5 lg:px-8 py-3 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="flex items-center gap-4">
          <h1 className="text-primary font-bold text-lg tracking-tight">MarketPulse</h1>
          {sessionStatus && (
            <span className={`text-xs font-medium px-2.5 py-1 rounded-full border ${sessionStatus.bg} ${sessionStatus.color}`}>
              {sessionStatus.text}
            </span>
          )}
        </div>
        <div className="flex items-center gap-5">
          <span className="text-muted-foreground text-sm font-mono tabular-nums">{istTime} IST</span>
          <div className="flex items-center gap-1.5">
            {connected ? (
              <Wifi size={14} className="text-success animate-pulse-dot" />
            ) : (
              <WifiOff size={14} className="text-destructive" />
            )}
            <span className={`text-xs font-medium ${connected ? "text-success" : "text-destructive"}`}>
              {connected ? "Live" : "Offline"}
            </span>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground border border-border px-2.5 py-1.5 rounded-md transition-colors hover:bg-secondary"
          >
            <LogOut size={12} />
            Logout
          </button>
        </div>
      </div>

      {/* Stale snapshot warning */}
      {showStaleBanner && isPreopen && (
        <div className="flex items-center gap-2 px-5 lg:px-8 py-2 bg-amber-900/30 border-b border-amber-700/40 text-amber-300 text-sm">
          <AlertTriangle size={15} className="shrink-0 text-amber-400" />
          <span>
            <strong>First snapshot (9:00 AM)</strong> — Data may reflect previous day carry-forward prices.
            Live pre-open data begins at <strong>~9:01 AM IST</strong>.
          </span>
          <button
            onClick={() => setShowStaleBanner(false)}
            className="ml-auto text-amber-500 hover:text-foreground text-base leading-none px-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <div className="max-w-[1920px] mx-auto w-full flex flex-col flex-1">
        {/* Stats cards */}
        <div className="px-5 lg:px-8 pt-5 pb-4">
          <StatsCards
            stocks={stocks}
            lastUpdate={lastUpdate}
            filterType={filterType}
            setFilterType={setFilterType}
            sessionStatus={sessionStatus}
          />
        </div>

        {/* Controls bar */}
        <div className="px-5 lg:px-8 pb-4">
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
            onExportCSV={handleExportCSV}
          />
        </div>

        {/* Shortlist table */}
        <div className="px-5 lg:px-8 pb-4">
          <ShortlistTable stocks={shortlist} isFrozen={isFrozen} freezeMessage={freezeMessage} />
        </div>

        {/* History panel */}
        <div className="px-5 lg:px-8 pb-4">
          <HistoryPanel />
        </div>

        {/* Watchlist info strip */}
        {isMultiSymbol && (
          <div className="flex items-center gap-2 px-5 lg:px-8 py-2 bg-primary/5 border-y border-primary/15 text-primary text-xs">
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

        {isSingleSymbol && (
          <div className="flex items-center gap-2 px-5 lg:px-8 py-2 bg-primary/5 border-y border-primary/15 text-primary text-xs">
            <Clock size={12} />
            <span>
              Filtering by "{parsedSymbols[0]}" — {displayed.length} result{displayed.length !== 1 ? "s" : ""}
            </span>
          </div>
        )}

        {/* Main table */}
        <div className="flex-1 overflow-auto px-5 lg:px-8 pb-5">
          <StockTable stocks={displayed} loading={!connected && stocks.length === 0} searchQuery={searchQuery} />
        </div>
      </div>

      {/* Footer */}
      <div className="text-center text-muted-foreground text-xs py-3 border-t border-border bg-background/50">
        MarketPulse — IFA &nbsp;|&nbsp; Updates reflect incoming snapshots during 9:00–9:07 AM IST
      </div>
    </div>
  );
}
