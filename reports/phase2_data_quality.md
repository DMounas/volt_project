# Phase 2 — Data Quality, Verification & Ingestion Report

**Document Version:** 2.0 (Post-Audit Remediation)  
**Date:** 2026-11-22  
**Dataset Provenance:** Strictly `SYNTHETIC`  
**Temporal Coverage:** 5 Completed Calendar Years (2021-01-01T00:00:00+05:30 to 2025-12-31T23:00:00+05:30)  
**Total Granular Intervals:** 219,120 Cluster-Hours (43,824 Hours &times; 5 Metro Clusters)  
**IEX 15-Minute Market Intervals:** 175,296 Blocks (43,824 Hours &times; 4 Blocks/Hour)  

---

## 1. Executive Summary

This report documents the structural integrity, physical realism, reproducibility, and audit metrics of the VOLT Phase 2 synthetic data pipeline and IEX market adapter following mandatory audit remediation.

> **CRITICAL METHODOLOGY DISCLOSURE:**  
> All records in this dataset are algorithmically generated and strictly classified as **`SYNTHETIC`**. They are not historical company records, real IEX trading telemetry, or observed physical battery sensor outputs. All historical training, validation, and testing horizons are confined to completed calendar years (2021–2025) to prevent any future-dating anomaly.

---

## 2. Dataset Suite & Checksum Manifest

| Dataset Filename | Logical Scope | Row Count | Compressed Size | SHA-256 Checksum |
|---|---|---|---|---|
| `cluster_hourly.csv.gz` | Hourly weather, EV charging, swap demand & renewables | 219,120 | 8,183.7 KB | `3b6189f31e47a8080f9eaffa40b66b4eed9dc0ad5a3cf26a8b6f63fa822d896e` |
| `iex_dam_15min.csv.gz` | 15-minute IEX Day-Ahead Market clearing prices & volumes | 175,296 | 3,098.1 KB | `1354ed27184c8120fef831c08f29250ec286aaf34e93b232db870249e2a85c9f` |
| `battery_pack_hourly.csv.gz` | Hourly BESS SOC, pack cohorts, degradation & reserves | 219,120 | 1,907.4 KB | `98d538f7d854b359f20f95c6dcc1ee99dc3480ccc08e572d31cc085668e843a0` |
| `customer_requests.csv.gz` | Event-level customer session requests & flexibility flags | 35,000 | 671.9 KB | `d3d825ee86150a237ebe7cdb902993948bed47f0e83b55300420564bea692f8f` |
| `swap_events.csv.gz` | Event-level discrete battery swap transactions & SOC logs | 30,000 | 395.7 KB | `80de1be32d35a4f2b3065e632cf5c7b0ecb0326ad2089bcea42b976c80ae8044` |
| `data_manifest.json` | Master manifest with schema, config hashes & metadata | 1 | 2.9 KB | `Validated JSON` |

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
| **Aggregation Methodology** | `VOLUME_WEIGHTED` ($\sum P_i E_i / \sum E_i$) | Energy/Volume-weighted hourly price | **PASSED** |
| **Dimensional Units Contract** | $E_{\text{block}} = P_{\text{mw}} \times 0.25\text{ h}$; $E_{\text{hour}} = \sum E_{\text{block}}$ | Dimensionally consistent MWh totals | **PASSED** |
| **Timezone Preservation** | `Asia/Kolkata` (UTC+05:30) | Strict operational semantics | **PASSED** |
| **Negative Price Prevention** | 0 negative prices detected | Hard rejection enforced | **PASSED** |

### 4.1 Dimensional Consistency & Example Remediation
In preliminary documentation, four 15-minute scheduled blocks with average power $\sim 4,300\text{ MW}$ were summed ($17,240$) and mislabelled as `MWh-equivalent`. 

The rectified, dimensionally correct calculation enforces:
- **Block 1 (14:00 - 14:15):** Price = 5,420.50 INR/MWh | Scheduled Power = 4,210.0 MW | Cleared Energy = **1,052.50 MWh**
- **Block 2 (14:15 - 14:30):** Price = 5,580.00 INR/MWh | Scheduled Power = 4,350.0 MW | Cleared Energy = **1,087.50 MWh**
- **Block 3 (14:30 - 14:45):** Price = 5,610.25 INR/MWh | Scheduled Power = 4,400.0 MW | Cleared Energy = **1,100.00 MWh**
- **Block 4 (14:45 - 15:00):** Price = 5,515.00 INR/MWh | Scheduled Power = 4,280.0 MW | Cleared Energy = **1,070.00 MWh**
- **Hourly Total Cleared Energy:** $\sum_{b=1}^4 E_b = 0.25 \times 17,240\text{ MW} = \mathbf{4,310.0\text{ MWh}}$ (NOT 17,240 MWh).
- **Hourly Average Cleared Power:** $\frac{1}{4} \sum_{b=1}^4 MW_b = \mathbf{4,310.0\text{ MW}}$.
- **Hourly Volume-Weighted Price:** $\frac{\sum P_b E_b}{\sum E_b} = \mathbf{5,532.48\text{ INR/MWh}}$.

---

## 5. Case-Fact Alignment & Provenance Governance

1. **Total Installed Capacity:** 1,200 MW aggregate capacity across the 5 clusters is preserved.
2. **Modality Distribution:** 60% DC fast-charging (720 MW) and 40% battery-swap stations (480 MW) strictly reflected.
3. **Storage Asset Split:** 600 MWh combined storage is modelled with 300 MWh BESS / 300 MWh swap packs, tagged `ASSUMED` in `assumptions.yaml`.
4. **Open-Access Renewable Reference:** Long-run renewable availability averages ~35% of total portfolio energy without imposing an unphysical flat 35% hourly quota.
5. **No Double-Counting:** Completed swap usable energy (2.25 kWh) is measured once in service delivery. Subsequent battery recharging is accounted solely as electrical grid load.
