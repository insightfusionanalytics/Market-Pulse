# Phase-Wise Implementation Plan (Client V1)

This document tracks the implementation of the client requirements in phases.

## Phase 0 - Baseline and Safety

- [x] Local auth, CORS, frontend-backend connectivity fixed.
- [x] Ensure scanner remains decision-support only (no order placement logic).
- [x] Keep Nifty 500 as default universe.

## Phase 1 - Core Rule Engine (Must Implement)

Goal: Convert dashboard from raw market feed viewer into rule-based shortlist engine.

- [x] Add mandatory filter #1:
  - Pre-open activity proxy must be significantly above 20-day average.
- [x] Add mandatory filter #2:
  - Pre-open price change must cross configurable threshold.
- [x] Add optional confirmation filters:
  - Buy vs sell imbalance.
  - Gap vs recent average gap.
  - Liquidity minimum.
- [x] Add configurable thresholds in `config.yaml`.
- [x] Add qualification reasons in API payload for transparency.

## Phase 2 - Historical Baseline Layer (Must Implement)

Goal: Enable per-stock comparison against historical behavior.

- [x] Persist per-stock daily metrics in local store.
- [x] Compute 20-day rolling averages per stock.
- [x] Exclude current day from baseline comparison.
- [x] Attach baseline metrics to each stock:
  - `activity_20d_avg`
  - `activity_vs_20d`
  - `gap_20d_avg`
  - `liquidity_20d_avg`

## Phase 3 - Output and Session Behavior (Must Implement)

Goal: Match required output and lifecycle behavior.

- [x] Provide shortlist-focused API endpoint.
- [x] Mark qualified stocks in primary feed payload.
- [x] Freeze final shortlist after pre-open cutover.
- [x] Keep final shortlist visible until 09:15.
- [ ] Finalize 30-second behavior after client confirmation.

## Phase 4 - Frontend Shortlist UX (Must Implement)

Goal: Present the required simple shortlist output.

- [x] Add simple shortlist table section with required fields:
  - Stock name
  - Pre-open price change
  - Pre-open activity metric
  - Comparison vs 20-day average
- [x] Show phase/freeze status in UI.
- [x] Keep existing detailed table for drill-down.

## Phase 5 - Validation and Acceptance

- [ ] Validate behavior in pre-open timings with live feed.
- [ ] Confirm final shortlist visibility window with client.
- [ ] Final cleanup and threshold tuning with user acceptance.
