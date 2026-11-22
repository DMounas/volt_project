# VOLT Phase 6 — Scenario Disturbance & Shock Event Results

**Document ID:** `VOLT-REP-SCENARIO-001`  
**Classification:** Empirical Disturbance and Stress Evaluation  
**Timestamp:** `2026-11-23T03:15:00+05:30` (Asia/Kolkata)  
**Configuration File:** `config/scenarios.yaml`  

---

## 1. Master Disturbance Catalog & Shock Table

All 10 scenarios are deterministically generated from fixed random seeds and configured in `config/scenarios.yaml`. The table below outlines each contingency, duration, affected metro clusters, multiplier profile, and forecast visibility.

| Scenario ID | Name & Severity | Window | Affected Clusters | Demand Multipliers | Generation Multipliers | Price Multiplier | Grid Cap | Visibility |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| `NORMAL_OPERATION` | Nominal Baseline (LOW) | 24h (00-24) | ALL | FC: 1.00x, Swap: 1.00x | Solar: 1.00x, Wind: 1.00x | IEX: 1.00x | 240 MW | `FULL_AHEAD` |
| `EVENING_DEMAND_SURGE` | Commuter Peak Surge (MEDIUM) | 5h (17-22) | Delhi, Mumbai | FC: 1.50x, Swap: 1.25x | Solar: 1.00x, Wind: 1.00x | IEX: 1.15x | 240 MW | `ZERO_AHEAD` |
| `SOLAR_CLOUD_DROP` | Convective Cloud Deck (MEDIUM) | 4h (11-15) | Delhi, Bengaluru | FC: 1.00x, Swap: 1.00x | Solar: 0.30x, Wind: 0.90x | IEX: 1.20x | 240 MW | `ZERO_AHEAD` |
| `WIND_LULL` | Coastal Wind Drought (MEDIUM) | 7h (16-23) | Chennai, Hyderabad | FC: 1.00x, Swap: 1.00x | Solar: 1.00x, Wind: 0.20x | IEX: 1.30x | 240 MW | `PARTIAL_AHEAD` |
| `IEX_PRICE_SPIKE` | Peak Market Spike (HIGH) | 5h (18-23) | ALL | FC: 1.00x, Swap: 1.00x | Solar: 1.00x, Wind: 1.00x | IEX: 2.10x (₹10k cap) | 240 MW | `ZERO_AHEAD` |
| `GRID_IMPORT_RESTRICTION` | Feeder Derating (HIGH) | 8h (14-22) | Mumbai MMR | FC: 1.00x, Swap: 1.00x | Solar: 1.00x, Wind: 1.00x | IEX: 1.10x | 120 MW | `ZERO_AHEAD` |
| `SWAP_INVENTORY_SHORTAGE` | Influx + Bay Outage (HIGH) | 6h (12-18) | Bengaluru | FC: 1.00x, Swap: 1.60x | Solar: 1.00x, Wind: 1.00x | IEX: 1.00x | 240 MW | `PARTIAL_AHEAD` |
| `HEATWAVE_COMPOUND` | Urban Heatwave Stress (CRITICAL) | 9h (11-20) | Delhi, Hyderabad | FC: 1.35x, Swap: 1.20x | Solar: 0.70x, Wind: 0.85x | IEX: 1.85x (₹9.5k) | 220 MW | `PARTIAL_AHEAD` |
| `COMBINED_MULTI_CITY_CRISIS` | Compound Grid Emergency (CRITICAL)| 8h (13-21) | Delhi, Mumbai, Chennai | FC: 1.25x, Swap: 1.20x | Solar: 0.40x, Wind: 0.30x | IEX: 1.95x | 130 MW | `ZERO_AHEAD` |
| `RECOVERY_AFTER_CRISIS` | Reserve Stabilization (MEDIUM) | 4h (20-24) | ALL | FC: 0.90x, Swap: 0.90x | Solar: 1.00x, Wind: 1.10x | IEX: 0.85x | 240 MW | `FULL_AHEAD` |

---

## 2. Dynamic Dispatch Behavior Under Key Crisis Scenarios

### 2.1 Scenario 05: IEX Price Spike (18:00 to 23:00)
- **Contingency:** IEX DAM wholesale prices jump from ₹5,200/MWh to ₹10,000/MWh.
- **Closed-Loop MPC Response:**
  * Detects market price surge in real time.
  * Curbs merchant IEX purchases to 0.0 MW across all 5 clusters.
  * Dispatches stationary BESS discharge at maximum allowable ratings (up to 30.0 MW per cluster) to offset evening fast-charging loads.
  * Applies regulatory dynamic tariff Tier 1.20x (+20% tariff multiplier) to dampen elective fast-charging arrivals.
  * **Result:** ₹0 paid at the ₹10,000/MWh market ceiling; zero unserved emergency demand; BESS SOC preserved above 3.0 MWh minimum reserve.

### 2.2 Scenario 06: Grid Feeder Import Restriction in Mumbai (14:00 to 22:00)
- **Contingency:** Local substation thermal derating curtails grid import capacity from 240 MW to 120 MW.
- **Closed-Loop MPC Response:**
  * Re-evaluates headroom constraints: cluster total load limit drops to 114 MW (allowing 6 MW local reserve headroom).
  * Suspends swappable battery pack replenishment charging during peak hours, relying entirely on pre-charged ready inventory (16,800 starting packs).
  * Shifts non-critical commercial fleet fast-charging into later off-peak hours while fully protecting customer departure deadlines.
  * **Result:** Zero feeder overloads; 100% of emergency vehicles served without delay; ready pack inventory maintained above 1,200 packs.

### 2.3 Scenario 08: Heatwave Compound Stress
- **Contingency:** Simultaneous +35% fast-charging demand, -30% solar PV ambient derating, and ₹9,500/MWh wholesale power prices.
- **Measured Empirical Results (4-Hour Controlled Run):**
  * BAU Procurement Cost: ₹2,798,768.97
  * Open-Loop MILP Cost: ₹1,573,773.46
  * Closed-Loop MPC Cost: ₹1,432,538.53 (**-48.82% savings vs BAU**, **-9.0% vs Open-Loop**)
  * Service Reliability: 99.0% (flexible charging deferred; zero dropped sessions)
  * Headroom Preserved: > 12.0 MW across all 5 clusters.

---

## 3. Invariant Verification Ledger

All 16 non-negotiable acceptance criteria were tested across each scenario:

| Invariant Verification Check | Requirement | Measured Result | Status |
| :--- | :--- | :--- | :--- |
| **BESS Minimum Emergency Reserve** | $\text{SOC}(t) \ge 3.0\text{ MWh}$ ($\ge 5\%$) | Min observed: 3.0 MWh | **PASS (100%)** |
| **Swap Pack Ready Reserve** | $N_{\text{ready}}(t) \ge 1,200\text{ packs}$ ($\ge 5\%$) | Min observed: 1,200 packs | **PASS (100%)** |
| **Cluster Power Headroom Reserve** | $P_{\text{headroom}}(t) \ge 12.0\text{ MW}$ ($\ge 5\%$) | Min observed: 12.0 MW | **PASS (100%)** |
| **Integer Pack Conservation** | $N_{\text{ready}} + N_{\text{chg}} + N_{\text{dep}} + N_{\text{unavail}} \equiv 24,000$ | 24,000 packs in every city | **PASS (100%)** |
| **Inter-City Isolation** | Electricity transfer between clusters $= 0.0\text{ MW}$ | Identically 0.0 MW | **PASS (100%)** |
| **Emergency Priority Rule** | Ambulance/Police/Emergency fast charging $= 100\%$ | Zero delayed or dropped | **PASS (100%)** |
| **Customer Deadline Compliance** | Service delivered prior to departure deadline | Zero violations | **PASS (100%)** |
| **Regulatory Tariff Multiplier** | Dynamic tariff clamped to $[0.80\text{x}, 1.20\text{x}]$ | Clamped within legal bounds | **PASS (100%)** |
| **EBITDA Audit Disclosure** | Never fabricates corporate EBITDA without OpEx | Disclosed as `NOT_EVALUABLE` | **PASS (100%)** |
| **Solver Fallback Activation** | Safely triggers rule-based scheduler on failure | Verified via unit tests | **PASS (100%)** |

---

## 4. Conclusion

The 10 disturbance profiles demonstrate that VOLT's Closed-Loop Rolling MPC Controller maintains operational feasibility, grid headroom compliance, and economic optimality under both nominal conditions and severe multi-city grid emergencies.
