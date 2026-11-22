# VOLT Optimization Engine — Mathematical Formulation Specification

**Document Version:** 1.0.0  
**Phase:** Phase 5 — Mathematical Optimization (MILP)  
**Solver:** HiGHS 1.16.0 via Pyomo 6.11.0 (`appsi_highs`)  
**Units Convention:** Power in Megawatts ($\text{MW}$), Energy in Megawatt-hours ($\text{MWh}$), Pack counts in Integers, Currency in Indian Rupees ($\text{INR}$).

---

## 1. Index Sets & Subscripts

| Symbol | Set Definition | Elements |
| :--- | :--- | :--- |
| $c \in \mathcal{C}$ | Metro Clusters (5 cities) | $\{\text{delhi\_ncr}, \text{mumbai\_mmr}, \text{bengaluru}, \text{hyderabad}, \text{chennai}\}$ |
| $t \in \mathcal{T}$ | Hourly Time Intervals (24 hours) | $\{0, 1, 2, \dots, 23\}$ |
| $s \in \mathcal{S}$ | Disturbance Scenarios | $\{\text{NORMAL}, \text{PEAK\_SQUEEZE}, \text{RENEWABLE\_DROUGHT}, \text{MARKET\_SPIKE}\}$ |
| $k \in \mathcal{K}$ | Discrete Dynamic Tariff Tiers | $\{0.80x, 0.90x, 1.00x, 1.10x, 1.20x\}$ |
| $h \in \mathcal{H}_{c,t}$ | Aggregated Fast Charging Cohorts | Grouped by (arrival hour, deadline hour, segment, flexibility) |

---

## 2. Model Parameters

| Parameter | Symbol | Unit | Default Value | Description |
| :--- | :--- | :--- | :--- | :--- |
| Cluster Grid Limit | $P_{c}^{\text{grid\_cap}}$ | MW | 240.0 | Total installed power capacity per cluster |
| Headroom Reserve | $R_{c}^{\text{headroom}}$ | MW | 12.0 | Mandatory 5% power capacity headroom reserve |
| IEX Eligibility Fraction | $\beta_{\text{iex}}$ | Fraction | 0.25 | Max fraction of grid import allowed from IEX DAM (60 MW) |
| Loss Factor | $\alpha_{\text{loss}}$ | Fraction | 0.0132 | Network transformation & distribution loss factor (1.32%) |
| BESS Capacity | $E^{\text{bess\_cap}}$ | MWh | 60.0 | Stationary storage capacity per cluster |
| BESS Min Reserve | $E^{\text{bess\_min}}$ | MWh | 3.0 | Mandatory 5% emergency BESS reserve |
| BESS Max Operating SOC | $E^{\text{bess\_max}}$ | MWh | 54.0 | Maximum operational SOC (90% rating) |
| BESS Charge Power Cap | $P^{\text{bess\_ch\_max}}$ | MW | 30.0 | Maximum AC-to-DC charging power |
| BESS Discharge Power Cap | $P^{\text{bess\_dis\_max}}$| MW | 30.0 | Maximum DC-to-AC discharging power |
| BESS Charge Efficiency | $\eta_{\text{bess\_ch}}$ | Fraction | 0.93 | AC-to-DC conversion efficiency |
| BESS Discharge Efficiency | $\eta_{\text{bess\_dis}}$ | Fraction | 0.93 | DC-to-AC conversion efficiency |
| BESS Degradation Cost | $c_{\text{deg}}$ | INR/MWh | 1250.0 | Battery wear replacement proxy cost |
| Swap Pack Inventory | $N^{\text{total}}$ | Integer | 24,000 | Total pack inventory per cluster |
| Swap Min Reserve | $N^{\text{ready\_min}}$ | Integer | 1,200 | Mandatory 5% ready pack reserve |
| Swap Usable Energy | $E^{\text{pack\_kwh}}$ | kWh | 2.25 | Usable energy delivered per pack swap |
| Swap Bay Power Rating | $P^{\text{bay\_max}}$ | MW | 96.0 | Installed swap charging bay capacity |
| Swap Bay Efficiency | $\eta_{\text{swap\_ch}}$ | Fraction | 0.90 | Swap bay pack recharge efficiency |
| Base Retail Tariff | $\bar{T}_{c}^{\text{prev}}$ | INR/kWh | 11.20 | Previous day volume-weighted retail tariff |
| CVaR Confidence | $\alpha_{\text{cvar}}$ | Fraction | 0.95 | Confidence percentile for tail-risk evaluation |
| CVaR Risk Weight | $\lambda_{\text{risk}}$ | Fraction | 0.20 | Weight assigned to CVaR in objective (0.0 for Det P50) |

---

## 3. Decision Variables

### 3.1 First-Stage Variables (Scenario-Independent)
- $u_{c,t,k} \in \{0, 1\}$: Binary indicator that dynamic tariff tier $k$ is selected for cluster $c$ at hour $t$.

### 3.2 Second-Stage Variables (Scenario-Dependent, $s \in \mathcal{S}$)
- $P_{c,t,s}^{\text{discom}} \in [0, 228.0]$: Electricity procurement from regional DISCOM (MW).
- $P_{c,t,s}^{\text{iex}} \in [0, 60.0]$: Electricity procurement from IEX Day-Ahead Market (MW).
- $P_{c,t,s}^{\text{ren\_used}} \in [0, P_{c,t,s}^{\text{ren\_avail}}]$: Open-access clean solar/wind energy utilized (MW).
- $P_{c,t,s}^{\text{ren\_curt}} \ge 0$: Clean solar/wind curtailed (MW).
- $P_{c,t,s}^{\text{bess\_ch}} \in [0, 30.0]$: Stationary BESS charging power (MW).
- $P_{c,t,s}^{\text{bess\_dis}} \in [0, 30.0]$: Stationary BESS discharging power (MW).
- $E_{c,t,s}^{\text{bess}} \in [3.0, 54.0]$: Stationary BESS State of Charge at end of hour $t$ (MWh).
- $N_{c,t,s}^{\text{start\_ch}} \in \mathbb{Z}_{\ge 0}$: Depleted packs admitted to charging bays at hour $t$.
- $N_{c,t,s}^{\text{ready}} \ge 1,200$: Ready packs available in battery swap inventory.
- $N_{c,t,s}^{\text{dep}} \ge 0$: Depleted packs awaiting charging.
- $E_{h,t',s}^{\text{fc\_sched}} \ge 0$: Energy delivered to cohort $h$ in interval $t' \in [T_h^{\text{arr}}, T_h^{\text{dead}}]$ (MWh).
- $\eta \in \mathbb{R}$: VaR threshold for Rockafellar-Uryasev CVaR formulation (INR).
- $u_s \ge 0$: Auxiliary shortfall variable for scenario $s$ under CVaR (INR).

---

## 4. Mathematical Constraints

### 4.1 Intra-Cluster Nodal Energy Balance (Zero Inter-City Transfer)
For each cluster $c \in \mathcal{C}$, hour $t \in \mathcal{T}$, and scenario $s \in \mathcal{S}$:
$$
P_{c,t,s}^{\text{discom}} + P_{c,t,s}^{\text{iex}} + P_{c,t,s}^{\text{ren\_used}} + \eta_{\text{bess\_dis}} P_{c,t,s}^{\text{bess\_dis}} = P_{c,t,s}^{\text{fc\_served}} + P_{c,t,s}^{\text{swap\_ch}} + P_{c,t,s}^{\text{bess\_ch}} + P_{c,t,s}^{\text{loss}}
$$
Where:
$$
P_{c,t,s}^{\text{fc\_served}} = \sum_{h \in \mathcal{H}_{c} : t \in [T_h^{\text{arr}}, T_h^{\text{dead}}]} E_{h,t,s}^{\text{fc\_sched}}
$$
$$
P_{c,t,s}^{\text{swap\_ch}} = \frac{N_{c,t,s}^{\text{start\_ch}} \times E^{\text{pack\_kwh}}}{1000 \times \eta_{\text{swap\_ch}}}
$$
$$
P_{c,t,s}^{\text{loss}} = \alpha_{\text{loss}} \left( P_{c,t,s}^{\text{fc\_served}} + P_{c,t,s}^{\text{swap\_ch}} + P_{c,t,s}^{\text{bess\_ch}} \right)
$$

### 4.2 Grid Interconnection & Power Capacity Headroom Guardrail
$$
P_{c,t,s}^{\text{discom}} + P_{c,t,s}^{\text{iex}} \le P_{c}^{\text{grid\_cap}} - R_{c}^{\text{headroom}} \quad (= 228.0\text{ MW})
$$
$$
P_{c,t,s}^{\text{headroom}} = P_{c}^{\text{grid\_cap}} - \left( P_{c,t,s}^{\text{discom}} + P_{c,t,s}^{\text{iex}} \right) \ge 12.0\text{ MW}
$$

### 4.3 IEX Day-Ahead Market Eligibility Cap
$$
P_{c,t,s}^{\text{iex}} \le \beta_{\text{iex}} \times P_{c}^{\text{grid\_cap}} \quad (= 60.0\text{ MW})
$$

### 4.4 Stationary BESS State of Charge Transition & Bounds
$$
E_{c,t,s}^{\text{bess}} = E_{c,t-1,s}^{\text{bess}} + \eta_{\text{bess\_ch}} P_{c,t,s}^{\text{bess\_ch}} \Delta t - \frac{1}{\eta_{\text{bess\_dis}}} P_{c,t,s}^{\text{bess\_dis}} \Delta t
$$
$$
3.0\text{ MWh} \le E_{c,t,s}^{\text{bess}} \le 54.0\text{ MWh} \quad (\forall c, t, s)
$$

### 4.5 Swappable Battery Pack Inventory Transitions
$$
N_{c,t,s}^{\text{ready}} = N_{c,t-1,s}^{\text{ready}} - N_{c,t,s}^{\text{swap\_req}} + N_{c,t-1,s}^{\text{start\_ch}}
$$
$$
N_{c,t,s}^{\text{dep}} = N_{c,t-1,s}^{\text{dep}} + N_{c,t,s}^{\text{swap\_req}} - N_{c,t,s}^{\text{start\_ch}}
$$
$$
N_{c,t,s}^{\text{chg}} = N_{c,t,s}^{\text{start\_ch}}
$$
$$
N_{c,t,s}^{\text{ready}} + N_{c,t,s}^{\text{chg}} + N_{c,t,s}^{\text{dep}} = 24,000\text{ packs}
$$
$$
N_{c,t,s}^{\text{ready}} \ge 1,200\text{ packs} \quad (\text{5\% Mandatory Reserve})
$$
$$
P_{c,t,s}^{\text{swap\_ch}} \le 96.0\text{ MW} \quad (\text{Bay Power Capacity})
$$

### 4.6 Fast Charging Customer Cohort Delivery Contract
For each cohort $h \in \mathcal{H}_c$:
$$
\sum_{t' = T_h^{\text{arr}}}^{T_h^{\text{dead}}} E_{h,t',s}^{\text{fc\_sched}} = E_h^{\text{total\_requested}}
$$
For non-flexible cohorts (`EMERGENCY`, `PRIORITY_FLEET`, or non-opt-in):
$$
E_{h,T_h^{\text{arr}},s}^{\text{fc\_sched}} = E_h^{\text{total\_requested}} \quad (\text{Immediate Zero-Delay Service})
$$

### 4.7 Discrete Dynamic Tariff Selection & Non-Anticipativity
$$
\sum_{k \in \mathcal{K}} u_{c,t,k} = 1 \quad (\forall c, t)
$$
$$
T_{c,t} = \sum_{k \in \mathcal{K}} u_{c,t,k} \cdot \left( m_k \times \bar{T}_{c}^{\text{prev}} \right), \quad m_k \in \{0.80, 0.90, 1.00, 1.10, 1.20\}
$$
> Notice: $u_{c,t,k}$ has **no scenario index $s$**, mathematically proving first-stage non-anticipativity across all disturbance scenarios.

---

## 5. Objective Function & Risk Formulation

$$
\min \quad \mathcal{J} = \sum_{s \in \mathcal{S}} \pi_s \cdot \text{NetOperatingCost}_s + \lambda_{\text{risk}} \cdot \text{CVaR}_{0.95}(\text{NetOperatingCost})
$$

### 5.1 Scenario Net Operating Cost
$$
\text{NetOperatingCost}_s = \sum_{c,t} \Big( c_{c,t}^{\text{discom}} P_{c,t,s}^{\text{discom}} + c_{t,s}^{\text{iex}} P_{c,t,s}^{\text{iex}} + c_{\text{deg}} P_{c,t,s}^{\text{bess\_dis}} + \text{IncentiveCost}_{c,t,s} - \text{RetailRevenue}_{c,t} \Big)
$$
Where:
- $\text{RetailRevenue}_{c,t} = T_{c,t} \times \left( P_{c,t,s}^{\text{fc\_served}} \times 1000 + N_{c,t,s}^{\text{swap\_req}} \times E^{\text{pack\_kwh}} \right)$
- $\text{IncentiveCost}_{c,t,s} = \sum_h \text{incentive\_rate}_h \times E_{h,t,s}^{\text{shifted}} \times 1000$

### 5.2 Rockafellar-Uryasev CVaR Representation
$$
\text{CVaR}_{0.95} = \eta + \frac{1}{1 - 0.95} \sum_{s \in \mathcal{S}} \pi_s \cdot u_s
$$
Subject to linear auxiliary inequalities:
$$
u_s \ge \text{NetOperatingCost}_s - \eta \quad (\forall s \in \mathcal{S})
$$
$$
u_s \ge 0 \quad (\forall s \in \mathcal{S})
$$
$$
\eta \in \mathbb{R} \quad (\text{Free Value-at-Risk threshold variable})
$$
This exact reformulation preserves the complete linearity of the program, enabling HiGHS 1.16.0 to solve to certified global optimality.
