import React, { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Search, BookMarked, X, Download, ArrowUpDown, SlidersHorizontal, ChevronDown } from "lucide-react";
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
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // Reusable control fragments — same elements rendered in different layouts for mobile vs desktop
  const sortControl = (
    <div className="flex items-center gap-2">
      <ArrowUpDown size={13} className="text-muted-foreground shrink-0" />
      <select
        value={sortBy}
        onChange={(e) => setSortBy(e.target.value as SortField)}
        className="h-9 sm:h-8 flex-1 sm:flex-none rounded-md border border-border bg-secondary/80 px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
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
  );

  const orderToggle = (
    <div className="flex rounded-md overflow-hidden border border-border h-9 sm:h-auto">
      {(["desc", "asc"] as const).map((o) => (
        <button
          key={o}
          className={`px-3 sm:py-1.5 text-xs font-medium transition-colors ${
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
  );

  const limitControl = (
    <div className="flex items-center gap-2">
      <Label className="text-xs text-muted-foreground shrink-0">Show</Label>
      <select
        value={limit}
        onChange={(e) => setLimit(Number(e.target.value) as StockLimit)}
        className="h-9 sm:h-8 flex-1 sm:flex-none rounded-md border border-border bg-secondary/80 px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
      >
        <option value={10}>Top 10</option>
        <option value={25}>Top 25</option>
        <option value={50}>Top 50</option>
        <option value={500}>All 500</option>
      </select>
    </div>
  );

  const autoRefreshControl = (
    <div className="flex items-center justify-between sm:justify-start gap-2">
      <div className="flex items-center gap-2">
        <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} className="data-[state=checked]:bg-primary scale-90" />
        <Label className={`text-xs font-medium ${autoRefresh ? "text-primary" : "text-muted-foreground"}`}>
          {autoRefresh && <span className="inline-block w-1.5 h-1.5 rounded-full bg-success mr-1.5 animate-pulse-dot" />}
          Auto-refresh
        </Label>
      </div>
      <select
        value={refreshIntervalSeconds}
        onChange={(e) => setRefreshIntervalSeconds(Number(e.target.value))}
        className="h-9 sm:h-8 rounded-md border border-border bg-secondary/80 px-2.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer disabled:opacity-40"
        disabled={!autoRefresh}
      >
        <option value={5}>5s</option>
        <option value={15}>15s</option>
        <option value={30}>30s</option>
        <option value={60}>60s</option>
      </select>
    </div>
  );

  const csvButton = onExportCSV && (
    <Button onClick={onExportCSV} variant="outline" size="sm" className="h-9 sm:h-8 text-xs gap-1.5 border-border w-full sm:w-auto">
      <Download size={13} />
      Download CSV
    </Button>
  );

  const searchInput = (
    <div className="flex items-center gap-2 flex-1 sm:flex-none">
      <div className="relative flex-1 sm:flex-none">
        <div className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
          {symbolCount > 1 ? (
            <BookMarked className="h-3.5 w-3.5 text-primary" />
          ) : (
            <Search className="h-3.5 w-3.5 text-muted-foreground" />
          )}
        </div>
        <Input
          placeholder="Search RELIANCE, TCS…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Escape" && setSearchQuery("")}
          className={`pl-8 pr-7 w-full sm:w-52 h-9 sm:h-8 text-xs bg-secondary/80 border-border text-foreground placeholder:text-muted-foreground transition-colors ${
            symbolCount > 1 ? "border-primary/50 bg-primary/5" : ""
          }`}
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery("")}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label="Clear search"
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
  );

  return (
    <div className="rounded-lg border border-border bg-card/80 backdrop-blur-sm">
      {/* ── DESKTOP layout (≥ md) — single row, original look ─────────────── */}
      <div className="hidden md:flex flex-wrap items-center justify-between gap-4 px-5 py-3">
        <div className="flex flex-wrap items-center gap-3">
          {sortControl}
          {orderToggle}
          <div className="w-px h-5 bg-border" />
          {limitControl}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {searchInput}
          <div className="w-px h-5 bg-border" />
          {csvButton}
          <div className="flex items-center gap-2">
            <Switch checked={autoRefresh} onCheckedChange={setAutoRefresh} className="data-[state=checked]:bg-primary scale-90" />
            <Label className={`text-xs font-medium ${autoRefresh ? "text-primary" : "text-muted-foreground"}`}>
              {autoRefresh && <span className="inline-block w-1.5 h-1.5 rounded-full bg-success mr-1.5 animate-pulse-dot" />}
              Auto
            </Label>
          </div>
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

      {/* ── MOBILE layout (< md) — search + filters drawer ────────────────── */}
      <div className="md:hidden p-3 space-y-3">
        <div className="flex items-center gap-2">
          {searchInput}
          <button
            onClick={() => setMobileFiltersOpen((v) => !v)}
            className={`flex items-center gap-1.5 h-9 px-3 rounded-md border text-xs font-medium transition-colors shrink-0 ${
              mobileFiltersOpen
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-secondary/80 text-foreground border-border hover:bg-secondary"
            }`}
            aria-expanded={mobileFiltersOpen}
            aria-controls="mobile-filters"
          >
            <SlidersHorizontal size={13} />
            Filters
            <ChevronDown size={13} className={`transition-transform ${mobileFiltersOpen ? "rotate-180" : ""}`} />
          </button>
        </div>

        {mobileFiltersOpen && (
          <div id="mobile-filters" className="space-y-3 pt-2 border-t border-border">
            <div>
              <Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Sort by</Label>
              <div className="flex items-center gap-2 mt-1.5">
                <div className="flex-1">{sortControl}</div>
                {orderToggle}
              </div>
            </div>

            <div>
              <Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Display</Label>
              <div className="mt-1.5">{limitControl}</div>
            </div>

            <div>
              <Label className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">Updates</Label>
              <div className="mt-1.5">{autoRefreshControl}</div>
            </div>

            {csvButton && <div className="pt-1">{csvButton}</div>}
          </div>
        )}
      </div>
    </div>
  );
};

export default React.memo(ControlsBar);
