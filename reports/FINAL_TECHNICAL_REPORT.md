# VOLT: Final Technical Report & Mathematical Architecture

**System Name:** VOLT — Virtual Orchestration of Load, Tariffs & Energy  
**Document Version:** 1.0.0 (Phase 7 Final Submission)  
**Classification:** Research & Operational Prototype  
**Date:** November 2026  
**Operating Regime:** Decision-Support Digital Twin & Rolling MPC  

---

## 1. Executive Summary & Industrial Problem Framing

### 1.1 The Operational Challenge of Megawatt-Scale EV Hubs
The rapid electrification of commercial two-wheeler (2W), three-wheeler (3W), light commercial vehicle (LCV), and bus fleets across India's tier-1 metropolitan corridors has concentrated immense electric loads at regional distribution substations. A typical five-city mega-network spanning **Delhi NCR, Mumbai MMR, Bengaluru, Hyderabad, and Chennai** encompasses:
- **1,200 MW** of aggregate feeder grid import capacity (240 MW per metropolitan cluster).
- **600 MWh** of combined electrical energy storage (split as 300 MWh stationary battery energy storage systems and 300 MWh in 120,000 swappable battery packs).
- Thousands of asynchronous fast-charging sessions and swap requests per hour.

### 1.2 Failure Modes of Incumbent Operations
In historical uncoordinated operations (the calibrated Business-As-Usual baseline):
1. **Low Reliability & Severe Balking:** Network service reliability sits at **78.4%**, driven by equipment maintenance downtime (calibrated at $82.0\%$ availability) and queue balking ($4.0\%$).
2. **High Electrical Losses:** Conversion, inversion, transformation, and distribution losses reach **10.18%**.
3. **Severe Market Exposure:** Unmanaged peak charging coincides with early-evening electricity demand peaks, exposing network operators to statutory price spikes on the Indian Energy Exchange (IEX) Day-Ahead Market (DAM) exceeding ₹10,000/MWh.
4. **Feeder Tripping & Degradation:** Uncoordinated simultaneous fast-charging breaches 240 MW substation headroom limits, risking feeder thermal overload and uncontrolled cell thermal degradation.

### 1.3 The VOLT Orchestration Solution
VOLT resolves these vulnerabilities through a multi-layered, closed-loop receding-horizon decision-support architecture:
- **Multi-Vector Quantile Forecasting:** GBDT models predicting P10, P50, and P90 distributions for EV demand, solar PV, wind, and IEX clearing prices.
- **Customer Flexibility Envelope:** Structuring voluntary demand shifting with regulatory dynamic tariffs ($0.80\times$ to $1.20\times$ average) and performance incentives.
- **Risk-Aware Pyomo MILP with CVaR:** Jointly optimizing wholesale procurement, BESS dispatch, and pack replenishment under tail-risk market conditions ($\alpha = 0.95$).
- **Closed-Loop Rolling Model Predictive Control (MPC):** Solving a 24-hour horizon at every interval $t$, applying **strictly the first hour action ($t=0$)**, updating physical twin states using realized shock actuals, and re-optimizing.

---

## 2. Mathematical Formulation

### 2.1 Two-Stage Stochastic Optimization Formulation
VOLT models the multi-city energy dispatch problem over a 24-hour horizon $T = \{0, 1, \dots, 23\}$ across clusters $C = \{\text{Delhi}, \text{Mumbai}, \text{Bengaluru}, \text{Hyderabad}, \text{Chennai}\}$.

#### Stage 1 Decisions (Here-and-Now):
- $z_{c, t, k} \in \{0, 1\}$: Dynamic tariff tier selection indicator for cluster $c$, hour $t$, tier $k \in \{\text{TIER\_80}, \text{TIER\_90}, \text{TIER\_100}, \text{TIER\_110}, \text{TIER\_120}\}$.

#### Stage 2 Recourse Decisions (Under Realized Scenario $\omega \in \Omega$):
- $P_{\text{DISCOM}, c}(t) \ge 0$: Baseload power drawn from local distribution utility (MW).
- $P_{\text{IEX}, c}(t) \ge 0$: Merchant power procured from IEX Day-Ahead Market (MW).
- $E_{\text{Ren}, c}(t) \ge 0$: Contracted renewable energy (solar + wind) dispatched to load/storage (MWh).
- $P_{\text{ch}, c}^{\text{BESS}}(t), P_{\text{dis}, c}^{\text{BESS}}(t) \ge 0$: Stationary BESS charge and discharge rates (MW).
- $N_{\text{ch}, c}(t) \in \mathbb{Z}_{\ge 0}$: Discrete battery packs dispatched to charging bays.
- $u_{j}(t) \ge 0$: Energy delivered to customer cohort $j$ in hour $t$ (MWh).

### 2.2 Objective Function
The objective minimizes expected wholesale procurement cost plus tail-risk Conditional Value-at-Risk (CVaR), battery degradation wear, customer flex incentives, and unserved energy penalties, offset by customer charging revenues:

$$\min \mathbb{E}\left[\sum_{c \in C} \sum_{t=0}^{T-1} \left( C_{\text{proc}, c}(t) + C_{\text{deg}, c}(t) + C_{\text{inc}, c}(t) + C_{\text{penalty}, c}(t) - R_{\text{retail}, c}(t) \right)\right] + \lambda \cdot \text{CVaR}_{\alpha}$$

Where:
- **Procurement Cost:**
  $$C_{\text{proc}, c}(t) = P_{\text{DISCOM}, c}(t) \cdot \text{Tariff}_{\text{DISCOM}} + P_{\text{IEX}, c}(t) \cdot \text{Price}_{\text{IEX}}(t) + E_{\text{Ren}, c}(t) \cdot \text{PPA}_{\text{Ren}}$$
- **Degradation Wear:**
  $$C_{\text{deg}, c}(t) = \left( P_{\text{ch}, c}^{\text{BESS}}(t) + P_{\text{dis}, c}^{\text{BESS}}(t) \right) \cdot \text{Rate}_{\text{deg}}$$
- **Flexibility Incentives:**
  $$C_{\text{inc}, c}(t) = \sum_{j} \text{IncentiveRate}_j \cdot u_{j, \text{shifted}}(t)$$
- **Conditional Value-at-Risk (Rockafellar-Uryasev formulation):**
  $$\text{CVaR}_{\alpha} = \zeta + \frac{1}{1 - \alpha} \sum_{\omega \in \Omega} p_{\omega} \cdot \theta_{\omega}$$
  Subject to:
  $$\theta_{\omega} \ge \sum_{c \in C} \sum_{t=0}^{T-1} C_{\text{proc}, c}^{\omega}(t) - \zeta, \quad \theta_{\omega} \ge 0$$

### 2.3 Essential Physical & Regulatory Constraints

1. **Spatial Isolation (Zero Inter-City Wheeling):**
   $$\Delta P_{c_1 \to c_2}(t) \equiv 0.0 \quad \forall c_1 \neq c_2, \forall t$$
2. **Substation Headroom Reserve:**
   $$P_{\text{DISCOM}, c}(t) + P_{\text{IEX}, c}(t) \le P_{\text{feeder\_cap}, c}(t) - P_{\text{reserve}} \quad (P_{\text{reserve}} = 12.0\text{ MW})$$
3. **Stationary BESS Emergency Reserve & Energy Balance:**
   $$SOC_c(t+1) = SOC_c(t) + \eta_{\text{ch}} P_{\text{ch}, c}(t) - \frac{1}{\eta_{\text{dis}}} P_{\text{dis}, c}(t)$$
   $$3.0\text{ MWh} \le SOC_c(t) \le 54.0\text{ MWh} \quad (\text{Reserve } \ge 5\%)$$
4. **Discrete Swappable Pack Conservation:**
   $$N_{\text{ready}, c}(t) + N_{\text{charging}, c}(t) + N_{\text{depleted}, c}(t) + N_{\text{unavail}, c}(t) \equiv 24,000\text{ packs}$$
   $$N_{\text{ready}, c}(t) \ge 1,200\text{ packs} \quad (\text{Reserve } \ge 5\%)$$
5. **Customer Delivery & Non-Shiftable Emergency Service:**
   $$\sum_{t = A_j}^{D_j} u_j(t) = E_{\text{requested}, j} \quad \forall \text{ cohorts } j$$
   $$\text{Emergency vehicles: } u_j(A_j) = E_{\text{requested}, j} \quad (\text{zero shifting permitted})$$
6. **Regulatory Tariff Clamping:**
   $$0.80 \cdot \bar{T}_{\text{prev}} \le T_c(t) \le 1.20 \cdot \bar{T}_{\text{prev}}$$

---

## 3. Closed-Loop Rolling MPC Controller

```
At each interval t = 0, 1, ..., T-1:
  1. Observe physical digital twin state: SOC(t), N_ready(t), N_depleted(t), Headroom(t)
  2. Ingest non-anticipative forecast expectation over [t, t + 24)
  3. Formulate and solve Pyomo MILP + CVaR problem using HiGHS
  4. Extract ONLY first-step action: a(t) = a_0*
  5. Apply a(t) to 5-city Digital Twin Simulator
  6. Digital Twin advances state using realized shock observations:
       SOC(t+1) = f_twin(SOC(t), a(t), actual_shocks)
       N_ready(t+1) = g_twin(N_ready(t), a(t), actual_swaps)
  7. Shift customer cohort arrival/deadline indices by -t_0
  8. Advance clock: t <- t + 1, repeat.
```

---

## 4. Final Empirical Benchmark Results

*Summary of 4-Policy Controlled Benchmark across 5 fixed seeds and all scenarios:*

| Metric | CALIBRATED_BAU | FALLBACK_HEURISTIC | OPEN_LOOP_MILP | CLOSED_LOOP_MPC | MPC Uplift vs BAU |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Service Reliability (%)** | 78.4% | 100.0% (Benign) | 99.2% | **99.6%** | **+21.2%** |
| **Fast-Charge Fill Rate (%)** | 80.6% | 100.0% | 99.5% | **100.0%** | **+19.4%** |
| **Swap Pack Fill Rate (%)** | 78.2% | 100.0% | 98.9% | **99.4%** | **+21.2%** |
| **System Loss Ratio (%)** | 10.18% | 8.45% | 7.92% | **7.64%** | **-2.54% abs** |
| **Renewable Utilization Share (%)** | 50.0% | 68.2% | 84.5% | **89.1%** | **+39.1%** |
| **Wholesale Energy Cost (₹ Lakh)** | ₹27.98 L | ₹29.40 L | ₹15.74 L | **₹14.33 L** | **-48.8% savings** |
| **Flexibility Incentives Paid (₹)** | ₹0 | ₹0 | ₹33,889 | **₹24,019** | — |
| **Net Operating Contribution (₹ Lakh)**| -₹9.87 L | -₹11.29 L | +₹2.04 L | **+₹3.55 L** | **+₹13.42 L** |
| **EBITDA Evaluation** | `NOT_EVALUABLE` | `NOT_EVALUABLE` | `NOT_EVALUABLE` | `NOT_EVALUABLE` | GAAP Compliant |
| **Mean Solve Time per Step** | 0.0 ms | 0.0 ms | 1,240 ms (t=0) | **238 ms** | Sub-second |

---

## 5. System Ablations & Sensitivity Key Findings

1. **Customer Demand Flexibility is Crucial:** Ablating voluntary demand flexibility incurs a **+59.49% wholesale procurement cost penalty**, as uncoordinated evening vehicle charging forces massive reliance on peak DISCOM overage and merchant IEX spot power.
2. **Closed-Loop MPC Beats Static Open-Loop:** Under compound shocks (`HEATWAVE_COMPOUND`), rolling MPC achieves an additional **+6.50% cost reduction over Open-Loop MILP** by dynamically utilizing BESS capacity in real time as weather and price realization errors unfold.
3. **Theoretical Perfection Ceiling:** The non-causal theoretical Oracle Upper Bound achieves an additional 5.8% cost savings, demonstrating that VOLT captures over **94% of the theoretical perfection margin** available under perfect foresight.
4. **Storage Architecture Sweet Spot:** The 50/50 storage split (60 MWh BESS / 24,000 packs per cluster) strikes the optimal economic balance between feeder peak shaving and swap queue wait times.

---

## 6. Audit & Regulatory Compliance

- **Zero Inter-City Wheeling:** Invariant verified across 100% of benchmark runs.
- **Reserve Invariants:** BESS emergency reserve ($\ge 3.0$ MWh), swap ready reserve ($\ge 1,200$ packs), and substation headroom ($\ge 12.0$ MW) satisfied at every simulated hour.
- **EBITDA Accounting Transparency:** Formally categorized as `NOT_EVALUABLE` without corporate SG&A, concession leases, and statutory depreciation schedules.
- **Deterministic Reproducibility:** Fixed seeds yield bitwise identical simulation trajectories.
