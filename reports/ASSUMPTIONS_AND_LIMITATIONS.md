# VOLT: Assumptions Register & Operational Limitations

## 1. Governance & Provenance Taxonomy

Every parameter, input dataset, constraint, and output ledger in the VOLT platform carries an immutable provenance classification tag:

| Classification | Meaning & Scope | Examples in VOLT |
| :--- | :--- | :--- |
| **`OBSERVED`** | Facts directly specified in the case study brief or regulatory grid standards. | 5 Metro hubs (Delhi, Mumbai, Bengaluru, Hyderabad, Chennai); 1,200 MW grid capacity; 600 MWh storage; ₹7.50/kWh DISCOM tariff; ₹3.80/kWh Solar/Wind PPA; 0.80x–1.20x dynamic tariff bounds. |
| **`ASSUMED`** | System engineering parameters adopted where exact physical specs were unspecified. | 50/50 storage split (300 MWh BESS / 300 MWh swap packs); 2.5 kWh pack nominal size (2.25 kWh usable); 1C pack charging rate (2.5 kW); ₹2,500/MWh BESS cell degradation wear rate; 2.5 MW auxiliary baseload. |
| **`SYNTHETIC`** | Generated stochastic time-series and scenario shocks. | Chronological weather time series (GHI, wind speed); 15-minute IEX DAM clearing prices; EV customer arrival Poisson streams; 10 disturbance shock scenarios. |
| **`SYNTHETIC_CALIBRATION`** | Reconstructed baseline parameters tuned to match case benchmarks. | 82.0% station availability factor and 4.0% queue balking rate tuned to achieve 78.4% reliability and 10.18% losses on the historical benchmark. |

---

## 2. Core Operational Assumptions

### 2.1 Spatial Isolation & Transmission Invariant
- **Assumption:** Zero inter-city electricity wheeling ($\Delta P_{c_1 \to c_2} \equiv 0.0\text{ MW}$).
- **Justification:** Intra-state DISCOM transmission networks in India charge open-access wheeling and cross-subsidy surcharges (ranging from ₹1.20 to ₹2.80/kWh) and inter-regional transmission losses across regional grids (NR/WR/SR) make real-time physical power wheeling between metro cities economically prohibitive for EV charging.
- **Enforcement:** Enforced as a hard constraint in all MILP formulations and validated by digital twin state invariants.

### 2.2 Storage Architecture Split (600 MWh Network Capacity)
- **Assumption:** Combined storage is split equally: 300 MWh stationary BESS (60 MWh/cluster) and 300 MWh swappable battery packs (120,000 packs network-wide, 24,000 packs/cluster).
- **Justification:** Stationary BESS provides instantaneous 0.5C power ramping (30 MW/cluster) for feeder peak-shaving and frequency support, while swappable packs provide 2W/3W commercial logistics turnaround.
- **Sensitivity:** Tested under 60/40 (stationary heavy) and 40/60 (swap heavy) allocations.

### 2.3 Reserve Margins
- **BESS Emergency Reserve:** Minimum 5% state-of-charge ($SOC_c(t) \ge 3.0\text{ MWh}$ per cluster, $\ge 15.0\text{ MWh}$ network-wide) held in reserve for emergency medical/police vehicle charging.
- **Swap Ready Reserve:** Minimum 5% ready pack inventory ($N_{\text{ready}, c}(t) \ge 1,200\text{ packs}$ per cluster, $\ge 6,000\text{ packs}$ network-wide) held uncommitted for emergency swap requests.
- **Substation Headroom:** Minimum 5% feeder capacity reserve ($P_{\text{headroom}, c}(t) \ge 12.0\text{ MW}$ per cluster, $\ge 60.0\text{ MW}$ network-wide) held below the 240 MW feeder rating to prevent thermal tripping.

### 2.4 Battery Degradation & Cell Lifecycle
- **Assumption:** Stationary BESS cycling wear is amortised at ₹2,500/MWh throughput.
- **Sensitivity:** Tested at ₹1,500/MWh (aggressive cycling) and ₹4,000/MWh (conservative cycling).

---

## 3. Physical & Commercial Limitations

### 3.1 Decision-Support Prototype Scope
- **Non-Live Infrastructure:** VOLT is an advanced mathematical optimization and digital twin simulation prototype designed for operations planning and control evaluation.
- **No Direct SCADA Link:** The prototype does not send binding analog dispatch commands to physical utility substations or battery BMS controllers.
- **No Binding IEX Bids:** Market prices are cleared against historical and synthetic clearing curves; the system does not submit binding financial bids to the Indian Energy Exchange.

### 3.2 Statutory Financial Boundary & EBITDA Non-Evaluability
- **Disclosure:** Corporate EBITDA is disclosed as **`NOT_EVALUABLE`** in accordance with Ind AS and GAAP accounting standards.
- **Reasoning:** The software models direct operational revenues, wholesale energy procurement costs, customer incentives, and cell degradation wear. A true corporate EBITDA requires:
  1. Corporate headquarters SG&A, software maintenance, and managerial payroll.
  2. Long-term land concession leases across 5 metro substations.
  3. Straight-line/WDV depreciation schedules for power electronics, transformers, and civil works.
  4. Capital debt financing, interest rates, and loan amortisation.
  5. State-specific corporate income tax, surcharges, and GST input credits.
- Claiming an EBITDA margin without these audited cost ledgers would be misleading.

### 3.3 Customer Demand & Elasticity Modeling
- Customer response to dynamic tariffs and flexibility incentives is modeled via calibrated logistic acceptance functions ($P(\text{accept}) = \frac{1}{1 + e^{-(\beta_0 + \beta_1 \cdot \text{Incentive})}}$).
- In real-world rollouts, customer elasticity varies by fleet operator commercial contract terms and weather conditions.
