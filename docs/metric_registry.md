# VOLT Metric Definition Registry & Comparison Semantics

## 1. Audited Policy Semantics

The VOLT platform evaluates five distinct operational policies and benchmarks. Every report, endpoint, and dashboard card must use these explicit terms without conflation:

| Identifier | Category | Executable? | Description & Calibration Baseline |
| :--- | :--- | :---: | :--- |
| `HISTORICAL_REFERENCE` | Case Study Target | No (Static) | Reference KPIs stated in the problem brief: **78.0% Reliability** and **10.0% Losses**. Provided as an external target, not a runnable controller. |
| `CALIBRATED_BAU` | Reconstructed Incumbent | Yes (Simulation) | Reconstructed incumbent uncoordinated policy calibrated in Phase 2. Incorporates **82.0% station availability downtime**, **4.0% customer queue balking**, merit-order dispatch without BESS peak-shaving, fixed tariffs, and zero customer flex incentives. Achieves **78.4% reliability** and **10.18% losses** on calibration benchmarks. |
| `FALLBACK_HEURISTIC` | Emergency Safety Policy | Yes (Rule-based) | Deterministic rule-based safety scheduler invoked if the mathematical solver times out, is unavailable, or proves infeasible. Preserves 5% BESS and pack reserves and prioritizes emergency fleets. Serves 100% on benign days if capacity allows; **must never be labeled as optimal or conflated with historical BAU**. |
| `OPEN_LOOP_MILP` | Static Optimization Plan | Yes (MILP) | Deterministic 24-hour mixed-integer linear programming schedule solved once at $t=0$ using Day-Ahead P50 forecasts. Executes as an open-loop dispatch without real-time state feedback or shock re-optimization. |
| `CLOSED_LOOP_MPC` | Receding-Horizon Controller | Yes (MPC) | Full closed-loop rolling horizon Model Predictive Control. Solves a 24-hour horizon at each interval $t$, **applies ONLY the $t=0$ action (1 hour)**, advances the digital twin with realized physical shocks, and re-optimizes at $t+1$. |

---

## 2. Canonical KPI Metric Registry

All metrics are calculated at verified physical meter boundaries.

### 2.1 Service Reliability & Fulfilment

#### `energy_service_reliability_pct` (%)
- **Definition:** Total energy delivered to electric vehicle batteries divided by total energy requested by drivers during operational hours.
- **Formula:**
  $$\text{Reliability} = 100.0 \times \frac{\sum_{t=1}^{T} E_{\text{delivered}}(t)}{\sum_{t=1}^{T} E_{\text{requested}}(t)}$$
- **Boundary:** Customer vehicle connector / charger dispenser output boundary.
- **Target:** $\ge 89.7\%$ (Phase 1–2 target: $89.7\%$).

#### `fast_charge_fill_rate_pct` (%)
- **Definition:** Delivered DC fast-charging energy divided by requested fast-charging energy.
- **Formula:**
  $$\text{FC Fill Rate} = 100.0 \times \frac{\sum_{t=1}^{T} E_{\text{FC, delivered}}(t)}{\sum_{t=1}^{T} E_{\text{FC, requested}}(t)}$$
- **Boundary:** DC Fast Charger Dispenser Output.

#### `swap_pack_fill_rate_pct` (%)
- **Definition:** Number of fully charged swappable battery packs dispensed divided by total battery pack swap requests.
- **Formula:**
  $$\text{Swap Fill Rate} = 100.0 \times \frac{\sum_{t=1}^{T} N_{\text{packs, dispensed}}(t)}{\sum_{t=1}^{T} N_{\text{packs, requested}}(t)}$$
- **Boundary:** Battery Swapping Station automated dispensing bay.
- **Accounting Invariant:** Strictly measured in **integer packs** ($N \in \mathbb{Z}_{\ge 0}$); never mixed with continuous energy (MWh).

---

### 2.2 Electrical System Efficiency & Losses

#### `energy_loss_ratio_pct` (%)
- **Definition:** Total electrical energy lost across transformation, inversion, battery chemical conversion, and distribution divided by gross energy entering the network.
- **Formula:**
  $$\text{Loss Ratio} = 100.0 \times \frac{L_{\text{substation}} + L_{\text{BESS}} + L_{\text{swap\_chargers}} + L_{\text{distribution}}}{E_{\text{grid\_import}} + E_{\text{solar}} + E_{\text{wind}}}$$
- **Substation Transformer Loss:** $1.2\%$ of feeder power flow.
- **BESS Conversion Loss:** $\approx 13.5\%$ round-trip loss ($93\%$ charge efficiency, $93\%$ discharge efficiency).
- **Swap Charger Loss:** $11.0\%$ pack charging loss ($89\%$ charging efficiency).
- **Local Distribution Loss:** $1.5\%$ across medium-voltage internal feeder cables.
- **Target:** $\le 8.0\%$.

#### `renewable_share_pct` (%)
- **Definition:** Direct solar/wind energy plus green energy stored in BESS supplied to EV loads divided by total energy served.
- **Formula:**
  $$\text{Renewable Share} = 100.0 \times \frac{\sum_{t=1}^{T} E_{\text{renewable, dispatched}}(t)}{\sum_{t=1}^{T} E_{\text{served}}(t)}$$
- **Curtailed Energy:** Tracked separately as $E_{\text{renewable, available}} - E_{\text{renewable, dispatched}}$.

---

### 2.3 Financial & Economic Ledgers

All ledgers maintain strict financial decoupling:

| Ledger Name | Unit | Formula / Basis | Boundary |
| :--- | :---: | :--- | :--- |
| **Wholesale Energy Procurement Cost** | INR | $\sum (P_{\text{DISCOM}} \times \text{Tariff}_{\text{DISCOM}} + P_{\text{IEX}} \times \text{Price}_{\text{IEX}} + P_{\text{Ren}} \times \text{PPA}_{\text{Ren}})$ | Utility & IEX settlement meters |
| **Retail Charging Revenue** | INR | $\sum (E_{\text{FC}} \times \text{Tariff}_{\text{Dynamic}} + N_{\text{Swap}} \times \text{Fee}_{\text{Swap}})$ | Customer billing gateways |
| **Flexibility Incentives Paid** | INR | $\sum (E_{\text{shifted}} \times \text{Rate}_{\text{Incentive}})$ | Customer flex ledger |
| **Gross Procurement Margin** | INR | $\text{Retail Revenue} - \text{Procurement Cost} - \text{Incentives Paid}$ | Consolidated gross margin |
| **Battery Degradation Expense** | INR | $\sum (\text{Throughput}_{\text{BESS}}) \times ₹2,500/\text{MWh}$ | Battery cell lifecycle ledger |
| **Variable O&M Expense** | INR | Station auxiliary cooling and consumable wear | Station physical boundary |
| **Net Operating Contribution** | INR | $\text{Gross Margin} - \text{Degradation} - \text{Variable O&M}$ | Segment contribution |
| **EBITDA Margin** | Status | **`NOT_EVALUABLE`** | Corporate statutory boundary |

---

### 2.4 EBITDA Disclosure & Missing Cost Bridge

The VOLT software prototype simulates physical scheduling, wholesale market trading, and customer demand coordination. In accordance with Ind AS / GAAP accounting standards, **EBITDA is disclosed as `NOT_EVALUABLE`** due to the absence of:

1. **Corporate Overhead & SG&A:** Central management, legal, regulatory, and software infrastructure salaries.
2. **Site Land Leases:** Long-term land lease and concession agreements for 5 metro hubs across 1,200 MW of substations.
3. **Depreciation Schedules:** Straight-Line vs WDV depreciation methods and asset lifespans for transformers, inverters, and switchgear.
4. **Financing & Debt Servicing:** Interest rates, loan tenures, and capital structure for initial hardware capex.
5. **Tax Boundaries:** Corporate income tax brackets, state surcharge rates, and GST input tax credit reconciliations.

Any claim of an achieved corporate EBITDA margin without these audited cost items would constitute a fraudulent accounting projection.
