# VOLT Assumptions Register

**Document Version:** 1.0  
**Phase:** Phase 1 Project Foundation  
**Classification Rule:** Every parameter in this register is classified as **`ASSUMED`**. Source-provided case facts are tracked separately in `case_study.yaml` with provenance **`OBSERVED`**.

This document lists every unknown parameter, the engineering rationale for its baseline selection, and the sensitivity bounds to be evaluated during simulation in later phases.

---

## 1. Case Facts vs. Modelling Assumptions Matrix

| Case Fact (OBSERVED) | Unknown Parameter in Fact | Implementation Assumption (ASSUMED) | Rationale |
|---|---|---|---|
| Five metro clusters (Delhi NCR, Mumbai MMR, Bengaluru, Hyderabad, Chennai) | Individual city capacity split | Equal 20% (240 MW) per cluster baseline | Case provides only total 1,200 MW; equal distribution is an editable starting point. |
| 1,200 MW total installed capacity | Substation grid import limits per city | 240 MW per cluster import limit | Interconnection caps cannot exceed installed facility capacity without upstream expansion. |
| 60% DC fast charge / 40% swap station mix | Number and rating of physical dispensers per hub | 120 kW - 240 kW DC dispensers; 2.5 kW swap slots | Typical commercial fast-charger ratings in Indian urban hubs. |
| 600 MWh combined storage capacity | Split between stationary BESS and swap-pack inventory | 300 MWh stationary BESS / 300 MWh swap packs (50/50 split) | The case does not specify the asset split; 50/50 is transparent and subjected to sensitivity testing. |
| 35% renewable energy sourcing reference | Hourly solar/wind availability profile | Diurnal solar curve + evening wind availability | 35% is a portfolio energy volume share, not a constant 35% power supply every hour. |
| 5% emergency reserve | Reserve asset allocation (BESS vs swap packs) | 5% applied to both stationary BESS and ready swap packs | Ensures priority emergency fleet guarantees across both fast-charging and swap modalities. |
| Dynamic tariff ±20% bound | Price elasticity of charging customers | Synthetic discrete willingness tiers (Rebate: 1.5-2.5 INR/kWh) | Customer elasticity cannot be fabricated without driver transaction logs. |
| 78% reliability baseline; 89.7% target | Swap-to-energy conversion formula | Usable pack nominal energy delivered per swap | A completed swap delivers 2.25 kWh usable energy; later recharging is a separate demand event. |
| 10% losses baseline; 8% target | Loss distribution by component | Chargers: 4%, BESS RT: 7%, Swap packs: 5%, Distribution: 2% | Engineering breakdown ensuring reconciled meter boundaries. |
| >12% per-cluster EBITDA target | Fixed overhead and corporate lease expenses | Illustrative operating margin proxy (Revenue - Opex) | Corporate overhead is unavailable; decision metric focuses on site operating margin. |

---

## 2. Detailed Parameter Register

### 2.1 Cluster Capacity Allocation
- **Case Status:** Unknown. Case specifies 1,200 MW system total across 5 cities.
- **Assumed Base Value:** 240.0 MW per cluster (20.0% share).
- **Unit:** `MW` / `fraction`.
- **Provenance:** `ASSUMED`.
- **Rationale:** Equal distribution serves as a neutral baseline. Configurable in `configs/assumptions.yaml`.
- **Sensitivity Range:**
  * Low: 15.0% (180.0 MW)
  * Base: 20.0% (240.0 MW)
  * High: 30.0% (360.0 MW)

### 2.2 Storage Asset Split (600 MWh)
- **Case Status:** Unknown. Case specifies combined 600 MWh storage.
- **Assumed Base Value:**
  * Stationary BESS: 300.0 MWh (50.0%)
  * Battery Swap Packs: 300.0 MWh (50.0%)
- **Unit:** `MWh` / `fraction`.
- **Provenance:** `ASSUMED`.
- **Rationale:** 50/50 split provides substantial stationary energy for peak shaving while provisioning adequate packs for 2W/3W commercial logistics fleets.
- **Sensitivity Range:**
  * Low Stationary BESS Share: 25.0% (150.0 MWh BESS / 450.0 MWh Swap Packs)
  * Base: 50.0% (300.0 MWh BESS / 300.0 MWh Swap Packs)
  * High Stationary BESS Share: 75.0% (450.0 MWh BESS / 150.0 MWh Swap Packs)

### 2.3 Stationary BESS Power Rating & Efficiencies
- **Case Status:** Unknown. MWh storage capacity does not determine MW power capability.
- **Assumed Base Value:**
  * C-rate: 0.50 C (150.0 MW charge/discharge capacity across 300 MWh BESS)
  * Charge Efficiency ($\eta_{ch}$): 0.93 (93.0%)
  * Discharge Efficiency ($\eta_{dis}$): 0.93 (93.0%)
  * Round-Trip Efficiency: $\sim 86.5\%$
  * Safe SOC Range: 0.10 to 0.90 (10% to 90%)
  * Modeled Degradation Cost: 1,250.0 INR/MWh-throughput
- **Unit:** `1/h`, `MW`, `fraction`, `INR/MWh`.
- **Provenance:** `ASSUMED`.
- **Rationale:** 2-hour duration (0.5C) BESS is industry standard for grid-connected utility storage. Efficiencies align with commercial LFP battery installations.
- **Sensitivity Range:**
  * C-rate: [0.25 C, 0.50 C, 1.00 C]
  * Round-Trip Efficiency: [82.0%, 86.5%, 91.0%]
  * Degradation Cost: [800.0, 1250.0, 2000.0] INR/MWh

### 2.4 Swappable Pack Specifications
- **Case Status:** Unknown. Case specifies swapping modality but no pack chemistry or capacity.
- **Assumed Base Value:**
  * Pack Nominal Capacity: 2.50 kWh
  * Total Active Pack Inventory: 120,000 packs ($300\text{ MWh} / 2.5\text{ kWh}$)
  * Slot Charging Power: 2.50 kW (1C standard charging)
  * Charging Efficiency: 0.90 (90.0%)
  * Minimum Dispense SOC: 0.90 (90.0%)
  * SOH Retirement Threshold: 0.75 (75.0%)
- **Unit:** `kWh`, `packs`, `kW`, `fraction`.
- **Provenance:** `ASSUMED`.
- **Rationale:** Based on prevailing Indian commercial 2W/3W swappable battery specifications (AIS-156 standard compliant).
- **Sensitivity Range:**
  * Pack Capacity: [2.0, 2.5, 3.5] kWh
  * Inventory Count: [80,000, 120,000, 150,000] packs

### 2.5 Grid Procurement Tariffs & Market Clearing
- **Case Status:** Unknown commercial agreements.
- **Assumed Base Value:**
  * DISCOM Commercial EV Tariff: 7.50 INR/kWh (7,500 INR/MWh)
  * Open-Access Renewable PPA: 3.80 INR/kWh (3,800 INR/MWh)
  * IEX Day-Ahead Market Baseline Average: 5.20 INR/kWh (5,200 INR/MWh)
  * Retail Fast-Charging Reference Tariff: 11.50 INR/kWh
  * Retail Swap Base Service Fee: 85.00 INR/swap
- **Unit:** `INR/kWh`, `INR/MWh`, `INR/swap`.
- **Provenance:** `ASSUMED`.
- **Rationale:** Reflects recent open-access solar/wind tariffs in India (CERC/SERC orders) and average Day-Ahead Market clearing bands on IEX.
- **Sensitivity Range:**
  * DISCOM Tariff: [6.50, 7.50, 9.00] INR/kWh
  * Renewable PPA: [3.20, 3.80, 4.50] INR/kWh
  * IEX Peak Price: [5.20, 10.00, 18.00] INR/kWh (under stress spike scenario)

### 2.6 Customer Demand Flexibility & Opt-In Response
- **Case Status:** Unknown customer elasticity.
- **Assumed Base Value:**
  * Fleet Opt-In Fraction: 0.30 (30.0%)
  * Max Feasible Window Shift: 2.0 hours
  * Incentive Tier 1 (1-hour delay): 1.50 INR/kWh rebate
  * Incentive Tier 2 (2-hour delay): 2.50 INR/kWh rebate
- **Unit:** `fraction`, `hour`, `INR/kWh`.
- **Provenance:** `ASSUMED`.
- **Rationale:** Fleets operating overnight or with schedule slack are assumed receptive to rebates below peak procurement spreads.
- **Sensitivity Range:**
  * Opt-In Share: [0.15, 0.30, 0.50]
  * Max Delay: [1.0, 2.0, 3.0] hours

### 2.7 Inter-Cluster Physical Coupling
- **Case Status:** Clarified in technical specification.
- **Assumed Value:** Physical inter-city power transmission is **STRICTLY DISABLED**.
- **Unit:** boolean (`false`).
- **Provenance:** `ASSUMED`.
- **Rationale:** Clusters are geographically separated by hundreds of kilometers across state borders with distinct DISCOMs and regional grid interconnections. Power wheeling cannot be physically commanded by the local operator.

### 2.8 Reconstructed BAU Baseline Calibration Parameters
- **Case Status:** Operational heuristics not provided by operator.
- **Provenance:** `SYNTHETIC_CALIBRATION`.
- **Target References:** 78.0% Service Reliability, 10.0% Energy Losses.
- **Calibrated Values:**
  * `station_availability_factor`: 0.80 (Allowed bounds: [0.72, 0.88])
  * `charger_efficiency`: 0.935 (Allowed bounds: [0.90, 0.95])
  * `swap_charge_efficiency`: 0.900 (Allowed bounds: [0.86, 0.93])
  * `auxiliary_load_pct`: 0.020 (Allowed bounds: [0.015, 0.040])
  * `distribution_loss_pct`: 0.012 (Allowed bounds: [0.010, 0.025])
- **Calibration Residuals:**
  * Measured Reliability: 78.40% (Residual: +0.40%)
  * Measured Losses: 10.18% (Residual: +0.18%)
  * Total Objective Error: 0.58%
- **Rationale:** Calibrated via bounded parameter optimization to reconstruct incumbent performance without post-hoc forcing or metric overriding.

---

### 2.9 Non-Identifiability & Storage Reserve Accounting (Remediation A2 & A4)
- **Parameter Non-Identifiability:**
  * Five physical parameters (`station_availability_factor`, `charger_efficiency`, `swap_charge_efficiency`, `auxiliary_load_pct`, `distribution_loss_pct`) were fitted against two aggregate scalar targets (78.0% reliability, 10.0% losses).
  * This is an underdetermined system with non-unique parameter identifiability; the calibrated set represents a plausible reference-matching configuration within engineering bounds (`SYNTHETIC_CALIBRATION`), not measured empirical hardware truth.
- **Combined Storage & Reserve Allocation:**
  * Combined Storage (`OBSERVED`): 600.0 MWh network-wide.
  * Asset Split (`ASSUMED`): 50/50 baseline &rarr; 300.0 MWh stationary BESS + 300.0 MWh swap pack inventory.
  * 5% Reserve Obligation (`OBSERVED` rule applied to `ASSUMED` split): 15.0 MWh BESS reserve + 15.0 MWh swap inventory reserve network-wide (30.0 MWh combined).
  * Per-Cluster Allocation (5 equal clusters): 3.0 MWh BESS reserve + 3.0 MWh swap reserve per cluster = 6.0 MWh total reserve per cluster.
  * Invariant: Sum across 5 clusters identically equals 15.0 MWh BESS and 15.0 MWh swap inventory (30.0 MWh combined network reserve).

---

### 2.10 Phase 3 Probabilistic Forecasting & Quantile Uncertainty
- **Canonical Operational Vectors (`OBSERVED` scope):**
  1. `fast_charge_demand_mwh` (MWh/h, cluster-level)
  2. `swap_demand_mwh` (MWh/h, cluster-level)
  3. `solar_available_mwh` (MWh/h, cluster-level)
  4. `wind_available_mwh` (MWh/h, cluster-level)
  5. `iex_clearing_price_inr_mwh` (INR/MWh, national market)
- **Model Family (`SYNTHETIC` implementation):** Tree-based quantile gradient boosting via scikit-learn `HistGradientBoostingRegressor(loss='quantile')` with P10, P50, and P90 quantiles.
- **Chronological Data Split:**
  * Train: 2021-01-01 to 2023-12-31 (3 years)
  * Validation: 2024-01-01 to 2024-12-31 (1 year, leap year calendar)
  * Test: 2025-01-01 to 2025-12-31 (1 year, untouched test period)
- **Operational NWP Weather Forecast Error Proxy (`ASSUMED`):** Day-ahead weather forecast uncertainty modeled as zero-mean Gaussian perturbation whose variance scales with lead time $h \in [1, 24]$.
- **Quantile Post-Processing (`ASSUMED` guardrails):** Monotonic sorting enforcing $P10 \le P50 \le P90$; physical clipping to $\ge 0.0$; solar nighttime cutoff strictly set to $0.0\text{ MWh}$ for hours 19:00 to 05:00 IST.

---

### 2.11 Phase 4 Customer Flexibility, Acceptance & Dynamic Tariffs

#### Customer Segments & Behavioral Opt-In Parameters (`ASSUMED`)
| Segment | Base Share | Sensitivity (Low/Base/High) | Priority Rank | Opt-In Rate | Max Wait (min) | Max Deferral (min) | Shiftable? | Rationale |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `EMERGENCY` | 3.0% | 2.0% / 3.0% / 5.0% | 1 | 0.0% | 0 | 0 | **No** | Ambulances, law enforcement; non-deferrable |
| `PRIORITY_FLEET` | 12.0% | 8.0% / 12.0% / 15.0% | 2 | 0.0% | 15 | 0 | **No** | Critical transit fleets; protected by 5% reserve |
| `RIDE_HAILING` | 35.0% | 30.0% / 35.0% / 40.0% | 3 | 35.0% | 30 | 60 | **Yes** | Commercial 4W/3W drivers during lull periods |
| `LOGISTICS_FLEET`| 30.0% | 25.0% / 30.0% / 40.0% | 4 | 60.0% | 90 | 180 | **Yes** | Last-mile and depot logistics with scheduling slack |
| `PRIVATE_EV` | 20.0% | 15.0% / 20.0% / 25.0% | 5 | 25.0% | 45 | 90 | **Yes** | Commuters responding to price incentives |

#### Logistic Acceptance Model (`ASSUMED`)
- Formula: $p_{\text{accept}} = \text{clip}\left(\sigma(\beta_0 + \beta_1 \cdot \text{incentive} + \beta_2 \cdot \text{notice} + \beta_3 \cdot \text{slack} + \gamma_{\text{segment}}), 0.0, 1.0\right)$
- Intercept $\beta_0$: Base -1.50 (Sensitivity: Low -2.00, High -1.00)
- Price Elasticity $\beta_1$: Base 0.80 (Sensitivity: Low 0.40, High 1.50) per INR/kWh
- Advance Notice $\beta_2$: Base 0.30 (Sensitivity: Low 0.10, High 0.50) per advance hour
- Schedule Slack $\beta_3$: Base 0.40 (Sensitivity: Low 0.20, High 0.60) per buffer hour
- Segment Utility Effects $\gamma$: `EMERGENCY`: -999.0, `PRIORITY_FLEET`: -999.0, `RIDE_HAILING`: 0.00, `LOGISTICS_FLEET`: +0.50, `PRIVATE_EV`: -0.20

#### Dynamic Tariff Policy Bounding Rule (`REGULATORY_GUARDRAIL_ASSUMED`)
- Floor Multiplier: $0.80 \times \bar{T}_{\text{prev}}$ (20% discount ceiling)
- Ceiling Multiplier: $1.20 \times \bar{T}_{\text{prev}}$ (20% premium ceiling)
- Final Tariff: $\text{final\_tariff} = \text{clip}(\text{raw\_tariff}, 0.80 \times \bar{T}_{\text{prev}}, 1.20 \times \bar{T}_{\text{prev}})$
- Baseline Reference Tariff: ₹11.50/kWh (Fast Charging), ₹85.00/swap (Battery Swap)

#### Decoupled Financial Accounting Invariant (`ASSUMED_POLICY`)
- Customer retail tariff revenue ($E_{\text{delivered}} \times T_{\text{final}}$) and voluntary flexibility incentive expenditures ($E_{\text{deferred}} \times I_{\text{rate}}$) are distinct accounting lines.
- Incentives are never subtracted from retail tariffs into a single blended rate.
- If operational wholesale cost inputs are missing, incentive offers return `NOT_EVALUABLE` rather than fabricating positive net value.


---

### 2.12 Phase 5 Mathematical Optimization (MILP), CVaR & Invariants

#### Stationary BESS Technical & Operating Bounds (`ASSUMED`)
- **Installed Capacity:** 60.0 MWh per cluster (300.0 MWh total across 5 clusters).
- **Power Rating:** 30.0 MW continuous charge / 30.0 MW continuous discharge (0.5 C-rate).
- **Efficiency:** AC-to-DC charge $\eta = 0.93$; DC-to-AC discharge $\eta = 0.93$ (roundtrip $\approx 86.5\%$).
- **Mandatory Emergency Reserve Floor:** $\ge 3.0\text{ MWh}$ ($60.0\text{ MWh} \times 0.05$) preserved every hour.
- **Maximum Operational SOC Ceiling:** $\le 54.0\text{ MWh}$ ($60.0\text{ MWh} \times 0.90$) to preserve battery cycle life.
- **Degradation Wear Cost Proxy:** ₹1,250.00 per MWh of throughput discharged.

#### Battery Swapping Hub Technical & Inventory Bounds (`ASSUMED`)
- **Total Pack Inventory:** 24,000 packs per cluster (120,000 packs across 5 clusters).
- **Usable Pack Energy:** 2.25 kWh delivered per swap; 2.50 kWh nominal rating.
- **Swap Bay Charger Power:** 96.0 MW aggregate bay rating per cluster (2.5 kW / slot).
- **Swap Bay Recharge Efficiency:** $\eta = 0.90$.
- **Mandatory Ready Reserve Floor:** $\ge 1,200\text{ packs}$ ($24,000 \times 0.05$) ready packs with $\text{SOC} \ge 90\%$.

#### Grid Interconnection & Power Capacity Headroom (`REGULATORY_GUARDRAIL_ASSUMED`)
- **Substation Grid Import Limit:** 240.0 MW per cluster.
- **Mandatory Headroom Reserve:** $\ge 12.0\text{ MW}$ ($240.0\text{ MW} \times 0.05$) capacity headroom preserved every hour.
- **Maximum Permissible Import:** $P^{\text{discom}} + P^{\text{iex}} \le 228.0\text{ MW}$.
- **IEX Day-Ahead Procurement Eligibility Cap:** $\le 60.0\text{ MW}$ (25% of 240 MW grid limit).

#### Discrete Dynamic Tariffs & Non-Anticipativity (`REGULATORY_GUARDRAIL_ASSUMED`)
- **Discrete Multipliers:** $m_k \in \{0.80, 0.90, 1.00, 1.10, 1.20\}$.
- **First-Stage Decision:** Binary selection $u_{c,t,k} \in \{0, 1\}$ is scenario-independent, guaranteeing non-anticipativity across all disturbance scenarios.

#### Conditional Value-at-Risk (CVaR) Tail-Risk Parameters (`ASSUMED`)
- **Confidence Percentile $\alpha$:** 0.95 (evaluates the worst 5% loss tail).
- **Risk Aversion Weight $\lambda_{\text{risk}}$:** 0.20 (balanced risk-return trade-off).
- **Formulation:** Linear Rockafellar-Uryasev auxiliary variable representation ($\eta, u_s$).

---

### 2.13 Phase 6 Digital Twin, Closed-Loop Rolling MPC & Shock Disturbances

#### Receding Horizon Architecture (`ASSUMED_POLICY`)
- **MPC Control Step:** Exactly 1 hour ($t=0$ action executed; digital twin stepped forward by 1 hour).
- **Receding Prediction Horizon:** 24 hours ($H=24$) re-optimized every hour.
- **Dynamic Boundary Conditions:** Initial state $S_0$ for stationary BESS and swappable packs at interval $t$ dynamically equals the observed physical state of the digital twin at $t$.
- **Forecast Non-Anticipativity:** Forecasts $\hat{W}(\tau \mid t)$ generated from origin $t$ do not access future actual realizations. Contingencies with `ZERO_AHEAD` visibility remain at baseline expectation until active.

#### Inter-City Isolation (`ASSUMED_REGULATORY`)
- **Zero Inter-City Electricity Wheeling:** Power transfer between metro clusters is strictly $0.0\text{ MW}$. Energy balances are fully localized to each municipal cluster.
- **Battery Pack Transport:** Disabled by default ($\Delta N_{\text{transport}} = 0$).

#### EBITDA Evaluation Invariant (`ACCOUNTING_INVARIANT`)
- Corporate EBITDA cannot be evaluated solely from station operating dispatch ledgers.
- If corporate overhead, real estate leases, SG&A, debt service, and depreciation schedules are missing, EBITDA margin returns `NOT_EVALUABLE`.
- Net Operating Contribution ($₹\text{Retail Revenue} - ₹\text{Procurement} - ₹\text{Degradation} - ₹\text{Incentives}$) is reported separately.

#### Crisis Disturbance Engine (`SYNTHETIC_SHOCKS`)
- Configured via `config/scenarios.yaml`.
- Includes 10 reproducible scenarios: `NORMAL_OPERATION`, `EVENING_DEMAND_SURGE`, `SOLAR_CLOUD_DROP`, `WIND_LULL`, `IEX_PRICE_SPIKE`, `GRID_IMPORT_RESTRICTION`, `SWAP_INVENTORY_SHORTAGE`, `HEATWAVE_COMPOUND`, `COMBINED_MULTI_CITY_CRISIS`, `RECOVERY_AFTER_CRISIS`.

