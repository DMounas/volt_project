# Phase 3 — Forecasting Model Card & Technical Specifications

## 1. Model Details
- **Model Name:** VOLT Multi-Vector Quantile Gradient Boosting Forecaster
- **Version:** 1.0.0
- **Model Family:** `HistGradientBoostingRegressor(loss='quantile')` from `scikit-learn` (v1.8.0)
- **Quantiles Modeled:** P10 (10th percentile), P50 (median / central forecast), P90 (90th percentile)
- **Prediction Granularity:** Hourly rolling 24-step horizon ($h \in [1, 24]$)
- **Timezone:** Indian Standard Time (`Asia/Kolkata`, UTC+05:30)
- **Target Variables:**
  1. `fast_charge_demand_mwh`: Cluster hourly DC fast-charging demand (MWh)
  2. `swap_demand_mwh`: Cluster hourly swappable battery energy requirement (MWh)
  3. `solar_available_mwh`: Cluster hourly open-access solar availability (MWh)
  4. `wind_available_mwh`: Cluster hourly open-access wind availability (MWh)
  5. `iex_clearing_price_inr_mwh`: National Indian Energy Exchange Day-Ahead Market clearing price (INR/MWh)

---

## 2. Intended Use & Epistemic Boundaries
- **Intended Use:** Virtual decision-support digital twin simulation, rolling-horizon scheduling, and operational risk assessment under uncertainty.
- **Out-of-Scope Use:** Direct automated financial order submission to the Indian Energy Exchange; live autonomous grid switching; safety-critical protection relay tripping.
- **Provenance Notice:** All training and evaluation data are algorithmically generated and classified as `SYNTHETIC`. Metrics should not be interpreted as empirical guarantees on real utility networks.

---

## 3. Training & Validation Protocol
- **Historical Development Period:** 5 completed calendar years (2021-01-01 to 2025-12-31).
- **Temporal Splitting (No Random Splitting):**
  - **Train:** 2021-01-01 to 2023-12-31 (3 years = 26,280 hours per cluster)
  - **Validation:** 2024-01-01 to 2024-12-31 (1 year = 8,784 hours, leap year calendar)
  - **Untouched Final Test:** 2025-01-01 to 2025-12-31 (1 year = 8,760 hours)
- **No Target Leakage:** Features are strictly computed from past observations observable at forecast origin $T$ ($t \le T$). Lags at $T+h-24$ and $T+h-168$ are strictly past values since $h \le 24$.

---

## 4. Post-Processing & Physical Guardrails
1. **Monotonic Quantile Sorting:** Pointwise sorting guarantees $\hat{y}_{P10} \le \hat{y}_{P50} \le \hat{y}_{P90}$ across all horizons.
2. **Physical Non-Negativity:** All energy quantities and market prices are clipped to $\ge 0.0$.
3. **Astronomical Solar Night Cutoff:** Solar availability is unconditionally set to $0.0\text{ MWh}$ for night hours (19:00 to 05:00 IST).

---

## 5. Performance Metrics & Loss Functions
- **Point Accuracy:** Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), Weighted Absolute Percentage Error (WAPE).
- **Probabilistic Calibration:**
  - Pinball loss: $L_q(y, \hat{y}) = \max(q(y - \hat{y}), (1-q)(\hat{y} - y))$ for $q \in \{0.10, 0.50, 0.90\}$.
  - Interval Coverage: Percentage of actual test observations falling within $[P10, P90]$ (nominal: 80%).
  - Interval Width: Mean $(P90 - P10)$ measuring sharpness.
- **Baseline Comparison:** Evaluated against `SeasonalNaive24` (persistence from same hour yesterday). Models only deployed if test MAE outperforms baseline.
