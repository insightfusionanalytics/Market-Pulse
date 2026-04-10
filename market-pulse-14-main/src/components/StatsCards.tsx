import React from "react";
import { Stock } from "@/types";
import { formatTime } from "@/lib/formatters";
import { BarChart3, TrendingUp, TrendingDown, Clock, Activity } from "lucide-react";

interface StatsCardsProps {
  stocks: Stock[];
  lastUpdate: string;
  filterType?: "all" | "gainers" | "losers";
  setFilterType?: (v: "all" | "gainers" | "losers") => void;
  sessionStatus?: { text: string; color: string; bg?: string } | null;
}

const StatsCards: React.FC<StatsCardsProps> = ({
  stocks,
  lastUpdate,
  filterType = "all",
  setFilterType,
}) => {
  const gainersCount = stocks.filter((s) => (s.iep_gap_pct ?? 0) > 0).length;
  const losersCount = stocks.filter((s) => (s.iep_gap_pct ?? 0) < 0).length;
  const unchangedCount = stocks.length - gainersCount - losersCount;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {/* Total Stocks */}
      <div className="relative overflow-hidden rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/30">
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-primary rounded-l-lg" />
        <div className="flex items-center gap-3 pl-2">
          <div className="p-2 rounded-lg bg-primary/10">
            <BarChart3 className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">Total</p>
            <p className="text-3xl font-bold font-mono tabular-nums text-foreground">{stocks.length}</p>
          </div>
        </div>
      </div>

      {/* Gainers */}
      <button
        className={`relative overflow-hidden rounded-lg border bg-card p-4 text-left transition-all hover:border-success/40 ${
          filterType === "gainers" ? "border-success/50 bg-success/5 ring-1 ring-success/20" : "border-border"
        }`}
        onClick={() => setFilterType?.(filterType === "gainers" ? "all" : "gainers")}
      >
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-success rounded-l-lg" />
        <div className="flex items-center gap-3 pl-2">
          <div className="p-2 rounded-lg bg-success/10">
            <TrendingUp className="h-5 w-5 text-success" />
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium flex items-center gap-1.5">
              Gainers
              {filterType === "gainers" && <span className="w-1.5 h-1.5 rounded-full bg-success" />}
            </p>
            <p className="text-3xl font-bold font-mono tabular-nums text-success">{gainersCount}</p>
          </div>
        </div>
      </button>

      {/* Losers */}
      <button
        className={`relative overflow-hidden rounded-lg border bg-card p-4 text-left transition-all hover:border-destructive/40 ${
          filterType === "losers" ? "border-destructive/50 bg-destructive/5 ring-1 ring-destructive/20" : "border-border"
        }`}
        onClick={() => setFilterType?.(filterType === "losers" ? "all" : "losers")}
      >
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-destructive rounded-l-lg" />
        <div className="flex items-center gap-3 pl-2">
          <div className="p-2 rounded-lg bg-destructive/10">
            <TrendingDown className="h-5 w-5 text-destructive" />
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium flex items-center gap-1.5">
              Losers
              {filterType === "losers" && <span className="w-1.5 h-1.5 rounded-full bg-destructive" />}
            </p>
            <p className="text-3xl font-bold font-mono tabular-nums text-destructive">{losersCount}</p>
          </div>
        </div>
      </button>

      {/* Last Update */}
      <div className="relative overflow-hidden rounded-lg border border-border bg-card p-4 transition-colors hover:border-muted-foreground/30">
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-muted-foreground/40 rounded-l-lg" />
        <div className="flex items-center gap-3 pl-2">
          <div className="p-2 rounded-lg bg-muted/50">
            <Clock className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider font-medium">Last Update</p>
            <p className="text-2xl font-bold font-mono tabular-nums text-foreground">
              {lastUpdate ? formatTime(lastUpdate) : "--:--:--"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default React.memo(StatsCards);
