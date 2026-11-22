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
| `block_minutes` | `INTEGER` | minute | OBSERVED | Granularity: 15-minute raw IEX block or 60-minute aggregated |
| `price_inr_mwh` | `NUMERIC(10,2)` | INR/MWh | OBSERVED / SYNTHETIC | Market clearing price per MWh |
| `cleared_volume_mw` | `NUMERIC(10,2)` | MW | OBSERVED / SYNTHETIC | Aggregate cleared trade volume |
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
