import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { getHistoryDates, downloadHistoryCSV, saveSnapshotNow } from "@/lib/api";
import { Download, History, Save, ChevronDown, ChevronUp } from "lucide-react";

function HistoryPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [dates, setDates] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchDates = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getHistoryDates();
      setDates(res.dates);
    } catch (e: any) {
      setError(e.message || "Failed to load history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) fetchDates();
  }, [isOpen]);

  const handleDownload = async (dateStr: string) => {
    setDownloading(dateStr);
    setError(null);
    try {
      await downloadHistoryCSV(dateStr);
    } catch (e: any) {
      setError(e.message || "Download failed");
    } finally {
      setDownloading(null);
    }
  };

  const handleSaveNow = async () => {
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await saveSnapshotNow();
      setSuccessMsg(`Snapshot saved for ${res.date}`);
      fetchDates();
    } catch (e: any) {
      setError(e.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr + "T00:00:00");
      return d.toLocaleDateString("en-IN", {
        weekday: "short",
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="rounded-lg border border-border bg-card">
      {/* Toggle header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-secondary/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <History size={16} className="text-primary" />
          <span className="text-sm font-medium text-foreground">Download History</span>
          {dates.length > 0 && !isOpen && (
            <span className="text-xs text-muted-foreground">({dates.length} days available)</span>
          )}
        </div>
        {isOpen ? (
          <ChevronUp size={16} className="text-muted-foreground" />
        ) : (
          <ChevronDown size={16} className="text-muted-foreground" />
        )}
      </button>

      {/* Expandable content */}
      {isOpen && (
        <div className="border-t border-border px-3 sm:px-4 py-3 space-y-3">
          {/* Save now button */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-2">
            <Button
              onClick={handleSaveNow}
              disabled={saving}
              variant="outline"
              size="sm"
              className="h-9 sm:h-8 text-xs w-full sm:w-auto"
            >
              <Save size={14} className="mr-1" />
              {saving ? "Saving..." : "Save Current Snapshot"}
            </Button>
            <span className="text-[11px] sm:text-xs text-muted-foreground">
              Auto-saves daily at 9:10 AM IST
            </span>
          </div>

          {/* Messages */}
          {error && (
            <div className="text-xs text-destructive bg-destructive/10 px-3 py-1.5 rounded">
              {error}
            </div>
          )}
          {successMsg && (
            <div className="text-xs text-success bg-success/10 px-3 py-1.5 rounded">
              {successMsg}
            </div>
          )}

          {/* Dates list */}
          {loading ? (
            <div className="text-xs text-muted-foreground py-2">Loading...</div>
          ) : dates.length === 0 ? (
            <div className="text-xs text-muted-foreground py-2">
              No saved snapshots yet. Data auto-saves daily at 9:10 AM IST.
            </div>
          ) : (
            <div className="space-y-1.5 max-h-60 overflow-y-auto">
              {dates.map((d) => (
                <div
                  key={d}
                  className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-secondary/50 transition-colors"
                >
                  <span className="text-sm text-foreground">{formatDate(d)}</span>
                  <Button
                    onClick={() => handleDownload(d)}
                    disabled={downloading === d}
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-primary hover:text-primary"
                  >
                    <Download size={14} className="mr-1" />
                    {downloading === d ? "Downloading..." : "CSV"}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default React.memo(HistoryPanel);
