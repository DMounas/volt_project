# VOLT Data Dictionary

**Document Version:** 1.0  
**Status:** Phase 1 Baseline Specification  
**Units Convention:** Power in `MW`, Energy in `MWh` / `kWh`, Tariffs in `INR/kWh` / `INR/MWh`, Fractions in `[0.0, 1.0]`.

This document specifies the primary logical entities and relational schemas for the VOLT energy orchestration platform and digital-twin simulator.

---

## 1. Network & Infrastructure Entities

### 1.1 `cluster`
Represents an independent regional operational grid node. Inter-city power wheeling is disabled by default.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `cluster_id` | `VARCHAR(32)` (PK) | — | OBSERVED | Unique slug (e.g., `delhi_ncr`, `mumbai_mmr`, `bengaluru`, `hyderabad`, `chennai`) |
| `name` | `VARCHAR(64)` | — | OBSERVED | Metro cluster display name |
| `timezone` | `VARCHAR(32)` | — | OBSERVED | Operational timezone (`Asia/Kolkata`) |
| `installed_power_mw` | `NUMERIC(10,2)` | MW | ASSUMED | Allocated installed capacity (unsupplied in case facts; baseline 240 MW) |
| `fast_charge_share` | `NUMERIC(5,4)` | fraction | OBSERVED | Modality fraction for DC fast charging (0.60) |
| `swap_share` | `NUMERIC(5,4)` | fraction | OBSERVED | Modality fraction for battery swap stations (0.40) |
| `grid_import_limit_mw` | `NUMERIC(10,2)` | MW | ASSUMED | Maximum instantaneous grid import capacity |
| `created_at` | `TIMESTAMPTZ` | — | SYNTHETIC | Record creation timestamp |

### 1.2 `station`
Physical hub within a cluster housing DC fast-chargers, swap bays, or both.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `station_id` | `VARCHAR(32)` (PK) | — | SYNTHETIC | Unique station identifier |
| `cluster_id` | `VARCHAR(32)` (FK) | — | OBSERVED | Parent cluster reference |
| `station_type` | `VARCHAR(32)` | — | SYNTHETIC | `FAST_CHARGING`, `SWAP_STATION`, or `HYBRID` |
| `charger_count` | `INTEGER` | count | SYNTHETIC | Number of physical charging dispensers/slots |
| `charger_power_mw` | `NUMERIC(8,3)` | MW | SYNTHETIC | Aggregate rated charging power at station |
| `swap_compatibility_groups` | `TEXT[]` | — | ASSUMED | Supported pack form factors/protocols |
| `latitude` / `longitude` | `NUMERIC(9,6)` | degrees | SYNTHETIC | Geolocation coordinates (optional for Phase 1) |

---

## 2. Market & Procurement Entities

### 2.1 `market_price`
Electricity wholesale clearing prices from the Indian Energy Exchange (IEX).

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `market_record_id` | `BIGSERIAL` (PK) | — | — | Internal record ID |
| `timestamp` | `TIMESTAMPTZ` | — | OBSERVED / SYNTHETIC | Delivery interval start time |
| `market` | `VARCHAR(16)` | — | OBSERVED | Market segment: `DAM` (Day-Ahead) or `RTM` (Real-Time) |
| `time_block` | `INTEGER` | 1..96 | OBSERVED | Settlement time block index within trading day |
| `price_inr_mwh` | `NUMERIC(10,2)` | INR/MWh | OBSERVED / SYNTHETIC | Market clearing price per MWh |
| `cleared_volume_mw` | `NUMERIC(10,2)` | MW | OBSERVED / SYNTHETIC | Scheduled active power trade volume over 15-min interval |
| `cleared_energy_mwh` | `NUMERIC(10,3)` | MWh | OBSERVED / SYNTHETIC | Cleared electrical energy = `cleared_volume_mw * 0.25 h` |
| `source` | `VARCHAR(64)` | — | OBSERVED / SYNTHETIC | Data source citation or generator seed |

### 2.2 `procurement_contract`
Commercial terms for bilateral open-access renewable contracts and DISCOM supplies.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `contract_id` | `VARCHAR(32)` (PK) | — | ASSUMED | Contract identifier |
| `cluster_id` | `VARCHAR(32)` (FK) | — | OBSERVED | Associated cluster |
| `source_type` | `VARCHAR(32)` | — | OBSERVED | `SOLAR_PPA`, `WIND_PPA`, or `DISCOM_TARIFF` |
| `max_mw` | `NUMERIC(10,2)` | MW | ASSUMED | Contracted capacity cap |
| `price_inr_mwh` | `NUMERIC(10,2)` | INR/MWh | ASSUMED | Contracted energy purchase price |
| `take_or_pay` | `BOOLEAN` | — | ASSUMED | True if minimum off-take obligation applies |
| `curtailment_penalty` | `NUMERIC(10,2)` | INR/MWh | ASSUMED | Penalty for voluntary curtailment (if any) |

---

## 3. Storage & Battery Entities

### 3.1 `bess_asset`
Stationary Battery Energy Storage System (BESS) installed at clusters.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `asset_id` | `VARCHAR(32)` (PK) | — | ASSUMED | BESS asset identifier |
| `cluster_id` | `VARCHAR(32)` (FK) | — | OBSERVED | Cluster location |
| `capacity_mwh` | `NUMERIC(10,2)` | MWh | ASSUMED | Rated usable energy storage capacity |
| `max_charge_mw` | `NUMERIC(8,2)` | MW | ASSUMED | Maximum charging power rating (independent of MWh) |
| `max_discharge_mw` | `NUMERIC(8,2)` | MW | ASSUMED | Maximum discharge power rating |
| `eta_charge` | `NUMERIC(5,4)` | fraction | ASSUMED | Charging efficiency (e.g., 0.93) |
| `eta_discharge` | `NUMERIC(5,4)` | fraction | ASSUMED | Discharging efficiency (e.g., 0.93) |
| `soc_min` / `soc_max` | `NUMERIC(5,4)` | fraction | ASSUMED | Operational SOC safety bounds (e.g., 0.10 to 0.90) |
| `initial_soc` | `NUMERIC(5,4)` | fraction | ASSUMED | Initial state of charge for simulation |
| `degradation_cost_inr_per_mwh` | `NUMERIC(10,2)` | INR/MWh | ASSUMED | Modeled wear cost per throughput MWh |

### 3.2 `battery_pack`
Individual swappable battery pack passport and tracking record.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `pack_id` | `VARCHAR(32)` (PK) | — | SYNTHETIC | Individual pack tracking identifier |
| `cluster_id` | `VARCHAR(32)` (FK) | — | OBSERVED | Current station / cluster location |
| `compatibility_group` | `VARCHAR(32)` | — | ASSUMED | Vehicle interface standard (e.g., `COMMERCIAL_2W_STD`) |
| `nominal_capacity_kwh` | `NUMERIC(6,2)` | kWh | ASSUMED | Nominal pack capacity (e.g., 2.5 kWh) |
| `soc` | `NUMERIC(5,4)` | fraction | SYNTHETIC | Current state of charge |
| `soh` | `NUMERIC(5,4)` | fraction | SYNTHETIC | State of health (retained capacity fraction) |
| `cycle_count` | `INTEGER` | cycles | SYNTHETIC | Cumulative equivalent full cycles |
| `status` | `VARCHAR(24)` | — | SYNTHETIC | `READY`, `CHARGING`, `DEPLETED`, `MAINTENANCE`, `RESERVE` |
| `charging_power_kw` | `NUMERIC(6,2)` | kW | ASSUMED | Active charging rate |

---

## 4. Demand, Flexibility & Customer Entities

### 4.1 `customer_request`
Discrete fast-charging or battery swap request submitted by an EV user or fleet.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `request_id` | `VARCHAR(32)` (PK) | — | SYNTHETIC | Unique request identifier |
| `cluster_id` | `VARCHAR(32)` (FK) | — | OBSERVED | Requested location cluster |
| `service_type` | `VARCHAR(16)` | — | OBSERVED | `FAST_CHARGE` or `BATTERY_SWAP` |
| `arrival_time` | `TIMESTAMPTZ` | — | SYNTHETIC | Customer arrival timestamp |
| `deadline` | `TIMESTAMPTZ` | — | SYNTHETIC | Requested departure deadline |
| `energy_required_mwh` | `NUMERIC(8,4)` | MWh | SYNTHETIC | Target delivered energy volume |
| `pack_type` | `VARCHAR(32)` | — | ASSUMED | Required compatible pack type (for swaps) |
| `priority` | `VARCHAR(16)` | — | SYNTHETIC | `CRITICAL`, `URGENT`, `DEADLINE_FLEET`, `FLEXIBLE` |
| `max_wait_hours` | `NUMERIC(4,2)` | hour | SYNTHETIC | Maximum acceptable wait before balking |
| `flexible_flag` | `BOOLEAN` | — | SYNTHETIC | Customer willingness to shift charging window |

### 4.2 `tariff`
Dynamic tariff schedule recommended by orchestrator.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `tariff_id` | `BIGSERIAL` (PK) | — | — | Record identifier |
| `cluster_id` | `VARCHAR(32)` (FK) | — | OBSERVED | Target cluster |
| `service_type` | `VARCHAR(16)` | — | OBSERVED | `FAST_CHARGE` or `BATTERY_SWAP` |
| `effective_date` | `DATE` | — | SYNTHETIC | Effective operating day |
| `hour_of_day` | `INTEGER` | hour | SYNTHETIC | Operating interval [0..23] |
| `previous_day_avg_inr_kwh` | `NUMERIC(8,2)` | INR/kWh | OBSERVED / SYNTHETIC | Baseline benchmark price |
| `min_price_inr_kwh` | `NUMERIC(8,2)` | INR/kWh | OBSERVED | Lower bound (0.80 × previous-day avg) |
| `max_price_inr_kwh` | `NUMERIC(8,2)` | INR/kWh | OBSERVED | Upper bound (1.20 × previous-day avg) |
| `recommended_price` | `NUMERIC(8,2)` | INR/kWh | SYNTHETIC | Orchestrated tariff recommendation |

---

## 5. Decision & KPI Entities

### 5.1 `decision`
Audit trail of operational recommendations generated by the optimizer.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `decision_id` | `BIGSERIAL` (PK) | — | — | Record identifier |
| `run_id` | `VARCHAR(64)` | — | SYNTHETIC | Associated optimization execution run |
| `cluster_id` | `VARCHAR(32)` (FK) | — | OBSERVED | Target cluster |
| `timestamp` | `TIMESTAMPTZ` | — | SYNTHETIC | Action interval start time |
| `decision_type` | `VARCHAR(32)` | — | SYNTHETIC | `BESS_CHARGE`, `BESS_DISCHARGE`, `IEX_PROCURE`, `DISCOM_PROCURE`, `TARIFF_REBATE` |
| `quantity` | `NUMERIC(10,3)` | specified | SYNTHETIC | Recommended quantity |
| `unit` | `VARCHAR(16)` | — | SYNTHETIC | `MW`, `MWh`, `INR/kWh`, `packs` |
| `reason_code` | `VARCHAR(64)` | — | SYNTHETIC | Explainability reason code |
| `binding_constraint` | `VARCHAR(64)` | — | SYNTHETIC | Active constraint limiting objective |

### 5.2 `kpi_result`
Evaluation results comparing baseline and optimized policies.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `kpi_result_id` | `BIGSERIAL` (PK) | — | — | Record identifier |
| `run_id` | `VARCHAR(64)` | — | SYNTHETIC | Associated run |
| `cluster_id` | `VARCHAR(32)` | — | OBSERVED | Cluster or `CONSOLIDATED` |
| `kpi_name` | `VARCHAR(64)` | — | OBSERVED | `SERVICE_RELIABILITY`, `ENERGY_LOSS_RATIO`, `EBITDA_MARGIN` |
| `value` | `NUMERIC(8,4)` | percent / INR | SYNTHETIC | Realized simulated value |
| `baseline_reference` | `NUMERIC(8,4)` | percent / INR | OBSERVED | Case baseline reference (e.g., 78.0%, 10.0%) |
| `target_value` | `NUMERIC(8,4)` | percent / INR | OBSERVED | Case business target (e.g., 89.7%, 8.0%, >12.0%) |

---

## 6. Energy Reconciliation & Manifest Entities (Phase 2)

### 6.1 `energy_balance_record`
Auditable meter-boundary reconciliation for each cluster and hourly simulation step.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `timestamp` | `TIMESTAMPTZ` | — | SYNTHETIC | Simulation interval start time |
| `cluster_id` | `VARCHAR(32)` | — | OBSERVED | Target regional cluster |
| `renewable_used_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | Solar/wind energy consumed directly by station loads |
| `discom_import_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | Baseload import from utility DISCOM grid |
| `iex_import_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | Day-ahead / real-time merchant energy import |
| `bess_discharge_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | Energy discharged from stationary BESS into switchgear |
| `total_supply_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | Total supply: `renewable_used + discom + iex + bess_discharge` |
| `fast_charge_input_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | AC electrical energy drawn by DC fast chargers |
| `swap_pack_charge_input_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | Electrical energy drawn by battery swap charging bays |
| `bess_charge_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | Electrical energy drawn to charge stationary BESS |
| `auxiliary_load_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | Station HVAC, lighting, telemetry, and control loads |
| `distribution_loss_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | Substation transformer and bus distribution losses |
| `total_demand_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | Total electrical demand across all loads and losses |
| `fast_charge_delivered_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | Metered DC energy delivered to EV batteries |
| `swap_energy_equivalent_delivered_mwh` | `NUMERIC(10,4)` | MWh | SYNTHETIC | Usable energy (2.25 kWh/pack) issued to swapping customers |
| `residual_abs_mwh` | `NUMERIC(10,5)` | MWh | SYNTHETIC | Absolute conservation residual: `\|total_supply - total_demand\|` |
| `is_reconciled` | `BOOLEAN` | — | SYNTHETIC | True if `residual_abs_mwh <= 0.005 MWh` |

---

## 7. Probabilistic Forecasting Entities (Phase 3)

### 7.1 `forecast_trajectory_point`
Point and quantile interval forecasts for rolling 24-hour horizon windows ($h \in [1, 24]$).

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `origin_timestamp` | `TIMESTAMPTZ` | — | SYNTHETIC | Timestamp at which forecast is generated (information boundary) |
| `horizon_hour` | `INTEGER` | 1..24 | — | Lead time ahead in hours |
| `target_timestamp` | `TIMESTAMPTZ` | — | SYNTHETIC | Future target delivery time = `origin_timestamp + horizon_hour` |
| `cluster_id` | `VARCHAR(32)` | — | OBSERVED | Cluster identifier or `national` for market prices |
| `target_name` | `VARCHAR(64)` | — | OBSERVED | Canonical vector: `fast_charge_demand_mwh`, `swap_demand_mwh`, `solar_available_mwh`, `wind_available_mwh`, `iex_clearing_price_inr_mwh` |
| `p10` | `NUMERIC(10,3)` | specified | SYNTHETIC | 10th percentile lower quantile estimate ($\ge 0$) |
| `p50` | `NUMERIC(10,3)` | specified | SYNTHETIC | 50th percentile median central forecast ($\ge p10$) |
| `p90` | `NUMERIC(10,3)` | specified | SYNTHETIC | 90th percentile upper quantile estimate ($\ge p50$) |
| `model_family` | `VARCHAR(64)` | — | SYNTHETIC | Model architecture: `HistGradientBoostingRegressor` |

### 7.2 `weather_covariates`
Time-aligned physical atmospheric predictors in `cluster_hourly`.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `ambient_temp_c` | `NUMERIC(5,1)` | °C | SYNTHETIC | Surface dry-bulb temperature |
| `relative_humidity_pct` | `NUMERIC(5,1)` | % | SYNTHETIC | Relative atmospheric humidity [15.0, 98.0] |
| `cloud_cover_pct` | `NUMERIC(5,1)` | % | SYNTHETIC | Total fractional cloud attenuation [5.0, 100.0] |
| `precipitation_mm` | `NUMERIC(6,1)` | mm | SYNTHETIC | Hourly accumulated rainfall |
| `solar_irradiance_w_m2` | `NUMERIC(7,1)` | W/m² | SYNTHETIC | Global horizontal irradiance proxy (strictly 0 at night) |
| `wind_speed_m_s` | `NUMERIC(5,2)` | m/s | SYNTHETIC | 10m hub-height wind speed [0.5, 22.0] |

---

## 8. Customer Flexibility & Dynamic Tariff Entities (Phase 4)

### 8.1 `customer_service_request`
Individual customer EV fast-charging sessions and battery swapping requests disaggregated from aggregate load.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `request_id` | `VARCHAR(32)` (PK) | — | SYNTHETIC | Unique synthetic request ID (no personal identifying info) |
| `cluster_id` | `VARCHAR(32)` (FK) | — | OBSERVED | Metro cluster identifier |
| `request_type` | `VARCHAR(16)` | — | OBSERVED | Physical service modality: `FAST_CHARGE` or `BATTERY_SWAP` |
| `customer_segment` | `VARCHAR(32)` | — | ASSUMED | `EMERGENCY`, `PRIORITY_FLEET`, `RIDE_HAILING`, `LOGISTICS_FLEET`, `PRIVATE_EV` |
| `arrival_ts` | `TIMESTAMPTZ` | — | SYNTHETIC | Customer arrival timestamp (Asia/Kolkata) |
| `departure_deadline_ts` | `TIMESTAMPTZ` | — | SYNTHETIC | Customer promised-ready departure deadline ($T_{\text{deadline}} \ge T_{\text{arrival}}$) |
| `requested_energy_kwh` | `NUMERIC(8,3)` | kWh | SYNTHETIC | Fast charging energy requirement (> 0) |
| `minimum_service_energy_kwh` | `NUMERIC(8,3)` | kWh | SYNTHETIC | Minimum acceptable energy for trip continuation |
| `requested_pack_count` | `INTEGER` | count | SYNTHETIC | Discrete integer pack count requested (battery swap) |
| `minimum_pack_count` | `INTEGER` | count | SYNTHETIC | Minimum discrete integer packs required |
| `pack_capacity_kwh` | `NUMERIC(5,2)` | kWh | ASSUMED | Nominal pack capacity (2.25 - 2.50 kWh) |
| `max_wait_minutes` | `NUMERIC(6,1)` | min | ASSUMED | Maximum acceptable queue/wait time |
| `max_deferral_minutes` | `NUMERIC(6,1)` | min | ASSUMED | Maximum deferral slack beyond normal charging duration |
| `flexibility_opt_in` | `BOOLEAN` | — | SYNTHETIC | Explicit opt-in state (never inferred from segment) |
| `service_priority` | `INTEGER` | 1..5 | ASSUMED | Priority tier (1=Emergency, 2=Priority Fleet, 3=Ride, 4=Logistics, 5=Private) |
| `baseline_tariff_inr_per_kwh` | `NUMERIC(8,2)` | INR/kWh | ASSUMED | Base applicable retail energy tariff |
| `previous_day_avg_tariff_inr_per_kwh` | `NUMERIC(8,2)` | INR/kWh | ASSUMED | Reference previous day average tariff for cluster |

### 8.2 `customer_flexibility_envelope`
Deterministic service-feasibility representation delineating non-shiftable demand from voluntary flexible load.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `request_id` | `VARCHAR(32)` (FK) | — | SYNTHETIC | Associated customer request |
| `cluster_id` | `VARCHAR(32)` | — | OBSERVED | Metro cluster identifier |
| `request_type` | `VARCHAR(16)` | — | OBSERVED | `FAST_CHARGE` or `BATTERY_SWAP` |
| `customer_segment` | `VARCHAR(32)` | — | ASSUMED | Customer segment classification |
| `arrival_ts` | `TIMESTAMPTZ` | — | SYNTHETIC | Arrival time |
| `earliest_start_ts` | `TIMESTAMPTZ` | — | SYNTHETIC | Earliest permissible service start time |
| `deadline_ts` | `TIMESTAMPTZ` | — | SYNTHETIC | Departure deadline |
| `requested_energy_kwh` | `NUMERIC(8,3)` | kWh | SYNTHETIC | Total requested energy |
| `minimum_service_energy_kwh` | `NUMERIC(8,3)` | kWh | SYNTHETIC | Minimum non-deferrable component |
| `non_shiftable_energy_kwh` | `NUMERIC(8,3)` | kWh | SYNTHETIC | Energy that must be served immediately |
| `flexible_energy_kwh` | `NUMERIC(8,3)` | kWh | SYNTHETIC | Energy eligible for voluntary deferral |
| `requested_pack_count` | `INTEGER` | count | SYNTHETIC | Requested discrete pack count |
| `non_shiftable_pack_count` | `INTEGER` | count | SYNTHETIC | Non-shiftable integer pack count |
| `flexible_pack_count` | `INTEGER` | count | SYNTHETIC | Eligible flexible integer pack count |
| `eligible_time_slots` | `TEXT[]` | — | SYNTHETIC | Hourly ISO timestamps within service window |
| `max_deferral_minutes` | `NUMERIC(6,1)` | min | ASSUMED | Feasible schedule deferral buffer |
| `is_deferrable` | `BOOLEAN` | — | SYNTHETIC | True if positive flexible energy and opted in |
| `reason_code` | `VARCHAR(64)` | — | SYNTHETIC | Explainable reason code (`EMERGENCY_NON_SHIFTABLE`, `NOT_OPTED_IN`, etc.) |
| `service_risk_score` | `NUMERIC(4,2)` | [0.0, 1.0] | SYNTHETIC | Risk index of proposed shift |

### 8.3 `dynamic_tariff_recommendation`
Dynamic retail energy tariff bounded to $[0.80x, 1.20x]$ previous day average.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `cluster_id` | `VARCHAR(32)` | — | OBSERVED | Cluster identifier |
| `service_type` | `VARCHAR(16)` | — | OBSERVED | Modality |
| `timestamp` | `TIMESTAMPTZ` | — | SYNTHETIC | Recommendation interval timestamp |
| `previous_day_average_tariff_inr_per_kwh` | `NUMERIC(8,2)` | INR/kWh | ASSUMED | Reference benchmark rate |
| `tariff_min_inr_per_kwh` | `NUMERIC(8,2)` | INR/kWh | REGULATORY_GUARDRAIL | Regulatory floor = $0.80 \times \bar{T}_{\text{prev}}$ |
| `tariff_max_inr_per_kwh` | `NUMERIC(8,2)` | INR/kWh | REGULATORY_GUARDRAIL | Regulatory ceiling = $1.20 \times \bar{T}_{\text{prev}}$ |
| `raw_tariff_inr_per_kwh` | `NUMERIC(8,2)` | INR/kWh | ASSUMED_POLICY | Unconstrained wholesale & congestion adjusted tariff |
| `final_tariff_inr_per_kwh` | `NUMERIC(8,2)` | INR/kWh | REGULATORY_GUARDRAIL | Final clipped tariff: $\text{clip}(T_{\text{raw}}, T_{\text{min}}, T_{\text{max}})$ |
| `clamped` | `BOOLEAN` | — | REGULATORY_GUARDRAIL | True if raw tariff was clipped by boundary |
| `clamping_direction` | `VARCHAR(16)` | — | REGULATORY_GUARDRAIL | `LOWER_BOUND`, `UPPER_BOUND`, or `NONE` |
| `adjustment_reasons` | `TEXT[]` | — | ASSUMED_POLICY | Audit trail of price adjustments |

### 8.4 `voluntary_incentive_offer`
Separate financial incentive offer evaluated against operational wholesale procurement benefits.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `offer_id` | `VARCHAR(32)` (PK) | — | SYNTHETIC | Unique incentive offer ID |
| `request_id` | `VARCHAR(32)` (FK) | — | SYNTHETIC | Associated customer request |
| `proposed_shift_kwh` | `NUMERIC(8,3)` | kWh | SYNTHETIC | Proposed flexible energy to defer |
| `proposed_shift_packs` | `INTEGER` | count | SYNTHETIC | Proposed discrete packs to defer |
| `effective_tariff_inr_per_kwh` | `NUMERIC(8,2)` | INR/kWh | REGULATORY_GUARDRAIL | Retail customer billing rate |
| `incentive_amount_inr` | `NUMERIC(8,2)` | INR | ASSUMED_POLICY | Decoupled cash/credit incentive paid to customer |
| `expected_acceptance_probability` | `NUMERIC(5,4)` | [0.0, 1.0] | ASSUMED | Logistic acceptance model probability |
| `expected_accepted_energy_kwh` | `NUMERIC(8,3)` | kWh | ASSUMED | Mathematical expectation $p \times E_{\text{flex}}$ |
| `estimated_incentive_cost_inr` | `NUMERIC(8,2)` | INR | ASSUMED_POLICY | Expected operational incentive expenditure |
| `estimated_operational_benefit_inr` | `NUMERIC(8,2)` | INR | ASSUMED_POLICY | Avoided peak wholesale procurement benefit |
| `net_expected_value_inr` | `NUMERIC(8,2)` | INR | ASSUMED_POLICY | Operational benefit minus incentive cost |
| `evaluable` | `BOOLEAN` | — | ASSUMED_POLICY | False if required cost inputs missing (`NOT_EVALUABLE`) |
| `status` | `VARCHAR(32)` | — | ASSUMED_POLICY | `RECOMMENDED`, `NOT_EVALUABLE`, `INSUFFICIENT_BENEFIT` |


---

## 9. Phase 5 Optimization Entities

### 9.1 `hourly_cluster_decision`
Granular physical dispatch variables and state trajectories for one cluster and one hour.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `cluster_id` | `VARCHAR(32)` | — | OBSERVED | Metro cluster identifier |
| `hour` | `INTEGER` | 0..23 | — | Hour index within the 24-hour horizon |
| `discom_mw` | `NUMERIC(8,3)` | MW | SYNTHETIC | Optimal procurement from regional DISCOM |
| `iex_mw` | `NUMERIC(8,3)` | MW | SYNTHETIC | Optimal purchase from IEX Day-Ahead Market |
| `renewable_used_mwh` | `NUMERIC(8,3)` | MWh | SYNTHETIC | On-site clean solar/wind generation utilized |
| `renewable_curtailed_mwh` | `NUMERIC(8,3)` | MWh | SYNTHETIC | Clean solar/wind curtailed |
| `bess_charge_mw` | `NUMERIC(8,3)` | MW | SYNTHETIC | Stationary BESS AC-to-DC charging power |
| `bess_discharge_mw` | `NUMERIC(8,3)` | MW | SYNTHETIC | Stationary BESS DC-to-AC discharging power |
| `bess_soc_mwh` | `NUMERIC(8,3)` | MWh | SYNTHETIC | Stationary BESS state of charge at end of hour |
| `bess_reserve_compliant` | `BOOLEAN` | — | SYNTHETIC | True if SOC $\ge 3.0\text{ MWh}$ mandatory reserve |
| `swap_packs_served` | `INTEGER` | count | SYNTHETIC | Swaps delivered to commercial customers |
| `swap_packs_charging` | `INTEGER` | count | SYNTHETIC | Packs undergoing charging in bay infrastructure |
| `swap_packs_ready` | `INTEGER` | count | SYNTHETIC | Packs ready with $\text{SOC} \ge 90\%$ |
| `swap_packs_depleted` | `INTEGER` | count | SYNTHETIC | Depleted packs queued for recharge |
| `swap_charge_power_mw` | `NUMERIC(8,3)` | MW | SYNTHETIC | Total electrical power consumed by swap charging bays |
| `swap_reserve_compliant`| `BOOLEAN` | — | SYNTHETIC | True if ready packs $\ge 1,200$ mandatory reserve |
| `fc_demand_requested_mwh`| `NUMERIC(8,3)`| MWh | SYNTHETIC | Aggregate fast charging energy requested |
| `fc_demand_served_mwh` | `NUMERIC(8,3)` | MWh | SYNTHETIC | Fast charging energy delivered |
| `fc_demand_shifted_mwh`| `NUMERIC(8,3)` | MWh | SYNTHETIC | Voluntary flexible energy deferred to/from this hour |
| `selected_tariff_tier` | `VARCHAR(16)` | — | REGULATORY | Selected discrete dynamic tariff tier ($0.80x$ to $1.20x$) |
| `tariff_inr_per_kwh` | `NUMERIC(8,2)` | INR/kWh | REGULATORY | Effective customer retail tariff |
| `tariff_revenue_inr` | `NUMERIC(12,2)`| INR | SYNTHETIC | Retail energy sales revenue |
| `incentive_spend_inr` | `NUMERIC(12,2)`| INR | SYNTHETIC | Customer flexibility incentive expenditures |
| `losses_mwh` | `NUMERIC(8,3)` | MWh | SYNTHETIC | Physical system energy losses |
| `power_headroom_mw` | `NUMERIC(8,3)` | MW | SYNTHETIC | Preserved substation import headroom |
| `power_headroom_compliant`| `BOOLEAN` | — | SYNTHETIC | True if headroom $\ge 12.0\text{ MW}$ mandatory reserve |
| `binding_constraints` | `TEXT[]` | — | SYNTHETIC | List of active binding physical/regulatory constraints |

### 9.2 `optimization_kpis`
Consolidated 24-hour performance indicators across all 5 metro clusters.

| Field | Type | Unit | Provenance | Description |
|---|---|---|---|---|
| `service_reliability_pct` | `NUMERIC(6,2)` | % | SYNTHETIC | Total energy delivered / total energy requested |
| `energy_loss_pct` | `NUMERIC(6,2)` | % | SYNTHETIC | Total system losses / total throughput |
| `renewable_share_pct` | `NUMERIC(6,2)` | % | SYNTHETIC | Clean renewable utilized / total procurement |
| `power_capacity_headroom_mw` | `NUMERIC(8,2)` | MW | SYNTHETIC | Minimum power headroom preserved |
| `deadline_violations_count` | `INTEGER` | count | SYNTHETIC | Delayed priority sessions (invariant: 0) |
| `total_procurement_cost_inr`| `NUMERIC(14,2)`| INR | SYNTHETIC | Total DISCOM + IEX electricity procurement expense |
| `total_retail_revenue_inr` | `NUMERIC(14,2)`| INR | SYNTHETIC | Total customer energy tariff billing revenue |
| `total_flexibility_incentive_inr`| `NUMERIC(14,2)`| INR | SYNTHETIC | Total flexibility incentive spend |
| `total_degradation_cost_inr`| `NUMERIC(14,2)`| INR | SYNTHETIC | Battery wear replacement proxy cost |
| `net_operating_cost_inr` | `NUMERIC(14,2)`| INR | SYNTHETIC | Net cost = Procurement + Deg + Incentives - Revenue |
| `cvar_tail_risk_cost_inr` | `NUMERIC(14,2)`| INR | SYNTHETIC | 95% tail-risk cost under adverse market spikes |
| `ebitda_operating_margin_pct`| `NUMERIC(6,2)` | % | SYNTHETIC | Site operating margin proxy |
