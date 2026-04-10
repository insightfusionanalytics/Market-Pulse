import React from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Search, BookMarked, X, Download, ArrowUpDown } from "lucide-react";
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
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-border bg-card/80 backdrop-blur-sm px-5 py-3">
      {/* Left group: Sort & Filter */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Sort By */}
        <div className="flex items-center gap-2">
          <ArrowUpDown size={13} className="text-muted-foreground" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortField)}
            className="h-8 rounded-md border border-border bg-secondary/80 px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
          >
            <option value="iep_gap_pct">Gap %</option>
            <option value="iep_gap_inr">Gap ₹</option>
            <option value="iep">IEP</option>
            <option value="bs_ratio">B/S Ratio</option>
            <option value="buy_qty">Buy Qty</option>
            <option value="sell_qty">Sell Qty</option>
            <option value="volume">Volume</option>
          </select>
        </div>

        {/* Order toggle */}
        <div className="flex rounded-md overflow-hidden border border-border">
          {(["desc", "asc"] as const).map((o) => (
            <button
              key={o}
              className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                sortOrder === o
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary/50 text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
              onClick={() => setSortOrder(o)}
            >
              {o === "desc" ? "Desc" : "Asc"}
            </button>
          ))}
        </div>

        {/* Divider */}
        <div className="w-px h-5 bg-border hidden md:block" />

        {/* Show limit */}
        <div className="flex items-center gap-2">
          <Label className="text-xs text-muted-foreground">Show</Label>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value) as StockLimit)}
            className="h-8 rounded-md border border-border bg-secondary/80 px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
          >
            <option value={10}>Top 10</option>
            <option value={25}>Top 25</option>
            <option value={50}>Top 50</option>
            <option value={500}>All 500</option>
          </select>
        </div>
      </div>

      {/* Right group: Search & Actions */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <div className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
              {symbolCount > 1 ? (
                <BookMarked className="h-3.5 w-3.5 text-primary" />
              ) : (
                <Search className="h-3.5 w-3.5 text-muted-foreground" />
              )}
            </div>
            <Input
              placeholder="RELIANCE, TCS, INFY…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Escape" && setSearchQuery("")}
              className={`pl-8 pr-7 w-52 h-8 text-xs bg-secondary/80 border-border text-foreground placeholder:text-muted-foreground transition-colors ${
                symbolCount > 1 ? "border-primary/50 bg-primary/5" : ""
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
          {symbolCount > 1 && (
            <span className="inline-flex items-center gap-1 bg-primary/10 border border-primary/25 text-primary text-xs px-2 py-1 rounded-md whitespace-nowrap font-medium">
              <BookMarked className="h-3 w-3" />
              {symbolCount}
            </span>
          )}
        </div>

        {/* Divider */}
        <div className="w-px h-5 bg-border hidden md:block" />

        {/* Export CSV */}
        {onExportCSV && (
          <Button onClick={onExportCSV} variant="outline" size="sm" className="h-8 text-xs gap-1.5 border-border">
            <Download size={13} />
            CSV
          </Button>
        )}

        {/* Auto Refresh */}
        <div className="flex items-center gap-2">
          <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} className="data-[state=checked]:bg-primary scale-90" />
          <Label className={`text-xs font-medium ${autoRefresh ? "text-primary" : "text-muted-foreground"}`}>
            {autoRefresh && <span className="inline-block w-1.5 h-1.5 rounded-full bg-success mr-1.5 animate-pulse-dot" />}
            Auto
          </Label>
        </div>

        {/* Refresh Interval */}
        <select
          value={refreshIntervalSeconds}
          onChange={(e) => setRefreshIntervalSeconds(Number(e.target.value))}
          className="h-8 rounded-md border border-border bg-secondary/80 px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer disabled:opacity-40"
          disabled={!autoRefresh}
        >
          <option value={5}>5s</option>
          <option value={15}>15s</option>
          <option value={30}>30s</option>
          <option value={60}>60s</option>
        </select>
      </div>
    </div>
  );
};

export default React.memo(ControlsBar);
