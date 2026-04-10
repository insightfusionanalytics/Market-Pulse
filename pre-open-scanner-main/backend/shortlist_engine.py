"""Rule-based shortlist engine with rolling historical baseline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class BaselineStats:
    avg_activity: float
    avg_gap_pct: float
    avg_daily_volume: float
    sample_days: int


class BaselineStore:
    def __init__(self, store_path: Path, lookback_days: int = 20):
        self.store_path = store_path
        self.lookback_days = lookback_days
        self._data: dict[str, Any] = {"symbols": {}}
        self._load()

    def _load(self) -> None:
        if not self.store_path.exists():
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            self._save()
            return
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                self._data = json.load(f) or {"symbols": {}}
        except Exception:
            self._data = {"symbols": {}}

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=True, indent=2)

    def update_from_snapshot(self, stocks: list[dict], snapshot_day: str | None = None) -> None:
        day_key = snapshot_day or date.today().isoformat()
        symbols = self._data.setdefault("symbols", {})

        for stock in stocks:
            symbol = (stock.get("symbol") or "").strip().upper()
            if not symbol:
                continue

            activity_proxy = self._activity_proxy(stock)
            gap_pct = abs(float(stock.get("iep_gap_pct") or 0.0))
            daily_volume = float(stock.get("volume") or 0.0)

            by_date = symbols.setdefault(symbol, {}).setdefault("by_date", {})
            existing = by_date.get(day_key, {})
            by_date[day_key] = {
                "activity_proxy": max(float(existing.get("activity_proxy") or 0.0), activity_proxy),
                "gap_pct": max(float(existing.get("gap_pct") or 0.0), gap_pct),
                "daily_volume": max(float(existing.get("daily_volume") or 0.0), daily_volume),
            }

            self._prune_old_days(by_date)

        self._save()

    def _prune_old_days(self, by_date: dict[str, dict[str, float]]) -> None:
        all_days = sorted(by_date.keys())
        if len(all_days) <= (self.lookback_days + 10):
            return
        to_delete = all_days[: len(all_days) - (self.lookback_days + 10)]
        for day in to_delete:
            by_date.pop(day, None)

    def get_baseline(self, symbol: str, exclude_day: str | None = None) -> BaselineStats | None:
        symbols = self._data.get("symbols", {})
        by_date = symbols.get(symbol, {}).get("by_date", {})
        if not by_date:
            return None

        valid_days = [d for d in sorted(by_date.keys()) if d != exclude_day]
        if not valid_days:
            return None

        recent_days = valid_days[-self.lookback_days :]
        if not recent_days:
            return None

        activities = [float(by_date[d].get("activity_proxy") or 0.0) for d in recent_days]
        gaps = [float(by_date[d].get("gap_pct") or 0.0) for d in recent_days]
        volumes = [float(by_date[d].get("daily_volume") or 0.0) for d in recent_days]

        sample_days = len(recent_days)
        if sample_days == 0:
            return None

        return BaselineStats(
            avg_activity=sum(activities) / sample_days,
            avg_gap_pct=sum(gaps) / sample_days,
            avg_daily_volume=sum(volumes) / sample_days,
            sample_days=sample_days,
        )

    @staticmethod
    def _activity_proxy(stock: dict) -> float:
        volume = float(stock.get("volume") or 0.0)
        if volume > 0:
            return volume
        buy_qty = float(stock.get("buy_qty") or 0.0)
        sell_qty = float(stock.get("sell_qty") or 0.0)
        return buy_qty + sell_qty


DEFAULT_RULES = {
    "lookback_days": 20,
    "mandatory": {
        "activity_spike_ratio": 1.5,
        "min_abs_gap_pct": 0.5,
    },
    "optional": {
        "enabled": {
            "order_imbalance": True,
            "gap_vs_avg": True,
            "liquidity_min_avg_daily_volume": False,
        },
        "buy_sell_ratio_high": 1.5,
        "buy_sell_ratio_low": 0.5,
        "gap_vs_avg_multiplier": 1.2,
        "liquidity_min_avg_daily_volume": 1000000,
        "min_optional_matches": 1,
    },
}


def merge_rules(config_rules: dict | None) -> dict:
    rules = json.loads(json.dumps(DEFAULT_RULES))
    if not isinstance(config_rules, dict):
        return rules

    for top_key in ("lookback_days",):
        if top_key in config_rules:
            rules[top_key] = config_rules[top_key]

    for section in ("mandatory", "optional"):
        if not isinstance(config_rules.get(section), dict):
            continue
        for k, v in config_rules[section].items():
            if isinstance(v, dict) and isinstance(rules[section].get(k), dict):
                rules[section][k].update(v)
            else:
                rules[section][k] = v
    return rules


def evaluate_and_rank(
    stocks: list[dict],
    baseline_store: BaselineStore,
    rules: dict,
    now_day: str | None = None,
) -> tuple[list[dict], list[dict]]:
    day_key = now_day or date.today().isoformat()
    baseline_store.update_from_snapshot(stocks, snapshot_day=day_key)

    mandatory = rules.get("mandatory", {})
    optional = rules.get("optional", {})
    enabled_optional = optional.get("enabled", {})

    activity_spike_threshold = float(mandatory.get("activity_spike_ratio", 1.5))
    min_abs_gap_pct = float(mandatory.get("min_abs_gap_pct", 0.5))

    bs_high = float(optional.get("buy_sell_ratio_high", 1.5))
    bs_low = float(optional.get("buy_sell_ratio_low", 0.5))
    gap_multiplier = float(optional.get("gap_vs_avg_multiplier", 1.2))
    min_liquidity = float(optional.get("liquidity_min_avg_daily_volume", 1000000))
    min_optional_matches = int(optional.get("min_optional_matches", 1))

    enriched: list[dict] = []
    for stock in stocks:
        s = dict(stock)
        symbol = (s.get("symbol") or "").strip().upper()
        # Include current-day rolling values so averages refresh as new snapshots arrive.
        baseline = baseline_store.get_baseline(symbol=symbol)

        activity_proxy = BaselineStore._activity_proxy(s)
        gap_abs = abs(float(s.get("iep_gap_pct") or 0.0))
        bs_ratio = float(s.get("bs_ratio") or 0.0)

        avg_activity = float(baseline.avg_activity) if baseline else 0.0
        avg_gap = float(baseline.avg_gap_pct) if baseline else 0.0
        avg_liquidity = float(baseline.avg_daily_volume) if baseline else 0.0
        sample_days = int(baseline.sample_days) if baseline else 0

        # Separate historical-only baseline for the displayed 20D avg volume
        hist_baseline = baseline_store.get_baseline(symbol=symbol, exclude_day=day_key)
        hist_avg_liquidity = float(hist_baseline.avg_daily_volume) if hist_baseline else 0.0

        activity_vs_20d = (activity_proxy / avg_activity) if avg_activity > 0 else 0.0

        mandatory_activity = activity_vs_20d >= activity_spike_threshold if avg_activity > 0 else False
        mandatory_gap = gap_abs >= min_abs_gap_pct

        opt_order_imbalance = (bs_ratio >= bs_high) or (bs_ratio <= bs_low)
        opt_gap_vs_avg = (gap_abs >= (avg_gap * gap_multiplier)) if avg_gap > 0 else False
        opt_liquidity = avg_liquidity >= min_liquidity if avg_liquidity > 0 else False

        optional_checks: list[tuple[str, bool]] = []
        if bool(enabled_optional.get("order_imbalance", True)):
            optional_checks.append(("order_imbalance", opt_order_imbalance))
        if bool(enabled_optional.get("gap_vs_avg", True)):
            optional_checks.append(("gap_vs_avg", opt_gap_vs_avg))
        if bool(enabled_optional.get("liquidity_min_avg_daily_volume", False)):
            optional_checks.append(("liquidity_min_avg_daily_volume", opt_liquidity))

        optional_matches = sum(1 for _, passed in optional_checks if passed)
        optional_pass = (optional_matches >= min_optional_matches) if optional_checks else True

        qualified = mandatory_activity and mandatory_gap and optional_pass

        reasons: list[str] = []
        if mandatory_activity:
            reasons.append("Activity spike above 20D baseline")
        if mandatory_gap:
            reasons.append("Meaningful pre-open price change")
        if opt_order_imbalance and any(name == "order_imbalance" for name, _ in optional_checks):
            reasons.append("Order imbalance confirmation")
        if opt_gap_vs_avg and any(name == "gap_vs_avg" for name, _ in optional_checks):
            reasons.append("Gap higher than historical average")
        if opt_liquidity and any(name == "liquidity_min_avg_daily_volume" for name, _ in optional_checks):
            reasons.append("Liquidity threshold satisfied")

        s.update(
            {
                "preopen_activity_metric": round(activity_proxy, 2),
                "activity_20d_avg": round(avg_activity, 2),
                "activity_vs_20d": round(activity_vs_20d, 2),
                "gap_20d_avg": round(avg_gap, 2),
                "liquidity_20d_avg": round(hist_avg_liquidity, 2),
                "baseline_sample_days": sample_days,
                "mandatory_activity_pass": mandatory_activity,
                "mandatory_gap_pass": mandatory_gap,
                "optional_matches": optional_matches,
                "optional_required": min_optional_matches,
                "optional_pass": optional_pass,
                "qualified": qualified,
                "flagged": qualified,
                "qualification_reasons": reasons,
            }
        )
        enriched.append(s)

    shortlist = [s for s in enriched if s.get("qualified")]
    shortlist.sort(
        key=lambda s: (
            float(s.get("activity_vs_20d") or 0.0),
            abs(float(s.get("iep_gap_pct") or 0.0)),
        ),
        reverse=True,
    )

    return enriched, shortlist
