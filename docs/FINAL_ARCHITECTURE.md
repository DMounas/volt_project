# VOLT: Final System Architecture Document

## 1. High-Level Architecture Overview

VOLT (Virtual Orchestration of Load, Tariffs & Energy) is an end-to-end digital twin and decision-support orchestration platform for a five-city commercial EV fast-charging and battery-swapping network across India.

```
       ┌─────────────────────────────────────────────────────────────┐
       │                Exogenous Market & Weather                   │
       │    IEX DAM Market (15-min)  •  Solar/Wind PPA  •  DISCOM    │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │           Multi-Vector Quantile Forecasting Engine          │
       │   P10 / P50 / P90 Pinball Regression  •  Daylight Split      │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │        Customer Demand Flexibility & Tariff Engine          │
       │   Service Cohorts  •  0.80x-1.20x Tariffs  •  Incentives   │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │     Risk-Aware Two-Stage MILP + CVaR Optimization Engine    │
       │   Pyomo 6.11 / HiGHS 1.16  •  Tail-Risk Hedge (alpha=0.95)   │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼ (Apply Step t=0 Action)
       ┌─────────────────────────────────────────────────────────────┐
       │         Closed-Loop Receding-Horizon MPC Controller         │
       │   1-Hour Step Application  •  Re-optimizes at t+1           │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │           5-Metro Cluster Digital Twin Simulator            │
       │   Exact SOC & Pack Conservation  •  Decoupled Ledgers        │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │                FastAPI Backend & React UI                   │
       │   12 REST API Route Groups  •  7 Interactive Dashboard Tabs │
       └─────────────────────────────────────────────────────────────┘
```

---

## 2. Core Subsystems

### 2.1 Multi-Vector Quantile Forecasting Subsystem (`engine/forecasting/`)
- **Models:** Quantile Gradient Boosted Decision Trees formulating P10, P50, and P90 forecast quantiles.
- **Targets:**
  - Net EV Fast-Charging Demand (MWh) per cluster.
  - Swappable Battery Pack Demand (Integer packs) per cluster.
  - Solar PV Generation (MWh) with forced night-zero cutoffs and daylight-specific evaluation.
  - Wind Turbine Generation (MWh).
  - Indian Energy Exchange (IEX) Day-Ahead Market Clearing Price (₹/MWh).
- **Leakage Prevention:** Strict chronological split: Train (2023), Validation (2024), Test (2025). Origin $t$ forecasts never access future time steps.

### 2.2 Customer Demand Flexibility Subsystem (`engine/customer/`)
- **Customer Segmentation:**
  1. *Emergency Vehicles:* Service Priority 1, 0% flex opt-in, 0 deadline delay.
  2. *Priority Commercial Fleets:* Service Priority 2, guaranteed delivery windows.
  3. *Retail Drivers:* Voluntary opt-in with incentive elasticity response functions.
- **Dynamic Tariff Bands:** Regulated bounds $0.80 \times \bar{T}_{\text{prev}} \le T(t) \le 1.20 \times \bar{T}_{\text{prev}}$ (₹8.96 to ₹13.44/kWh around ₹11.20/kWh baseline).

### 2.3 Risk-Aware Mathematical Optimization Subsystem (`engine/optimization/`)
- **Mathematical Formulation:** Two-stage Mixed-Integer Linear Program (MILP) with Conditional Value-at-Risk (CVaR).
  - *Stage 1 (Here-and-Now):* Regulated dynamic customer tariff tier selection.
  - *Stage 2 (Recourse):* Energy procurement (DISCOM vs IEX vs PPA), stationary BESS charge/discharge schedule, battery pack bay replenishment, customer demand shifting.
- **Objective Function:**
  $$\min \text{Expected Operating Cost} + \lambda \cdot \text{CVaR}_{0.95}(\text{Procurement Cost})$$
- **Invariants Enforced:**
  - Zero inter-city power transfer ($\Delta P_{c_1 \to c_2} \equiv 0.0\text{ MW}$).
  - BESS emergency reserve $\ge 3.0$ MWh per cluster.
  - Swap pack ready reserve $\ge 1,200$ packs per cluster.
  - Substation headroom reserve $\ge 12.0$ MW per cluster.
  - Integer pack inventory conservation $\equiv 24,000$ packs per cluster.

### 2.4 Closed-Loop Rolling MPC Controller (`engine/twin/mpc_controller.py`)
- Receding-horizon controller operating on a 24-hour lookahead window.
- Solves MILP at origin $t$, extracts **strictly the first action interval $t=0$**, applies actions to the digital twin simulator, advances physical states using realized synthetic shocks, shifts customer cohorts by $-t_0$, and repeats at $t+1$.
- Resilient fallback mechanism: switches seamlessly to `HeuristicFallbackScheduler` if the mathematical solver times out or encounters numerical infeasibility.

### 2.5 Digital Twin Simulator (`engine/twin/simulator.py`)
- Simulates exact physical dynamics:
  - Battery pack discrete charging states (Ready, Charging, Depleted, Unavailable).
  - BESS state of charge with bidirectional conversion losses ($93\%$ charge efficiency, $93\%$ discharge efficiency).
  - Substation transformer losses ($1.2\%$), auxiliary station power ($2.5$ MW), distribution line losses ($1.5\%$).
  - Decoupled financial ledgers: retail revenue vs wholesale procurement vs flex incentives vs cell degradation wear.

---

## 3. Technology Stack & Runtime Environment

- **Backend:** Python 3.14.0, FastAPI 0.115+, Pydantic v2, Pyomo 6.11.0, highspy 1.16.0 (HiGHS solver), NumPy, Pandas, Scikit-learn, LightGBM.
- **Frontend:** TypeScript 5.6+, React 18, Vite 8.3, Recharts, Lucide Icons.
- **Operating Environment:** Windows 11 / Linux compatible, multi-core CPU architecture.
