import React, { useState, useMemo } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Stock } from "@/types";
import { formatCurrency, formatLargeNumber, extractSymbolName } from "@/lib/formatters";
import { Loader2, ChevronUp, ChevronDown } from "lucide-react";

type SortKey = "iep" | "prev_close" | "iep_gap_inr" | "iep_gap_pct" | "buy_qty" | "sell_qty" | "bs_ratio" | "volume" | "liquidity_20d_avg";
type SortDirection = "asc" | "desc";

interface StockTableProps {
  stocks: Stock[];
  loading: boolean;
  searchQuery: string;
}

function SignalBadge({ signal }: { signal: string }) {
  if (signal === "BUY BIAS") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-semibold bg-success/10 text-success border border-success/20">
        <span className="w-1.5 h-1.5 rounded-full bg-success" />
        BUY
      </span>
    );
  }
  if (signal === "SELL BIAS") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-semibold bg-destructive/10 text-destructive border border-destructive/20">
        <span className="w-1.5 h-1.5 rounded-full bg-destructive" />
        SELL
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-semibold bg-muted/40 text-muted-foreground border border-border">
      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/50" />
      NEUTRAL
    </span>
  );
}

/** Heatmap background for IEP Gap % — subtle green/red tint based on magnitude */
function gapHeatmapBg(pct: number): string {
  const abs = Math.abs(pct);
  if (abs < 0.5) return "";
  if (pct > 0) {
    if (abs >= 3) return "bg-success/12";
    if (abs >= 1.5) return "bg-success/8";
    return "bg-success/4";
  } else {
    if (abs >= 3) return "bg-destructive/12";
    if (abs >= 1.5) return "bg-destructive/8";
    return "bg-destructive/4";
  }
}

/** Mini bar for B/S Ratio visualization */
function BSRatioBar({ ratio }: { ratio: number }) {
  const capped = Math.min(ratio, 3);
  const pct = Math.round((capped / 3) * 100);
  const color = ratio < 0.5 ? "bg-destructive/60" : ratio > 1.5 ? "bg-success/60" : "bg-muted-foreground/30";
  return (
    <div className="w-10 h-1 bg-muted/50 rounded-full overflow-hidden mt-0.5">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

const StockRow = React.memo(({ stock, rank }: { stock: Stock; rank: number }) => {
  const gapPct = stock.iep_gap_pct ?? 0;
  const isGainer = gapPct > 0;
  const isLoser = gapPct < 0;
  const isHighlight = stock.alert_level === "HIGH";

  const gapColor = isGainer ? "text-success" : isLoser ? "text-destructive" : "text-muted-foreground";

  return (
    <tr
      className={`border-b border-border/50 transition-colors hover:bg-secondary/40 ${
        isHighlight ? (isGainer ? "bg-success/[0.03]" : "bg-destructive/[0.03]") : ""
      } ${rank % 2 === 0 ? "bg-secondary/[0.06]" : ""}`}
    >
      {/* # */}
      <td className="px-3 py-2 text-muted-foreground font-mono text-xs text-center w-10">{rank}</td>

      {/* Symbol */}
      <td className="px-3 py-2 font-semibold text-foreground text-sm">
        <div className="flex items-center gap-1.5">
          {stock.flagged && (
            <span className="text-[10px] bg-amber-500/20 text-amber-400 border border-amber-500/30 px-1 rounded font-bold">!</span>
          )}
          {extractSymbolName(stock.symbol)}
        </div>
      </td>

      {/* IEP */}
      <td className="px-3 py-2 font-mono font-semibold text-foreground text-right text-sm tabular-nums">
        {stock.iep > 0 ? formatCurrency(stock.iep) : "–"}
      </td>

      {/* Prev Close */}
      <td className="px-3 py-2 font-mono text-muted-foreground text-right text-sm tabular-nums">
        {formatCurrency(stock.prev_close)}
      </td>

      {/* IEP Gap ₹ */}
      <td className={`px-3 py-2 font-mono font-medium text-right text-sm tabular-nums ${gapColor}`}>
        {stock.iep_gap_inr != null ? `${stock.iep_gap_inr > 0 ? "+" : ""}${formatCurrency(stock.iep_gap_inr)}` : "–"}
      </td>

      {/* IEP Gap % — with heatmap */}
      <td className={`px-3 py-2 font-mono font-bold text-right text-sm tabular-nums ${gapColor} ${gapHeatmapBg(gapPct)}`}>
        {gapPct != null ? `${gapPct > 0 ? "+" : ""}${gapPct.toFixed(2)}%` : "–"}
      </td>

      {/* Buy Qty */}
      <td className="px-3 py-2 font-mono text-muted-foreground text-right text-sm tabular-nums">
        {formatLargeNumber(stock.buy_qty)}
      </td>

      {/* Sell Qty */}
      <td className="px-3 py-2 font-mono text-muted-foreground text-right text-sm tabular-nums">
        {formatLargeNumber(stock.sell_qty)}
      </td>

      {/* B/S Ratio */}
      <td className="px-3 py-2 text-right">
        <div className="flex flex-col items-end">
          <span
            className={`font-mono font-semibold text-sm tabular-nums ${
              (stock.bs_ratio ?? 0) < 0.5
                ? "text-destructive"
                : (stock.bs_ratio ?? 0) > 1.5
                  ? "text-success"
                  : "text-muted-foreground"
            }`}
          >
            {stock.bs_ratio != null ? stock.bs_ratio.toFixed(2) : "–"}
          </span>
          {stock.bs_ratio != null && <BSRatioBar ratio={stock.bs_ratio} />}
        </div>
      </td>

      {/* Signal */}
      <td className="px-3 py-2">
        <SignalBadge signal={stock.signal ?? "NEUTRAL"} />
      </td>

      {/* Volume */}
      <td className="px-3 py-2 font-mono text-muted-foreground text-right text-sm tabular-nums">
        {stock.volume > 0 ? formatLargeNumber(stock.volume) : "–"}
      </td>

      {/* 20D Avg Vol */}
      <td className="px-3 py-2 font-mono text-muted-foreground text-right text-sm tabular-nums">
        {stock.liquidity_20d_avg && stock.liquidity_20d_avg > 0
          ? formatLargeNumber(stock.liquidity_20d_avg)
          : "–"}
      </td>

      {/* Updated */}
      <td className="px-3 py-2 font-mono text-[11px] text-muted-foreground text-right tabular-nums">
        {stock.last_updated ?? "–"}
      </td>
    </tr>
  );
});
StockRow.displayName = "StockRow";

// Column definitions
const COLUMNS: { label: string; sortKey: SortKey | null; align: string }[] = [
  { label: "#", sortKey: null, align: "text-center" },
  { label: "Symbol", sortKey: null, align: "text-left" },
  { label: "IEP", sortKey: "iep", align: "text-right" },
  { label: "Prev Close", sortKey: null, align: "text-right" },
  { label: "Gap ₹", sortKey: "iep_gap_inr", align: "text-right" },
  { label: "Gap %", sortKey: "iep_gap_pct", align: "text-right" },
  { label: "Buy Qty", sortKey: "buy_qty", align: "text-right" },
  { label: "Sell Qty", sortKey: "sell_qty", align: "text-right" },
  { label: "B/S Ratio", sortKey: "bs_ratio", align: "text-right" },
  { label: "Signal", sortKey: null, align: "text-left" },
  { label: "Volume", sortKey: "volume", align: "text-right" },
  { label: "20D Avg Vol", sortKey: "liquidity_20d_avg", align: "text-right" },
  { label: "Updated", sortKey: null, align: "text-right" },
];

const StockTable: React.FC<StockTableProps> = ({ stocks, loading, searchQuery }) => {
  const [sortConfig, setSortConfig] = useState<{ key: SortKey; direction: SortDirection }>({
    key: "iep_gap_pct",
    direction: "desc",
  });

  const handleSort = (key: SortKey) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key ? (prev.direction === "desc" ? "asc" : "desc") : "desc",
    }));
  };

  const sortedStocks = useMemo(() => {
    return [...stocks].sort((a, b) => {
      const aVal = (a as any)[sortConfig.key] ?? 0;
      const bVal = (b as any)[sortConfig.key] ?? 0;
      const diff = (aVal as number) - (bVal as number);
      return sortConfig.direction === "desc" ? -diff : diff;
    });
  }, [stocks, sortConfig.key, sortConfig.direction]);

  // Loading skeleton
  if (loading && stocks.length === 0) {
    return (
      <div className="rounded-lg border border-border overflow-hidden bg-card">
        <table className="w-full">
          <thead>
            <tr className="bg-secondary/30 border-b border-border">
              {COLUMNS.map((c) => (
                <th key={c.label} className={`px-3 py-2.5 text-[11px] uppercase tracking-wider text-muted-foreground font-medium ${c.align}`}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 10 }).map((_, i) => (
              <tr key={i} className="border-b border-border/50">
                {COLUMNS.map((_, j) => (
                  <td key={j} className="px-3 py-2">
                    <Skeleton className="h-4 w-full bg-muted/50" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // Empty state
  if (stocks.length === 0 && !loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-muted-foreground rounded-lg border border-border bg-card">
        {searchQuery ? (
          <p className="text-base">No stocks match "{searchQuery}"</p>
        ) : (
          <>
            <Loader2 className="h-8 w-8 animate-spin mb-3 text-primary" />
            <p className="text-base font-medium">Waiting for pre-open data...</p>
            <p className="text-sm mt-1 text-muted-foreground">Live data streams 9:00–9:07 AM IST</p>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border overflow-auto bg-card">
      <table className="w-full">
        <thead className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm">
          <tr className="border-b border-border">
            {COLUMNS.map((col) => (
              <th
                key={col.label}
                onClick={col.sortKey ? () => handleSort(col.sortKey!) : undefined}
                className={`px-3 py-2.5 text-[11px] uppercase tracking-wider font-medium whitespace-nowrap ${col.align} ${
                  col.sortKey
                    ? "cursor-pointer hover:bg-secondary/50 transition-colors select-none text-muted-foreground hover:text-foreground"
                    : "text-muted-foreground"
                } ${sortConfig.key === col.sortKey ? "text-primary" : ""}`}
              >
                <span className="inline-flex items-center gap-1">
                  {col.label}
                  {col.sortKey && sortConfig.key === col.sortKey && (
                    sortConfig.direction === "desc"
                      ? <ChevronDown size={12} className="text-primary" />
                      : <ChevronUp size={12} className="text-primary" />
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedStocks.map((stock, index) => (
            <StockRow key={stock.symbol} stock={stock} rank={index + 1} />
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default StockTable;
