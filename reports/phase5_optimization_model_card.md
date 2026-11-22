# Model Card: VOLT Multi-City Risk-Aware MILP Optimization Engine

## Model Details
- **Model Name:** VOLT Rolling Multi-City Energy, Battery & Customer-Service Dispatch Optimizer
- **Model Version:** 5.0.0
- **Model Type:** Mixed-Integer Linear Program (MILP) with Rockafellar-Uryasev Conditional Value-at-Risk (CVaR)
- **Framework:** Pyomo 6.11.0 / HiGHS 1.16.0 (`appsi_highs`)
- **Primary Use Case:** Optimal co-optimization of grid electricity procurement, wholesale market bidding, on-site solar/wind utilization, stationary BESS (300 MWh), battery swap pipelines (120,000 packs across 5 cities), discrete dynamic tariffs, and voluntary customer flexibility incentives over 24-hour rolling horizons.
- **Auditor / Release Date:** 2026-11-23

---

## Intended Use & Scope
- **Intended Users:** Energy trading desk, virtual power plant (VPP) operators, network dispatchers, and commercial fleet managers.
- **Operating Horizon:** 24 hours at 1-hour resolution.
- **Target Geographies:** 5 metro clusters: Delhi NCR, Mumbai MMR, Bengaluru, Hyderabad, Chennai.
- **Out-of-Scope:**
  - Real-time frequency regulation (< 1 minute).
  - Inter-city physical wheeling (strictly prohibited by non-contiguous distribution jurisdictions).
  - Closed-loop rolling feedback MPC with live hardware actuation (reserved for Phase 6).
  - Black-box Reinforcement Learning (rejected for certified regulatory safety).

---

## Formulation & Decision Hierarchy

| Decision Domain | Physical Asset | Decision Variables | Bounds & Constraints |
| :--- | :--- | :--- | :--- |
| **Grid Procurement** | DISCOM Interconnection | $P_{c,t,s}^{\text{discom}} \ge 0$ | $P^{\text{discom}} + P^{\text{iex}} \le 240\text{ MW} - 12\text{ MW}$ reserve |
| **Market Purchase** | IEX Day-Ahead Market | $P_{c,t,s}^{\text{iex}} \ge 0$ | Eligibility cap $\le 60.0\text{ MW}$ (25% grid limit) |
| **Clean Generation** | On-site Solar & Wind | $P_{c,t,s}^{\text{ren\_used}}, P_{c,t,s}^{\text{ren\_curt}}$ | $P^{\text{used}} + P^{\text{curt}} = P^{\text{available}}$ |
| **Stationary BESS** | 60 MWh / Cluster BESS | $P_{c,t,s}^{\text{bess\_ch}}, P_{c,t,s}^{\text{bess\_dis}}$ | $P \le 30\text{ MW}$; $\text{SOC} \in [3.0, 54.0]\text{ MWh}$ |
| **Swapping Pipeline**| 24,000 Packs / Cluster | $N_{c,t,s}^{\text{start\_ch}}, N_{c,t,s}^{\text{ready}}$ | Ready $\ge 1,200\text{ packs}$; Power $\le 96\text{ MW}$ |
| **Dynamic Pricing** | Retail Customer Tariff | $u_{c,t,k} \in \{0, 1\}$ | Multiplier $m_k \in \{0.80, 0.90, 1.00, 1.10, 1.20\}$ |
| **Customer Flexibility**| Fast Charge Cohorts | $E_{h,t',s}^{\text{fc\_sched}} \ge 0$ | Sum delivered = Total requested by deadline |
| **Tail-Risk Hedging** | CVaR rockafellar-Uryasev| $\eta \in \mathbb{R}, u_s \ge 0$ | $u_s \ge \text{Cost}_s - \eta$ at confidence $\alpha = 0.95$ |

---

## Physical & Regulatory Invariants

1. **Zero Inter-City Wheeling Invariant:** Intra-cluster nodal balance is enforced strictly per cluster. No variables or terms exist linking power flows across different cities.
2. **5% Stationary BESS Emergency Reserve:** SOC is constrained to $E_{c,t,s}^{\text{bess}} \ge 3.0\text{ MWh}$ ($60\text{ MWh} \times 0.05$) at all times.
3. **5% Battery Swap Ready Reserve:** Inventory is constrained to $N_{c,t,s}^{\text{ready}} \ge 1,200\text{ packs}$ ($24,000 \times 0.05$) at all times.
4. **5% Grid Power Capacity Headroom:** Combined DISCOM and IEX import is constrained to $\le 228.0\text{ MW}$ ($240\text{ MW} - 12.0\text{ MW}$), guaranteeing minimum 12.0 MW reserved capacity headroom.
5. **Zero Priority Deadline Violations:** Emergency (3% share) and priority fleet (12% share) sessions are served immediately with zero permitted shifting slack.
6. **Dynamic Tariff Non-Anticipativity:** Tariff variables $u_{c,t,k}$ are first-stage decisions, preventing unrealistic future scenario anticipation in retail rate posting.
7. **Financial Decoupling:** Retail tariff revenue is booked to tariff revenue accounts; flexibility incentive payments are booked to flexibility expense accounts. No netting is permitted inside the optimization accounting ledger.

---

## Solver Performance & Benchmarks

- **Solver:** HiGHS 1.16.0 (`appsi_highs`)
- **Deterministic Problem Dimensions:** 112,870 variables, 11,360 constraints.
- **Deterministic Solve Time:** **7.36 seconds** to relative MIP gap $< 0.01\%$.
- **4-Scenario Stochastic Problem Dimensions:** 451,480 variables, 45,440 constraints.
- **Stochastic CVaR Solve Time:** **31.52 seconds** to relative MIP gap $< 0.01\%$.
- **Fallback Heuristic:** Rule-based greedy dispatch executes in **< 0.02 seconds** if solver times out or becomes unavailable, with transparent `FALLBACK_HEURISTIC` status reporting.

---

## Ethical & Epistemic Disclosures
- **Synthetic Data:** Customer request vectors, solar/wind availability, and IEX market price realizations are synthetic models based on historical Indian power sector distributions.
- **Assumed Parameters:** Battery degradation costs (₹1,250/MWh), charger efficiencies (93% BESS, 90% swap bays), and logistic acceptance slopes are engineering assumptions documented in the VOLT Assumptions Register.
- **Operational Reality:** This model produces decision-support schedules under rolling MPC assumptions and is not a direct SCADA grid control or binding market bidding gateway.
