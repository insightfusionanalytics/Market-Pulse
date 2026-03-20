import React, { useState, useMemo } from "react";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Stock } from "@/types";
import { formatCurrency, formatLargeNumber, formatPercentage, extractSymbolName } from "@/lib/formatters";
import { Loader2 } from "lucide-react";

type SortKey = "iep" | "prev_close" | "iep_gap_inr" | "iep_gap_pct" | "buy_qty" | "sell_qty" | "bs_ratio" | "volume";
type SortDirection = "asc" | "desc";

interface StockTableProps {
  stocks: Stock[];
  loading: boolean;
  searchQuery: string;
}

function SignalBadge({ signal }: { signal: string }) {
  if (signal === "BUY BIAS") {
    return (
      <span className="inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-bold bg-success/15 text-success border border-success/30">
        🟢 BUY
      </span>
    );
  }
  if (signal === "SELL BIAS") {
    return (
      <span className="inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-bold bg-destructive/15 text-destructive border border-destructive/30">
        🔴 SELL
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-bold bg-muted/50 text-muted-foreground border border-border">
      ⚪ NEUTRAL
    </span>
  );
}

const StockRow = React.memo(({ stock, rank }: { stock: Stock; rank: number }) => {
  const gapPct = stock.iep_gap_pct ?? 0;
  const isGainer = gapPct > 0;
  const isLoser = gapPct < 0;
  const isHighlight = stock.alert_level === "HIGH";

  const gapColor = isGainer ? "text-success" : isLoser ? "text-destructive" : "text-muted-foreground";

  return (
    <TableRow
      className={`border-border hover:bg-secondary/50 transition-colors ${
        isHighlight ? (isGainer ? "bg-success/5" : "bg-destructive/5") : ""
      }`}
    >
      {/* # */}
      <TableCell className="text-muted-foreground font-mono text-xs w-8">{rank}</TableCell>

      {/* Symbol */}
      <TableCell className="font-bold text-foreground min-w-[100px]">
        <div className="flex items-center gap-1">
          {stock.flagged && <span className="text-xs bg-yellow-500 text-black px-1 rounded font-bold">⚑</span>}
          {extractSymbolName(stock.symbol)}
        </div>
      </TableCell>

      {/* IEP */}
      <TableCell className="font-mono font-bold text-foreground">
        {stock.iep > 0 ? formatCurrency(stock.iep) : "–"}
      </TableCell>

      {/* Prev Close */}
      <TableCell className="font-mono text-muted-foreground">{formatCurrency(stock.prev_close)}</TableCell>

      {/* IEP Gap ₹ */}
      <TableCell className={`font-mono font-semibold ${gapColor}`}>
        {stock.iep_gap_inr != null ? `${stock.iep_gap_inr > 0 ? "+" : ""}${formatCurrency(stock.iep_gap_inr)}` : "–"}
      </TableCell>

      {/* IEP Gap % */}
      <TableCell className={`font-mono font-bold ${Math.abs(gapPct) >= 2.0 ? gapColor : "text-muted-foreground"}`}>
        {gapPct != null ? `${gapPct > 0 ? "+" : ""}${gapPct.toFixed(2)}%` : "–"}
      </TableCell>

      {/* Buy Qty */}
      <TableCell className="font-mono text-muted-foreground">{formatLargeNumber(stock.buy_qty)}</TableCell>

      {/* Sell Qty */}
      <TableCell className="font-mono text-muted-foreground">{formatLargeNumber(stock.sell_qty)}</TableCell>

      {/* B/S Ratio */}
      <TableCell
        className={`font-mono font-bold ${
          (stock.bs_ratio ?? 0) < 0.5
            ? "text-destructive"
            : (stock.bs_ratio ?? 0) > 1.5
              ? "text-success"
              : "text-muted-foreground"
        }`}
      >
        {stock.bs_ratio != null ? stock.bs_ratio.toFixed(2) : "–"}
      </TableCell>

      {/* Signal */}
      <TableCell>
        <SignalBadge signal={stock.signal ?? "NEUTRAL"} />
      </TableCell>

      {/* Volume (Indicative) */}
      <TableCell className="font-mono text-muted-foreground">
        {stock.volume > 0 ? formatLargeNumber(stock.volume) : "–"}
      </TableCell>

      {/* Last Updated */}
      <TableCell className="font-mono text-xs text-muted-foreground">{stock.last_updated ?? "–"}</TableCell>
    </TableRow>
  );
});
StockRow.displayName = "StockRow";

// Column headers
const COLUMNS = [
  { label: "#", sortKey: null },
  { label: "Symbol", sortKey: null },
  { label: "IEP", sortKey: "iep" as SortKey },
  { label: "Prev Close", sortKey: null },
  { label: "IEP Gap ₹", sortKey: "iep_gap_inr" as SortKey },
  { label: "IEP Gap %", sortKey: "iep_gap_pct" as SortKey },
  { label: "Buy Qty", sortKey: "buy_qty" as SortKey },
  { label: "Sell Qty", sortKey: "sell_qty" as SortKey },
  { label: "B/S Ratio", sortKey: "bs_ratio" as SortKey },
  { label: "Signal", sortKey: null },
  { label: "Ind. Volume", sortKey: "volume" as SortKey },
  { label: "Updated", sortKey: null },
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
      <div className="rounded-lg border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-border bg-secondary/50 hover:bg-secondary/50">
              {COLUMNS.map((c) => (
                <TableHead key={c.label} className="text-xs uppercase tracking-wider text-muted-foreground">
                  {c.label}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 10 }).map((_, i) => (
              <TableRow key={i} className="border-border">
                {COLUMNS.map((_, j) => (
                  <TableCell key={j}>
                    <Skeleton className="h-4 w-full bg-muted" />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  // Empty state
  if (stocks.length === 0 && !loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
        {searchQuery ? (
          <p className="text-lg">No stocks match "{searchQuery}"</p>
        ) : (
          <>
            <Loader2 className="h-8 w-8 animate-spin mb-3 text-primary" />
            <p className="text-lg">Waiting for pre-open data...</p>
            <p className="text-sm mt-1 text-muted-foreground">Live data streams 9:00–9:07 AM IST</p>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border overflow-auto">
      <Table>
        <TableHeader>
          <TableRow className="border-border bg-secondary/50 hover:bg-secondary/50">
            {COLUMNS.map((col) =>
              col.sortKey ? (
                <TableHead
                  key={col.label}
                  onClick={() => handleSort(col.sortKey!)}
                  className="text-xs uppercase tracking-wider text-muted-foreground cursor-pointer hover:bg-muted/80 transition-colors select-none whitespace-nowrap"
                >
                  {col.label}
                  {sortConfig.key === col.sortKey && (
                    <span className="ml-1 opacity-80">{sortConfig.direction === "desc" ? "↓" : "↑"}</span>
                  )}
                </TableHead>
              ) : (
                <TableHead
                  key={col.label}
                  className="text-xs uppercase tracking-wider text-muted-foreground whitespace-nowrap"
                >
                  {col.label}
                </TableHead>
              ),
            )}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedStocks.map((stock, index) => (
            <StockRow key={stock.symbol} stock={stock} rank={index + 1} />
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default StockTable;
