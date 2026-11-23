# VOLT: 8-Slide Pitch Deck Specification

## Slide 1: Title & The Megawatt EV Revolution
- **Headline:** VOLT — Virtual Orchestration of Load, Tariffs & Energy
- **Sub-headline:** Closed-Loop Rolling MPC for Megawatt-Scale EV Charging & Swapping Hubs
- **Key Facts:**
  - 5 Indian Megacities: Delhi NCR, Mumbai MMR, Bengaluru, Hyderabad, Chennai.
  - 1,200 MW Grid Feeder Capacity • 600 MWh Storage (300 MWh BESS + 120,000 Swappable Packs).
  - Target: Transition uncoordinated operations into a resilient, profitable, green grid orchestrator.

---

## Slide 2: The Industrial Bottleneck
- **Headline:** Why Conventional EV Infrastructure Fails Under Stress
- **Visuals / Metrics:**
  - **78.4% Reliability:** Stations crippled by transformer overloads, maintenance downtime, and driver queue balking.
  - **10.18% System Losses:** Unmanaged battery charging and high transformer conversion inefficiencies.
  - **Severe IEX Market Spikes:** Evening vehicle charging peaks collide with statutory ₹10,000/MWh merchant electricity price spikes.
- **Takeaway:** Static threshold rules and unmanaged charging lead to utility penalties and financial insolvency.

---

## Slide 3: The VOLT Solution Architecture
- **Headline:** End-to-End Stochastic Orchestration Architecture
- **Three Pillar Framework:**
  1. *Multi-Vector Quantile Forecasting:* Probabilistic P10/P50/P90 models for load, solar, wind, and market prices.
  2. *Customer Flexibility Framework:* Voluntary charging windows within 0.80x–1.20x tariff bounds; priority protection for emergency vehicles.
  3. *Risk-Aware Pyomo MILP + CVaR:* Co-optimizing power procurement, BESS dispatch, and pack replenishment under tail-risk market conditions ($\alpha = 0.95$).

---

## Slide 4: Real-Time Closed-Loop Rolling MPC
- **Headline:** From Static Day-Ahead Plans to Adaptive Receding-Horizon Control
- **Execution Flow:**
  - Solves 24-hour horizon at every interval $t$.
  - Applies **strictly the first hour action ($t=0$)** to the digital twin.
  - Ingests realized weather/demand actuals and updates state transitions.
  - Shifts customer cohorts and re-optimizes at $t+1$.
- **Resilience Invariant:** Deterministic fallback scheduler triggers automatically on solver timeout, guaranteeing reserve margins without system crashes.

---

## 5. Slide 5: Empirical Benchmark & Verified Uplift
- **Headline:** Proven Superiority Across 5 Metros & Fixed Seeds
- **Core Numbers (Heatwave Compound Shock):**
  - **Procurement Cost:** ₹27.98L (BAU) $\to$ ₹15.74L (Open-Loop MILP) $\to$ **₹14.33L (Closed-Loop MPC)** $\implies$ **-48.8% Cost Savings**.
  - **Service Reliability:** 78.4% (BAU) $\to$ **99.6% (Closed-Loop MPC)**.
  - **System Losses:** 10.18% $\to$ **7.64%**.
  - **Renewable Utilization:** 50.0% $\to$ **89.1%**.

---

## Slide 6: Deep Ablations & Sensitivity Insights
- **Headline:** What Drives the Value? Rigorous Feature Ablation
- **Key Findings:**
  - *No Customer Flexibility:* **+59.5% Cost Penalty** (Flexibility is essential to shave evening DISCOM peaks).
  - *Static Open-Loop vs MPC:* Static plans suffer a **+6.5% penalty** under compound shocks; closed-loop feedback captures real-time arbitrage.
  - *Theoretical Oracle Bound:* Captures over **94% of theoretical perfect-foresight ceiling**.

---

## Slide 7: Honest Engineering & Regulatory Invariants
- **Headline:** Production-Grade Governance & Honest Accounting
- **Invariants Strictly Held (100% across all runs):**
  - Zero inter-city electricity wheeling ($\Delta P \equiv 0.0$ MW).
  - 5% BESS emergency reserve ($\ge 3.0$ MWh/cluster) & 5% swap ready reserve ($\ge 1,200$ packs).
  - Integer pack conservation strictly held ($\equiv 24,000$ packs/cluster).
  - Substation headroom reserve maintained ($\ge 12.0$ MW).
- **Statutory EBITDA Disclosure:** Formally marked **`NOT_EVALUABLE`** due to unsupplied corporate SG&A, land leases, and depreciation schedules (Ind AS / GAAP compliance).

---

## Slide 8: Deployment Roadmap & Operational Value
- **Headline:** Phased Commercial Deployment Roadmap
- **Roadmap:**
  - *Phase 1 (Day-Ahead Advisory):* Shadow scheduling alongside existing DISCOM SCADA.
  - *Phase 2 (Automated Swapping Control):* Closed-loop automated charging bay scheduling for 2W/3W batteries.
  - *Phase 3 (Full Dynamic Tariff Gateway):* Direct integration with fleet operator telematics and IEX bidding gateways.
- **Closing Proposition:** VOLT delivers 48% energy procurement savings, near-zero unserved demand, and rock-solid grid stability for India's electrified transport future.
