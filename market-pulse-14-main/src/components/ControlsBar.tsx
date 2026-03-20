import React from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Search, BookMarked, X } from "lucide-react";
import { SortField, SortOrder, StockLimit } from "@/types";

interface ControlsBarProps {
  sortBy: SortField;
  setSortBy: (v: SortField) => void;
  sortOrder: SortOrder;
  setSortOrder: (v: SortOrder) => void;
  limit: StockLimit;
  setLimit: (v: StockLimit) => void;
  searchQuery: string;
  setSearchQuery: (v: string) => void;
  autoRefresh: boolean;
  setAutoRefresh: (v: boolean) => void;
  refreshIntervalSeconds: number;
  setRefreshIntervalSeconds: (v: number) => void;
  onExportCSV?: () => void;
}

const ControlsBar: React.FC<ControlsBarProps> = ({
  sortBy,
  setSortBy,
  sortOrder,
  setSortOrder,
  limit,
  setLimit,
  searchQuery,
  setSearchQuery,
  autoRefresh,
  setAutoRefresh,
  refreshIntervalSeconds,
  setRefreshIntervalSeconds,
  onExportCSV,
}) => {
  const symbolCount = searchQuery.trim() ? searchQuery.split(/[,\s]+/).filter((s) => s.trim().length > 0).length : 0;

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-border bg-card p-4">
      <div className="flex flex-wrap items-center gap-4">
        {/* Sort By */}
        <div className="flex items-center gap-2">
          <Label className="text-xs text-muted-foreground whitespace-nowrap">Sort by</Label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortField)}
            className="h-9 rounded-md border border-border bg-secondary px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="iep_gap_pct">IEP Gap %</option>
            <option value="iep_gap_inr">IEP Gap ₹</option>
            <option value="iep">IEP Price</option>
            <option value="bs_ratio">B/S Ratio</option>
            <option value="buy_qty">Buy Qty</option>
            <option value="sell_qty">Sell Qty</option>
            <option value="volume">Ind. Volume</option>
          </select>
        </div>

        {/* Order */}
        <div className="flex items-center gap-2">
          <Label className="text-xs text-muted-foreground">Order</Label>
          <div className="flex rounded-md overflow-hidden border border-border">
            {(["desc", "asc"] as const).map((o) => (
              <Button
                key={o}
                size="sm"
                variant={sortOrder === o ? "default" : "ghost"}
                className={`rounded-none text-xs h-9 ${sortOrder === o ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}
                onClick={() => setSortOrder(o)}
              >
                {o === "desc" ? "Desc" : "Asc"}
              </Button>
            ))}
          </div>
        </div>

        {/* Show */}
        <div className="flex items-center gap-2">
          <Label className="text-xs text-muted-foreground">Show</Label>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value) as StockLimit)}
            className="h-9 rounded-md border border-border bg-secondary px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value={10}>Top 10</option>
            <option value={25}>Top 25</option>
            <option value={50}>Top 50</option>
            <option value={500}>All 500</option>
          </select>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {/* Multi-symbol watchlist search */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <div className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
              {symbolCount > 1 ? (
                <BookMarked className="h-4 w-4 text-primary" />
              ) : (
                <Search className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
            <Input
              placeholder="RELIANCE, TCS, INFY…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Escape" && setSearchQuery("")}
              className={`pl-9 pr-8 w-56 h-9 bg-secondary border-border text-foreground placeholder:text-muted-foreground transition-colors ${
                symbolCount > 1 ? "border-primary/60 bg-primary/5" : ""
              }`}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>

          {/* Badge: only shows when 2+ symbols */}
          {symbolCount > 1 && (
            <div className="flex items-center gap-1 bg-primary/10 border border-primary/30 text-primary text-xs px-2 py-1 rounded-md whitespace-nowrap">
              <BookMarked className="h-3 w-3" />
              <span>{symbolCount} symbols</span>
            </div>
          )}
        </div>

        {/* Export CSV */}
        {onExportCSV && (
          <Button onClick={onExportCSV} variant="outline" size="sm" className="h-9">
            📥 Export CSV
          </Button>
        )}

        {/* Auto Refresh */}
        <div className="flex items-center gap-2">
          <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} className="data-[state=checked]:bg-primary" />
          <Label className={`text-xs ${autoRefresh ? "text-primary" : "text-muted-foreground"}`}>
            Auto-refresh {autoRefresh ? "ON" : "OFF"}
          </Label>
        </div>

        {/* Refresh Interval */}
        <div className="flex items-center gap-2">
          <Label className="text-xs text-muted-foreground">Refresh</Label>
          <select
            value={refreshIntervalSeconds}
            onChange={(e) => setRefreshIntervalSeconds(Number(e.target.value))}
            className="h-9 rounded-md border border-border bg-secondary px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            disabled={!autoRefresh}
          >
            <option value={5}>5 sec</option>
            <option value={15}>15 sec</option>
            <option value={30}>30 sec</option>
            <option value={60}>1 min</option>
          </select>
        </div>
      </div>
    </div>
  );
};

export default ControlsBar;
