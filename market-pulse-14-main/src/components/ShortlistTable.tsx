import React from "react";
import { Stock } from "@/types";
import { formatLargeNumber } from "@/lib/formatters";

interface ShortlistTableProps {
  stocks: Stock[];
  isFrozen: boolean;
  freezeMessage: string | null;
}

function ShortlistTable({ stocks, isFrozen, freezeMessage }: ShortlistTableProps) {
  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-secondary/20">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Rule-Based Shortlist</h3>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Pre-open change | Activity metric | 20D average comparison
          </p>
        </div>
        <span className={`text-[11px] font-medium px-2.5 py-1 rounded-full border ${
          isFrozen
            ? "bg-amber-500/10 text-amber-400 border-amber-500/25"
            : "bg-success/10 text-success border-success/25"
        }`}>
          {isFrozen ? "Frozen" : "Live"}
        </span>
      </div>

      {freezeMessage && (
        <div className="px-5 py-2 text-xs text-amber-300 bg-amber-900/15 border-b border-amber-700/30">
          {freezeMessage}
        </div>
      )}

      {stocks.length === 0 ? (
        <div className="px-5 py-8 text-sm text-muted-foreground text-center">
          No shortlisted stocks yet based on current rule thresholds.
        </div>
      ) : (
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-secondary/15 border-b border-border">
              <tr>
                <th className="text-left px-4 py-2 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">Stock</th>
                <th className="text-right px-4 py-2 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">Change %</th>
                <th className="text-right px-4 py-2 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">Activity</th>
                <th className="text-right px-4 py-2 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">20D Avg</th>
                <th className="text-right px-4 py-2 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">Ratio</th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((s, i) => {
                const change = Number(s.iep_gap_pct || 0);
                return (
                  <tr key={s.symbol} className={`border-b border-border/40 hover:bg-secondary/30 transition-colors ${i % 2 === 0 ? "bg-secondary/[0.04]" : ""}`}>
                    <td className="px-4 py-2 font-semibold text-foreground">{s.symbol}</td>
                    <td className={`px-4 py-2 text-right font-mono tabular-nums font-medium ${change > 0 ? "text-success" : change < 0 ? "text-destructive" : "text-muted-foreground"}`}>
                      {change > 0 ? "+" : ""}{change.toFixed(2)}%
                    </td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums text-foreground">
                      {formatLargeNumber(Number(s.preopen_activity_metric || 0))}
                    </td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums text-muted-foreground">
                      {formatLargeNumber(Number(s.activity_20d_avg || 0))}
                    </td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums text-primary font-semibold">
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

export default React.memo(ShortlistTable);
