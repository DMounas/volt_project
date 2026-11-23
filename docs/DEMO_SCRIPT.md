# VOLT: 3–5 Minute Judge Demonstration Script

## Overview
This script provides a structured, live walk-through of the VOLT platform for hackathon judges, highlighting the real-world operational challenges of massive EV charging hubs, the mathematical rigor of risk-aware rolling MPC, and verifiable empirical benchmark results.

---

## 1. Opening & The Industrial Challenge (0:00 – 0:45)
- **Goal:** Establish the scale, physical bottlenecks, and failure of uncoordinated charging.
- **Narrative:**
  > "Welcome to VOLT (Virtual Orchestration of Load, Tariffs & Energy). Across 5 major Indian metros—Delhi, Mumbai, Bengaluru, Hyderabad, and Chennai—we operate 1,200 MW of grid interconnection capacity, 600 MWh of battery storage, and 120,000 swappable battery packs.
  > Under business-as-usual uncoordinated charging, the network experiences an incumbent 78.4% service reliability and 10.18% energy losses. Stations suffer frequent transformer overloads, customer queue balking, and catastrophic exposure to peak IEX merchant price spikes.
  > Conventional approaches fail because they either treat EV charging as dumb static load or rely on open-loop day-ahead optimization that shatters the moment real weather or market shocks hit."

---

## 2. Platform Architecture & Data Integrity (0:45 – 1:30)
- **Action:** Open Dashboard: `http://localhost:5173`. Point to **Overview** and **Forecasts** tabs.
- **Narrative:**
  > "VOLT solves this by coupling multi-vector quantile forecasting with closed-loop rolling Model Predictive Control.
  > In the **Forecasts** tab, notice our chronological quantile models (P10, P50, P90). For solar generation, we explicitly evaluate daylight-only intervals separately from all-hours metrics so forced night zeros don't inflate statistical coverage.
  > In the **Customer Flexibility** tab, commercial fleets and retail drivers are enrolled into voluntary shifting windows, while emergency services are strictly quarantined with 0% shifting and zero deadline delays."

---

## 3. Live Crisis Simulation: The Heatwave Compound Shock (1:30 – 2:45)
- **Action:** Navigate to **Digital Twin & MPC** tab (`SimulationTab.tsx`).
- **Setup:**
  - Select Scenario: `HEATWAVE_COMPOUND` (Compound evening demand surge + solar heat derating + 40% IEX price spike).
  - Select Policy: `CLOSED_LOOP_MPC`.
  - Click **"Run Simulation"**.
- **Demonstration Points:**
  - **Receding-Horizon Inspector:** Show that VOLT applies **strictly the first hour action ($t=0$)**, steps the digital twin forward with realized shocks, and re-optimizes.
  - **Asset Invariants:** Highlight that throughout the shock:
    * Stationary BESS emergency reserve stays $\ge 3.0\text{ MWh}$ in all 5 clusters.
    * Swappable pack ready reserve stays $\ge 1,200\text{ packs}$.
    * Exact integer pack conservation holds ($\equiv 24,000\text{ packs}$ per cluster).
    * Substation headroom stays $\ge 12.0\text{ MW}$.
    * Inter-city electricity transfer is strictly $0.0\text{ MW}$.
  - **Explainability Drawer:** Open a decision step to show the automated reasoning: BESS discharge peak-shaving, voluntary customer cohort shifting, and dynamic tariff tier selection within legal bounds (0.80x–1.20x).

---

## 4. Benchmark & Ablation Evidence (2:45 – 4:00)
- **Action:** Navigate to **Benchmark & Reports** tab (`BenchmarkReportsTab.tsx`).
- **Demonstration Points:**
  - **Audited Policy Matrix:** Contrast the 4 distinct policies:
    * `CALIBRATED_BAU`: Reconstructed historical uncoordinated operations (78.4% reliability, 10.18% loss).
    * `FALLBACK_HEURISTIC`: Safe deterministic scheduler (preserves 5% reserves, no solver).
    * `OPEN_LOOP_MILP`: Static 24-hour day-ahead plan.
    * `CLOSED_LOOP_MPC`: **48.8% cost savings vs BAU** and **+6.5% additional savings over Open-Loop MILP** while achieving **>99.0% service reliability**.
  - **Ablation Studies:** Point to the marginal value of features:
    * Without customer flexibility: **+59.5% cost penalty**.
    * Without closed-loop MPC (using open-loop MILP): **+6.5% cost penalty**.
    * Theoretical Oracle Bound: Perfect foresight achieves only ~5.8% additional margin, demonstrating that VOLT captures over 94% of the theoretical perfection ceiling.
  - **Statutory EBITDA Disclosure:** Highlight the prominent warning box:
    > "Notice our honest accounting disclosure: Corporate EBITDA is labeled **`NOT_EVALUABLE`**. Unlike teams that fabricate net profit margins, we disclose that without corporate SG&A, substation land concession leases, and depreciation schedules, declaring EBITDA would violate GAAP and Ind AS accounting standards."

---

## 5. Summary & Closing (4:00 – 4:30)
- **Narrative:**
  > "VOLT proves that combining risk-aware Pyomo MILP optimization with high-speed HiGHS solving in a closed-loop receding-horizon MPC controller delivers industrial-grade grid stability, 48% energy cost reduction, and guaranteed reserve invariants under extreme Indian grid stress.
  > All test suites pass 100%, and the entire evaluation is fully reproducible via our CLI harness. Thank you."
