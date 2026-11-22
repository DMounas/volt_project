# VOLT API Contracts — Phase 1

**Document Version:** 1.0  
**Base URL:** `http://localhost:8000/api/v1`  
**Data Format:** JSON  
**Specification Owner's Rule:** All responses strictly preserve provenance tags (`OBSERVED`, `ASSUMED`, `SYNTHETIC`) and physical units.

---

## 1. `GET /api/v1/health`

Returns service health status, application version, database connectivity, and runtime environment.

### Request
```http
GET /api/v1/health HTTP/1.1
Host: localhost:8000
Accept: application/json
```

### Response (`200 OK`)
```json
{
  "status": "ok",
  "app_name": "VOLT — Virtual Orchestration of Load, Tariffs & Energy",
  "version": "0.1.0",
  "timestamp": "2026-11-22T16:22:45.123456Z",
  "database": "connected",
  "environment": "development"
}
```

---

## 2. `GET /api/v1/config/case`

Returns source-provided case study facts, capacity shares, KPI benchmarks, operational guardrails, and explicit disclosures of unsupplied parameters.

### Request
```http
GET /api/v1/config/case HTTP/1.1
Host: localhost:8000
Accept: application/json
```

### Response (`200 OK`)
```json
{
  "title": "VOLT Five-City EV Fast-Charging & Battery-Swapping Network",
  "specification_version": "v1.0",
  "currency": "INR",
  "clusters": [
    "Delhi NCR",
    "Mumbai MMR",
    "Bengaluru",
    "Hyderabad",
    "Chennai"
  ],
  "cluster_count": 5,
  "cluster_provenance": "OBSERVED",
  "installed_capacity": {
    "value": 1200.0,
    "unit": "MW",
    "provenance": "OBSERVED",
    "description": "Total combined system installed power capacity across all five clusters"
  },
  "capacity_mix": {
    "fast_charging": {
      "share": 0.60,
      "percentage": 60.0,
      "aggregate_capacity_mw": 720.0,
      "unit": "fraction",
      "provenance": "OBSERVED",
      "description": "DC fast-charging hubs share of total installed capacity (720 MW)"
    },
    "battery_swapping": {
      "share": 0.40,
      "percentage": 40.0,
      "aggregate_capacity_mw": 480.0,
      "unit": "fraction",
      "provenance": "OBSERVED",
      "description": "Battery-swap stations share of total installed capacity (480 MW)"
    }
  },
  "storage_capacity": {
    "combined_storage_mwh": 600.0,
    "unit": "MWh",
    "provenance": "OBSERVED",
    "asset_split_known": false,
    "description": "Combined storage capacity across stationary BESS and swap-pack inventory. Asset split is unknown in case facts and must be configured in assumptions."
  },
  "renewable_sourcing_reference": {
    "value": 0.35,
    "percentage": 35.0,
    "unit": "fraction",
    "provenance": "OBSERVED",
    "description": "Portfolio open-access solar and wind sourcing share; not a constant hourly generation constraint"
  },
  "kpi_benchmarks": {
    "service_reliability": {
      "current_reference": 0.78,
      "current_percentage": 78.0,
      "target": 0.897,
      "target_percentage": 89.7,
      "relative_increase_percent": 15.0,
      "unit": "fraction",
      "provenance": "OBSERVED"
    },
    "energy_losses": {
      "current_reference": 0.10,
      "current_percentage": 10.0,
      "target": 0.08,
      "target_percentage": 8.0,
      "relative_reduction_percent": 20.0,
      "unit": "fraction",
      "provenance": "OBSERVED"
    },
    "ebitda_margin": {
      "target": 0.12,
      "target_percentage": 12.0,
      "operator": ">",
      "scope": "per_cluster_and_consolidated",
      "unit": "fraction",
      "provenance": "OBSERVED"
    }
  },
  "operating_guardrails": {
    "emergency_reserve": {
      "value": 0.05,
      "percentage": 5.0,
      "unit": "fraction",
      "scope": "applicable_capacity_and_swap_pack_inventory",
      "constraint_type": "hard_constraint",
      "provenance": "OBSERVED"
    },
    "customer_tariff_bound": {
      "min_multiplier": 0.80,
      "max_multiplier": 1.20,
      "reference_base": "previous_day_average_tariff",
      "provenance": "OBSERVED"
    }
  },
  "historical_data_specification": {
    "duration_years": 5,
    "time_resolution": "1 hour",
    "required_series": [
      "weather",
      "cluster_charging_demand",
      "swap_logs",
      "iex_prices",
      "renewable_generation",
      "battery_soh"
    ],
    "provenance": "OBSERVED"
  },
  "unknown_assumptions": [
    {
      "parameter": "Individual city capacity allocation",
      "case_fact_status": "Unknown in case study (only aggregate 1,200 MW supplied)",
      "assumed_value": "equal_share_baseline",
      "unit": "fraction/MW",
      "provenance": "ASSUMED",
      "rationale": "Equal 20% (240 MW) per cluster baseline is configured in assumptions.yaml for simulation."
    },
    {
      "parameter": "600 MWh storage asset split (BESS vs swap packs)",
      "case_fact_status": "Unknown in case study (only aggregate 600 MWh combined supplied)",
      "assumed_value": "50% BESS (300 MWh) / 50% swap packs (300 MWh)",
      "unit": "fraction/MWh",
      "provenance": "ASSUMED",
      "rationale": "50/50 baseline split configured in assumptions.yaml; subject to sensitivity testing."
    },
    {
      "parameter": "Stationary BESS power rating (MW)",
      "case_fact_status": "Unknown in case study (storage capacity MWh does not determine MW)",
      "assumed_value": "C-rate 0.5C (150 MW)",
      "unit": "MW",
      "provenance": "ASSUMED",
      "rationale": "Assumed 0.5C 2-hour duration rating for stationary BESS."
    }
  ]
}
```

---

## 3. `GET /api/v1/clusters`

Returns the five operational metro clusters with observed identity and assumed baseline capacity parameters.

### Request
```http
GET /api/v1/clusters HTTP/1.1
Host: localhost:8000
Accept: application/json
```

### Response (`200 OK`)
```json
{
  "total_clusters": 5,
  "clusters": [
    {
      "cluster_id": "delhi_ncr",
      "name": "Delhi NCR",
      "provenance": "OBSERVED",
      "installed_capacity_share_assumed": 0.20,
      "installed_capacity_mw_assumed": 240.0,
      "capacity_provenance": "ASSUMED",
      "grid_import_limit_mw_assumed": 240.0,
      "status": "active"
    },
    {
      "cluster_id": "mumbai_mmr",
      "name": "Mumbai MMR",
      "provenance": "OBSERVED",
      "installed_capacity_share_assumed": 0.20,
      "installed_capacity_mw_assumed": 240.0,
      "capacity_provenance": "ASSUMED",
      "grid_import_limit_mw_assumed": 240.0,
      "status": "active"
    },
    {
      "cluster_id": "bengaluru",
      "name": "Bengaluru",
      "provenance": "OBSERVED",
      "installed_capacity_share_assumed": 0.20,
      "installed_capacity_mw_assumed": 240.0,
      "capacity_provenance": "ASSUMED",
      "grid_import_limit_mw_assumed": 240.0,
      "status": "active"
    },
    {
      "cluster_id": "hyderabad",
      "name": "Hyderabad",
      "provenance": "OBSERVED",
      "installed_capacity_share_assumed": 0.20,
      "installed_capacity_mw_assumed": 240.0,
      "capacity_provenance": "ASSUMED",
      "grid_import_limit_mw_assumed": 240.0,
      "status": "active"
    },
    {
      "cluster_id": "chennai",
      "name": "Chennai",
      "provenance": "OBSERVED",
      "installed_capacity_share_assumed": 0.20,
      "installed_capacity_mw_assumed": 240.0,
      "capacity_provenance": "ASSUMED",
      "grid_import_limit_mw_assumed": 240.0,
      "status": "active"
    }
  ],
  "provenance": "OBSERVED",
  "note": "Cluster names are observed case study facts. Individual city capacity splits and grid limits are ASSUMED and configurable."
}
```

---

## 4. `GET /api/v1/scenarios`

Returns configured disturbance scenario metadata for stress-testing and benchmark evaluations.

### Request
```http
GET /api/v1/scenarios HTTP/1.1
Host: localhost:8000
Accept: application/json
```

### Response (`200 OK`)
```json
{
  "total_scenarios": 7,
  "scenarios": [
    {
      "scenario_id": "NORMAL",
      "name": "Normal Operating Conditions",
      "description": "Typical baseline operations with seasonal average demand, nominal renewable generation, and normal IEX price spread.",
      "demand_multiplier": 1.0,
      "renewable_multiplier": 1.0,
      "iex_price_multiplier": 1.0,
      "swap_demand_multiplier": 1.0,
      "initial_pack_ready_fraction": 0.85,
      "initial_bess_soc": 0.50,
      "probability_weight": 0.45,
      "seed": 42,
      "status": "configured",
      "provenance": "SYNTHETIC"
    },
    {
      "scenario_id": "DEMAND_PEAK",
      "name": "Urban Demand Peak",
      "description": "Heatwave or extreme urban mobility peak causing a 35% surge in fast-charging demand across afternoon and evening hours.",
      "demand_multiplier": 1.35,
      "renewable_multiplier": 0.95,
      "iex_price_multiplier": 1.25,
      "swap_demand_multiplier": 1.20,
      "initial_pack_ready_fraction": 0.80,
      "initial_bess_soc": 0.50,
      "probability_weight": 0.15,
      "seed": 101,
      "status": "configured",
      "provenance": "SYNTHETIC"
    },
    {
      "scenario_id": "RENEWABLE_DROP",
      "name": "Renewable Generation Drop",
      "description": "Monsoon cloud cover or wind lull causing a 60% curtailment in open-access solar/wind availability, forcing reliance on grid imports.",
      "demand_multiplier": 1.0,
      "renewable_multiplier": 0.40,
      "iex_price_multiplier": 1.15,
      "swap_demand_multiplier": 1.0,
      "initial_pack_ready_fraction": 0.85,
      "initial_bess_soc": 0.50,
      "probability_weight": 0.15,
      "seed": 202,
      "status": "configured",
      "provenance": "SYNTHETIC"
    },
    {
      "scenario_id": "IEX_PRICE_SPIKE",
      "name": "IEX Merchant Price Spike",
      "description": "Severe transmission congestion and peak merchant tariff spike on IEX Day-Ahead Market exceeding 2.5x normal cleared rates.",
      "demand_multiplier": 1.05,
      "renewable_multiplier": 0.90,
      "iex_price_multiplier": 2.50,
      "swap_demand_multiplier": 1.0,
      "initial_pack_ready_fraction": 0.85,
      "initial_bess_soc": 0.60,
      "probability_weight": 0.10,
      "seed": 303,
      "status": "configured",
      "provenance": "SYNTHETIC"
    },
    {
      "scenario_id": "SWAP_SHORTAGE",
      "name": "Battery Swap Pack Shortage",
      "description": "Commercial delivery fleet shift-change rush leading to acute swap pack exhaustion in dense urban stations.",
      "demand_multiplier": 1.0,
      "renewable_multiplier": 1.0,
      "iex_price_multiplier": 1.0,
      "swap_demand_multiplier": 1.80,
      "initial_pack_ready_fraction": 0.40,
      "initial_bess_soc": 0.50,
      "probability_weight": 0.08,
      "seed": 404,
      "status": "configured",
      "provenance": "SYNTHETIC"
    },
    {
      "scenario_id": "COMBINED_CRISIS",
      "name": "Correlated Multi-Vector Crisis",
      "description": "Concurrent demand surge (+30%), severe renewable collapse (-65%), IEX price surge (2.8x), and reduced initial battery reserve.",
      "demand_multiplier": 1.30,
      "renewable_multiplier": 0.35,
      "iex_price_multiplier": 2.80,
      "swap_demand_multiplier": 1.50,
      "initial_pack_ready_fraction": 0.50,
      "initial_bess_soc": 0.35,
      "probability_weight": 0.04,
      "seed": 505,
      "status": "configured",
      "provenance": "SYNTHETIC"
    },
    {
      "scenario_id": "RECOVERY",
      "name": "Post-Crisis Restoration",
      "description": "Orderly 24-hour recovery horizon restoring stationary BESS state-of-charge and replenishing swap inventory to safety thresholds.",
      "demand_multiplier": 0.90,
      "renewable_multiplier": 1.10,
      "iex_price_multiplier": 0.85,
      "swap_demand_multiplier": 0.95,
      "initial_pack_ready_fraction": 0.45,
      "initial_bess_soc": 0.25,
      "probability_weight": 0.03,
      "seed": 606,
      "status": "configured",
      "provenance": "SYNTHETIC"
    }
  ],
  "provenance": "SYNTHETIC",
  "note": "Scenario metadata only. No simulation results or performance claims are made at Phase 1."
}
```
