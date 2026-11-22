# Phase 2 — Baseline Policy Calibration Report

**Status:** CALIBRATED  
**Date:** 2026-11-22  
**Target Benchmarks (Case Reference):** Reliability = 78.0%, Energy Losses = 10.0%  
**Provenance:** SYNTHETIC_CALIBRATION  

---

## 1. Executive Summary

In accordance with Phase 2 requirements, the reconstructed Business-As-Usual (BAU) baseline policy was calibrated against the case study reference benchmarks using bounded physical parameter optimization.

> **CRITICAL SAFEGUARD RULE:**  
> The baseline KPI was **never forced** by writing 0.78 or 0.10 into metric output. Numerators and denominators were measured directly from simulated physical flows.

## 2. Calibration Residuals & Alignment

| Metric | Target Reference | Measured Baseline | Residual | Status |
|---|---|---|---|---|
| **Service Reliability** | **78.0%** | **78.40%** | **+0.40%** | Calibrated Baseline |
| **Energy Loss Ratio** | **10.0%** | **10.18%** | **+0.18%** | Calibrated Baseline |
| **Cumulative Objective Error** | &le; 1.0% | **0.58%** | — | Within Bounded Tolerance |

## 3. Calibrated Physical Parameters

All parameters were selected strictly within realistic engineering bounds and classified as `SYNTHETIC_CALIBRATION`:

| Parameter | Calibrated Value | Allowed Engineering Bounds | Physical Rationale |
|---|---|---|---|
| `station_availability_factor` | `0.8` | [0.72, 0.88] | Equipment downtime, maintenance slots, and charger servicing intervals |
| `charger_efficiency` | `0.935` | [0.90, 0.95] | AC-DC conversion and thermal cooling loss in high-power fast dispensers |
| `swap_charge_efficiency` | `0.9` | [0.86, 0.93] | Pack charging efficiency at 1C standard rate in multi-bay hubs |
| `auxiliary_load_pct` | `0.02` | [0.015, 0.040] | Continuous station HVAC, safety systems, telemetry, and lighting |
| `distribution_loss_pct` | `0.012` | [0.010, 0.025] | Step-down transformer and local bus distribution loss |

## 4. Energy Meter-Boundary Reconciliation Audit

- **Total Intervals Audited:** 3600 cluster-hours
- **Reconciliation Pass Rate:** **100.0%**
- **Maximum Absolute Residual:** **0.00010 MWh** (Tolerance: 0.005 MWh)
- **Mean Absolute Residual:** **0.00003 MWh**
- **Maximum Percentage Residual:** **0.0011%**
- **No-Double-Counting Audit:** PASSED: Swap pack usable energy (2.25 kWh/pack) counted ONCE in service reliability numerator. Subsequent pack charging energy is accounted strictly as an electrical demand flow.
- **Reserve Compliance:** 5.0% emergency reserve locked and maintained across all clusters.

---

## 5. Storage Split & 5% Emergency Reserve Arithmetic Correction

The case study supplies a combined 600 MWh storage figure without specifying the asset split or cluster allocation:
- **Combined Storage (`OBSERVED`):** 600.0 MWh network-wide.
- **Asset Split (`ASSUMED`):** 50/50 baseline assumption &rarr; 300.0 MWh stationary BESS + 300.0 MWh swap pack inventory.
- **5% Emergency Reserve Obligation (`OBSERVED` rule applied to `ASSUMED` split):**
  * Stationary BESS Reserve: $0.05 \times 300.0\text{ MWh} = \mathbf{15.0\text{ MWh}}$ network-wide.
  * Swap Pack Inventory Reserve: $0.05 \times 300.0\text{ MWh} = \mathbf{15.0\text{ MWh}}$ network-wide (6,000 packs network-wide).
  * Combined Network Reserve: $\mathbf{30.0\text{ MWh}}$ network-wide (5% of 600 MWh).
- **Cluster Allocation (`ASSUMED` equal 20% share):**
  * Stationary BESS per Cluster: 60.0 MWh.
  * Swap Pack Inventory per Cluster: 60.0 MWh (24,000 packs at 2.5 kWh nominal).
  * **Per-Cluster 5% Reserve:** $0.05 \times 60.0\text{ MWh} = \mathbf{3.0\text{ MWh}}$ BESS reserve and $0.05 \times 24,000 = \mathbf{1,200\text{ packs}}$ ($\mathbf{3.0\text{ MWh}}$) swap reserve.
  * **Network Sum Invariant:** $\sum_{c=1}^5 3.0\text{ MWh} = \mathbf{15.0\text{ MWh}}$ BESS reserve, and $\sum_{c=1}^5 1,200\text{ packs} = \mathbf{6,000\text{ packs}}$ ($\mathbf{15.0\text{ MWh}}$) swap reserve.

> **CRITICAL ARITHMETIC CORRECTION:**  
> The 15.0 MWh figure represents the network-wide 5% reserve for the 300 MWh asset pool. It is **NOT** a per-city quota. Multiplying 15.0 MWh by 5 cities was a descriptive typographical error in preliminary drafts; the simulation engine and tests strictly enforce 3.0 MWh per cluster, summing to 15.0 MWh network-wide.

---

## 6. Non-Identifiability & Epistemic Boundaries Notice

Calibrating 5 physical parameters (`station_availability_factor`, `charger_efficiency`, `swap_charge_efficiency`, `auxiliary_load_pct`, `distribution_loss_pct`) against 2 aggregate scalar targets (78.0% reliability and 10.0% losses) is a mathematically **underdetermined parameter identification problem**.

### Key Epistemic Safeguards:
1. **Multiple Equivalent Solutions:** An infinite set of parameter combinations within physical bounds can yield similar cumulative residuals ($\le 1.0\%$).
2. **Not Empirical Ground Truth:** Passing unit and integration tests verifies that the digital twin's physical mechanics are self-consistent and bounded; it does **not** prove that these parameters represent measured real-world hardware characteristics.
3. **Classification:** This parameter set is strictly designated as `SYNTHETIC_CALIBRATION`.
4. **Decoupling from Forecasting:** Phase 3 probabilistic forecasting models are trained on historical time series features and evaluated purely on statistical loss metrics (MAE, RMSE, Pinball loss, interval coverage). They are **never** tuned, calibrated, or forced to reproduce the 78% or 10% KPIs.
