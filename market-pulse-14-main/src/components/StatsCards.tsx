import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Stock } from "@/types";
import { formatTime } from "@/lib/formatters";
import { AlertTriangle, BarChart3, TrendingUp, TrendingDown, Clock } from "lucide-react";

interface StatsCardsProps {
  stocks: Stock[];
  lastUpdate: string;
  filterType?: "all" | "gainers" | "losers";
  setFilterType?: (v: "all" | "gainers" | "losers") => void;
  sessionStatus?: { text: string; color: string } | null;
}

const StatsCards: React.FC<StatsCardsProps> = ({
  stocks,
  lastUpdate,
  filterType = "all",
  setFilterType,
  sessionStatus,
}) => {
  // Use iep_gap_pct — the correct pre-open metric
  const gainersCount = stocks.filter((s) => (s.iep_gap_pct ?? 0) > 0).length;
  const losersCount = stocks.filter((s) => (s.iep_gap_pct ?? 0) < 0).length;
  const highAlerts = stocks.filter((s) => s.alert_level === "HIGH").length;

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      {/* Total Stocks */}
      <Card className="bg-card border-border">
        <CardContent className="flex items-center gap-3 p-4">
          <BarChart3 className="h-8 w-8 text-primary shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Total Stocks</p>
            <p className="text-2xl font-bold text-primary">{stocks.length}</p>
          </div>
        </CardContent>
      </Card>

      {/* Gainers */}
      <Card
        className={`cursor-pointer hover:border-success/60 transition-all bg-card border-border ${
          filterType === "gainers" ? "border-success/60 bg-success/5" : ""
        }`}
        onClick={() => setFilterType?.(filterType === "gainers" ? "all" : "gainers")}
      >
        <CardContent className="flex items-center gap-3 p-4">
          <TrendingUp className="h-8 w-8 text-success shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-muted-foreground uppercase tracking-wider flex items-center justify-between">
              Gainers
              {filterType === "gainers" && <span className="text-success text-xs">●</span>}
            </p>
            <p className="text-2xl font-bold text-success">{gainersCount}</p>
          </div>
        </CardContent>
      </Card>

      {/* Losers */}
      <Card
        className={`cursor-pointer hover:border-destructive/60 transition-all bg-card border-border ${
          filterType === "losers" ? "border-destructive/60 bg-destructive/5" : ""
        }`}
        onClick={() => setFilterType?.(filterType === "losers" ? "all" : "losers")}
      >
        <CardContent className="flex items-center gap-3 p-4">
          <TrendingDown className="h-8 w-8 text-destructive shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-muted-foreground uppercase tracking-wider flex items-center justify-between">
              Losers
              {filterType === "losers" && <span className="text-destructive text-xs">●</span>}
            </p>
            <p className="text-2xl font-bold text-destructive">{losersCount}</p>
          </div>
        </CardContent>
      </Card>

      {/* Last Update */}
      <Card className="bg-card border-border">
        <CardContent className="flex items-center gap-3 p-4">
          <Clock className="h-8 w-8 text-muted-foreground shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Last Update</p>
            <p className="text-2xl font-bold text-muted-foreground">
              {lastUpdate ? formatTime(lastUpdate) : "--:--:--"}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Session Status (replaces High Alerts card — cleaner) */}
      <Card className="bg-card border-border">
        <CardContent className="flex items-center gap-3 p-4">
          <AlertTriangle className="h-8 w-8 text-yellow-500 shrink-0" />
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Session</p>
            {sessionStatus ? (
              <p className={`text-sm font-bold ${sessionStatus.color}`}>{sessionStatus.text}</p>
            ) : (
              <p className="text-2xl font-bold text-yellow-500">{highAlerts}</p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default StatsCards;
