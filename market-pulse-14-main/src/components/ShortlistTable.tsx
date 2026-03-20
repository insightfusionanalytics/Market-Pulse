import React from "react";
import { Stock } from "@/types";
import { formatLargeNumber } from "@/lib/formatters";

interface ShortlistTableProps {
  stocks: Stock[];
  isFrozen: boolean;
  freezeMessage: string | null;
}

export default function ShortlistTable({ stocks, isFrozen, freezeMessage }: ShortlistTableProps) {
  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div>
          <h3 className="text-base font-semibold text-foreground">Rule-Based Shortlist</h3>
          <p className="text-xs text-muted-foreground">
            Stock | Pre-open price change | Pre-open activity metric | Comparison vs 20D average
          </p>
        </div>
        <div className="text-xs">
          <span className={`px-2 py-1 rounded border ${isFrozen ? "bg-amber-500/10 text-amber-400 border-amber-500/30" : "bg-primary/10 text-primary border-primary/30"}`}>
            {isFrozen ? "Frozen" : "Live"}
          </span>
        </div>
      </div>

      {freezeMessage && (
        <div className="px-4 py-2 text-xs text-amber-300 bg-amber-900/20 border-b border-amber-700/40">
          {freezeMessage}
        </div>
      )}

      {stocks.length === 0 ? (
        <div className="px-4 py-8 text-sm text-muted-foreground">
          No shortlisted stocks yet based on current rule thresholds.
        </div>
      ) : (
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-secondary/50 border-b border-border">
              <tr>
                <th className="text-left px-4 py-2 text-xs uppercase tracking-wider text-muted-foreground">Stock</th>
                <th className="text-right px-4 py-2 text-xs uppercase tracking-wider text-muted-foreground">Pre-open change %</th>
                <th className="text-right px-4 py-2 text-xs uppercase tracking-wider text-muted-foreground">Activity metric</th>
                <th className="text-right px-4 py-2 text-xs uppercase tracking-wider text-muted-foreground">20D avg</th>
                <th className="text-right px-4 py-2 text-xs uppercase tracking-wider text-muted-foreground">Vs 20D</th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((s) => {
                const change = Number(s.iep_gap_pct || 0);
                return (
                  <tr key={s.symbol} className="border-b border-border/50 hover:bg-secondary/30">
                    <td className="px-4 py-2 font-semibold text-foreground">{s.symbol}</td>
                    <td className={`px-4 py-2 text-right font-mono ${change > 0 ? "text-success" : change < 0 ? "text-destructive" : "text-muted-foreground"}`}>
                      {change > 0 ? "+" : ""}
                      {change.toFixed(2)}%
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-foreground">
                      {formatLargeNumber(Number(s.preopen_activity_metric || 0))}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-muted-foreground">
                      {formatLargeNumber(Number(s.activity_20d_avg || 0))}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-primary font-semibold">
                      {(Number(s.activity_vs_20d || 0)).toFixed(2)}x
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
