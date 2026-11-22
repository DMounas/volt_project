# Phase 2 — Data Quality, Verification & Ingestion Report

**Document Version:** 1.0  
**Date:** 2026-11-22  
**Dataset Provenance:** Strictly `SYNTHETIC`  
**Temporal Coverage:** 5 Calendar Years (2022-01-01T00:00:00+05:30 to 2026-12-31T23:00:00+05:30)  
**Total Granular Intervals:** 219,120 Cluster-Hours (43,824 Hours &times; 5 Metro Clusters)  
**IEX 15-Minute Market Intervals:** 175,296 Blocks (43,824 Hours &times; 4 Blocks/Hour)  

---

## 1. Executive Summary

This report documents the structural integrity, physical realism, reproducibility, and audit metrics of the VOLT Phase 2 synthetic data pipeline and IEX market adapter.

> **CRITICAL METHODOLOGY DISCLOSURE:**  
> All records in this dataset are algorithmically generated and strictly classified as **`SYNTHETIC`**. They are not historical company records, real IEX trading telemetry, or observed physical battery sensor outputs.

---

## 2. Dataset Suite & Checksum Manifest

| Dataset Filename | Logical Scope | Row Count | Compressed Size | SHA-256 Checksum (Prefix) |
|---|---|---|---|---|
| `cluster_hourly.csv.gz` | Hourly weather, EV charging, swap demand & renewables | 219,120 | 7,707.2 KB | `cae00d561ed1...` |
| `iex_dam_15min.csv.gz` | 15-minute IEX Day-Ahead Market clearing prices & volumes | 175,296 | 1,930.4 KB | `5aaf728f18a3...` |
| `battery_pack_hourly.csv.gz` | Hourly BESS SOC, pack cohorts, degradation & reserves | 219,120 | 1,907.5 KB | `06c6e9bf8027...` |
| `customer_requests.csv.gz` | Event-level customer session requests & flexibility flags | 35,000 | 671.9 KB | `7ae6b2095e35...` |
| `swap_events.csv.gz` | Event-level discrete battery swap transactions & SOC logs | 30,000 | 395.8 KB | `007741cf1723...` |
| `data_manifest.json` | Master manifest with schema, config hashes & metadata | 1 | 2.8 KB | `Validated JSON` |

---

## 3. Physical Realism & Boundary Validation

### 3.1 Non-Negativity & Capacity Boundaries
- **Fast-Charge Demand:** All values &ge; 0.0 MWh; hourly demand never exceeds cluster fast-charge capacity (144.0 MW).
- **Battery-Swap Requests:** Integer counts &ge; 0; hourly request volume is physically bounded by station slot throughput and ready pack inventory.
- **Stationary BESS:** SOC strictly maintained within $[0.10, 0.90]$; power charge/discharge rates adhere to 0.5C (30.0 MW per cluster).
- **Solar Irradiance:** Strictly 0.0 W/m² between 18:00 and 06:00 IST; smooth solar noon bell curve attenuated by cloud cover and rainfall.
- **Wind Generation:** Cubic power curves bounded by 50 MW contracted capacity per cluster.

### 3.2 Climate Modeling Across Five Clusters
- **Delhi NCR:** Severe continental range (6°C winter min to 43°C summer max); prominent summer heatwave demand surge.
- **Mumbai MMR:** Coastal tropical (24°C to 34°C); high relative humidity (70–90%); intense southwest monsoon (June–Sept).
- **Bengaluru:** Elevated plateau; moderate year-round temperatures (16°C to 33°C); balanced renewable profile.
- **Hyderabad:** Semi-arid plateau; hot pre-monsoon dry peaks (March–May).
- **Chennai:** Tropical wet/dry; unique northeast winter monsoon (October–December) driving distinct seasonal rain and cloud patterns.

---

## 4. IEX 15-Minute Market Adapter Audit

The IEX adapter (`engine.data.IEXMarketAdapter`) was evaluated across the 175,296 raw 15-minute market records:

| Audit Parameter | Measured Metric | Specification Requirement | Result |
|---|---|---|---|
| **Complete Hours Processed** | 43,824 hours | 100% of expected hours | **PASSED** |
| **Blocks Per Complete Hour** | Exactly 4 blocks (`:00`, `:15`, `:30`, `:45`) | Exactly 4 blocks | **PASSED** |
| **Missing Blocks Detected** | 0 missing blocks | Explicitly reported in diagnostics | **PASSED** |
| **Duplicate Blocks Handled** | 0 duplicates | Deduplicated cleanly | **PASSED** |
| **Aggregation Methodology** | `VOLUME_WEIGHTED` ($\sum P_i V_i / \sum V_i$) | Required when volume is present | **PASSED** |
| **Timezone Preservation** | `Asia/Kolkata` (UTC+05:30) | Strict operational semantics | **PASSED** |
| **Negative Price Prevention** | 0 negative prices detected | Hard rejection enforced | **PASSED** |

---

## 5. Case-Fact Alignment & Provenance Governance

1. **Total Installed Capacity:** 1,200 MW aggregate capacity across the 5 clusters is preserved.
2. **Modality Distribution:** 60% DC fast-charging (720 MW) and 40% battery-swap stations (480 MW) strictly reflected.
3. **Storage Asset Split:** 600 MWh combined storage is modelled with 300 MWh BESS / 300 MWh swap packs, tagged `ASSUMED` in `assumptions.yaml`.
4. **Open-Access Renewable Reference:** Long-run renewable availability averages ~35% of total portfolio energy without imposing an unphysical flat 35% hourly quota.
5. **No Double-Counting:** Completed swap usable energy (2.25 kWh) is measured once in service delivery. Subsequent battery recharging is accounted solely as electrical grid load.
