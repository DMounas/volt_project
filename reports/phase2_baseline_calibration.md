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
