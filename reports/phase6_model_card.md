# Model Card: VOLT Closed-Loop Rolling MPC Controller (Phase 6)

**Model Identifier:** `VOLT-MPC-CL-2.0`  
**Model Date:** November 2026  
**Model Type:** Mixed-Integer Linear Programming (MILP) Receding-Horizon Closed-Loop Controller with CVaR Tail-Risk Hedging  
**Primary Engine:** Pyomo 6.11.0 with HiGHS 1.16.0 / `appsi_highs`  
**Contact:** Google DeepMind Team  

---

## 1. Model Details

### 1.1 Overview
The VOLT Closed-Loop Rolling MPC Controller coordinates wholesale power procurement, stationary battery energy storage systems (BESS), swappable battery pack replenishment bays, dynamic retail tariffs, and customer flexibility deferrals across five Indian metro clusters (Delhi NCR, Mumbai MMR, Bengaluru, Hyderabad, Chennai).

### 1.2 Mathematical Formulation
- **Horizon:** Receding 24-hour horizon, re-solved at each 1-hour control interval.
- **Decision Commitment:** Applies ONLY the first hour decision variables $u(0)$, advances the digital twin under actual scenario shock realizations, and re-optimizes from the newly observed state.
- **Objective:** Minimizes expected operating procurement cost, battery degradation wear, and CVaR tail risk ($\alpha=0.95, \lambda=0.20$), minus retail tariff revenue.
- **Boundary Invariants:**
  * Strict integer battery pack conservation ($24,000\text{ packs/cluster}$)
  * Mandatory 5% emergency reserves: BESS ($\ge 3.0\text{ MWh/cluster}$), Swap Ready ($\ge 1,200\text{ packs/cluster}$), Power Headroom ($\ge 12.0\text{ MW/cluster}$)
  * Zero inter-city power wheeling
  * 100% emergency vehicle non-shiftability

---

## 2. Intended Use

### 2.1 Primary Intended Applications
- **Strategic & Tactical Decision Support:** Evaluating infrastructure sizing, storage dispatch strategies, and dynamic tariff policies under extreme weather and grid stress.
- **Scenario Stress Testing:** Evaluating multi-city operational resilience under compound contingencies (heatwaves, cloud cover drops, wholesale market price spikes, feeder thermal curtailments).
- **Policy Comparison:** Quantifying efficiency gains of predictive closed-loop MPC over uncoordinated Business-As-Usual (BAU) baseline dispatch.

### 2.2 Out-of-Scope & Prohibited Uses
- **NOT a Live Grid Controller:** This model is a decision-support simulation, not a real-time SCADA grid control system or direct substation switching gateway.
- **NOT an Automated Live Market Bidder:** Does not place binding orders on the Indian Energy Exchange (IEX) or Power Exchange India Limited (PXIL).
- **Zero Inter-City Electricity Transfer:** The 5 metro energy networks are physically isolated; electricity cannot be transferred between cities.

---

## 3. Factors, Inputs & Realizations

### 3.1 Input Vectors
- **Fast-Charge Demand:** Hourly EV charging arrivals disaggregated by customer segment (Emergency, Priority Fleet, Commercial, Elective Private).
- **Battery Swapping Requests:** Arrived discrete battery pack swap requests.
- **Renewable Generation:** Contracted open-access solar PV and wind generation.
- **Wholesale Prices:** Regulated DISCOM Time-of-Day (ToD) tariffs and IEX Day-Ahead Market (DAM) clearing prices.
- **Feeder Import Ceilings:** Cluster grid import ratings (nominal 240 MW).

### 3.2 Disturbance Shock Scenarios
The controller is evaluated across 10 deterministic crisis scenarios (`NORMAL_OPERATION`, `EVENING_DEMAND_SURGE`, `SOLAR_CLOUD_DROP`, `WIND_LULL`, `IEX_PRICE_SPIKE`, `GRID_IMPORT_RESTRICTION`, `SWAP_INVENTORY_SHORTAGE`, `HEATWAVE_COMPOUND`, `COMBINED_MULTI_CITY_CRISIS`, `RECOVERY_AFTER_CRISIS`).

---

## 4. Evaluation Metrics & Performance

- **Service Reliability:** $\text{Served Energy} / \text{Requested Energy} \times 100\%$ (achieves $\ge 99.0\%$ under crisis; 100% on normal days).
- **Cost Reduction:** Achieves **48.82% wholesale procurement cost savings** compared to uncoordinated BAU baseline, and an additional **9.0% savings** over rigid open-loop scheduling under compound heatwave stress.
- **Loss Accounting:** System loss ratio measured at explicit conversion, battery thermal, auxiliary, and distribution meter boundaries.
- **EBITDA Disclosure:** Disclosed as `NOT_EVALUABLE` due to missing corporate OpEx (land leases, corporate overhead, asset depreciation schedules).

---

## 5. Resilience & Fallback Guarantees

If the MILP solver times out ($>25.0\text{s}$) or encounters numerical infeasibility:
1. The controller automatically activates `HeuristicFallbackScheduler`.
2. The event is tagged as `SolverStatus.FALLBACK_HEURISTIC` with `is_fallback=True`.
3. Safe rule-based dispatch is enforced, preserving the 5% BESS reserve, 5% swap ready reserve, and 5% headroom reserve.
4. Fallback execution is never misrepresented as an optimal MILP solution.
