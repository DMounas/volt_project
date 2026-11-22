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

---

## 5. `GET /api/v1/data/manifest`

Returns the master synthetic data manifest with file sizes, row counts, config hashes, and SHA-256 checksums.

### Request
```http
GET /api/v1/data/manifest HTTP/1.1
Host: localhost:8000
Accept: application/json
```

### Response (`200 OK`)
```json
{
  "manifest_version": "1.0.0",
  "generator_version": "1.0.0",
  "provenance": "SYNTHETIC",
  "random_seed": 42,
  "demo_mode": false,
  "date_range": {
    "start": "2022-01-01T00:00:00+05:30",
    "end": "2026-12-31T23:00:00+05:30",
    "total_hours_per_cluster": 43824,
    "total_cluster_hours": 219120,
    "timezone": "Asia/Kolkata"
  },
  "clusters": [
    "delhi_ncr",
    "mumbai_mmr",
    "bengaluru",
    "hyderabad",
    "chennai"
  ],
  "config_hashes": {
    "case_study.yaml": "87f2a52f1375a7280e4b3ffdf2f5f5b84ba1ae478a97adc82e0a124eeb0d85ca",
    "assumptions.yaml": "f518032e0e7cf14c0f7612c79022319c24b4aff50e4618fb3697fd7044fe2669",
    "scenarios.yaml": "c866c435b5ee0c8d427b038be5fa729f4e2396a531dbf2c532b1517ae40ca778",
    "model.yaml": "76f1a5197f2bc2a0f359d9db94f53f8f006ca75bf428687859aa8ca233e82b25"
  },
  "files": {
    "cluster_hourly.csv.gz": {
      "path": "cluster_hourly.csv.gz",
      "row_count": 219120,
      "size_bytes": 7892150,
      "sha256": "cae00d561ed1...",
      "description": "Hourly weather, EV fast-charge, swap demand, and renewable availability by cluster"
    },
    "iex_dam_15min.csv.gz": {
      "path": "iex_dam_15min.csv.gz",
      "row_count": 175296,
      "size_bytes": 1976763,
      "sha256": "5aaf728f18a3...",
      "description": "15-minute Indian Energy Exchange Day-Ahead Market prices and cleared trading volumes"
    }
  },
  "methodology_disclaimer": "All records in this dataset are algorithmically generated and strictly classified as SYNTHETIC."
}
```

---

## 6. `GET /api/v1/data/iex/diagnostics`

Returns structural audit and volume-weighted aggregation diagnostics across 15-minute IEX DAM blocks.

### Request
```http
GET /api/v1/data/iex/diagnostics?sample_records=400 HTTP/1.1
Host: localhost:8000
Accept: application/json
```

### Response (`200 OK`)
```json
{
  "total_15min_records_read": 400,
  "total_hours_produced": 100,
  "aggregation_method_used": "VOLUME_WEIGHTED",
  "complete_hours_count": 100,
  "incomplete_hours_count": 0,
  "duplicate_blocks_count": 0,
  "out_of_order_blocks_count": 0,
  "missing_blocks_details": [],
  "min_hourly_price_inr_mwh": 3150.40,
  "max_hourly_price_inr_mwh": 8920.15,
  "mean_hourly_price_inr_mwh": 5195.80,
  "provenance": "SYNTHETIC"
}
```

---

## 7. `GET /api/v1/baseline/calibration`

Returns the reconstructed Business-As-Usual (BAU) baseline calibration audit report, showing exact measured metrics and residuals against the 78.0% reliability and 10.0% loss benchmarks.

### Request
```http
GET /api/v1/baseline/calibration HTTP/1.1
Host: localhost:8000
Accept: application/json
```

### Response (`200 OK`)
```json
{
  "target_service_reliability_pct": 78.0,
  "target_energy_loss_pct": 10.0,
  "measured_service_reliability_pct": 78.40,
  "measured_energy_loss_pct": 10.18,
  "residual_reliability_pct": 0.40,
  "residual_loss_pct": 0.18,
  "total_objective_error": 0.58,
  "calibrated_parameters": {
    "station_availability_factor": 0.80,
    "charger_efficiency": 0.935,
    "swap_charge_efficiency": 0.90,
    "auxiliary_load_pct": 0.02,
    "distribution_loss_pct": 0.012
  },
  "parameter_bounds": {
    "station_availability_min": 0.72,
    "station_availability_max": 0.88,
    "charger_efficiency_min": 0.90,
    "charger_efficiency_max": 0.95,
    "swap_charge_efficiency_min": 0.86,
    "swap_charge_efficiency_max": 0.93,
    "auxiliary_load_pct_min": 0.015,
    "auxiliary_load_pct_max": 0.04,
    "distribution_loss_pct_min": 0.01,
    "distribution_loss_pct_max": 0.025
  },
  "calibration_sample_hours": 1680,
  "energy_reconciliation_pass_rate_pct": 100.0,
  "max_energy_residual_mwh": 0.00010,
  "status": "CALIBRATED",
  "provenance": "SYNTHETIC_CALIBRATION",
  "notes": "Reconstructed baseline parameters were bounded and calibrated to match 78% reliability and 10% losses under the normal reference dataset without forcing or overriding measured outputs."
}
```

---

## 8. `GET /api/v1/baseline/simulation`

Executes a multi-interval baseline simulation and returns the complete energy meter-boundary reconciliation audit.

### Request
```http
GET /api/v1/baseline/simulation?sample_hours=24 HTTP/1.1
Host: localhost:8000
Accept: application/json
```

### Response (`200 OK`)
```json
{
  "total_intervals_audited": 120,
  "reconciled_intervals_count": 120,
  "reconciliation_pass_rate_pct": 100.0,
  "is_fully_reconciled": true,
  "measured_kpis": {
    "measured_service_reliability_pct": 78.40,
    "measured_loss_ratio_pct": 10.18
  },
  "residuals": {
    "max_absolute_residual_mwh": 0.00010,
    "mean_absolute_residual_mwh": 0.00003,
    "max_percentage_residual": 0.0011
  },
  "energy_accounting_mwh": {
    "gross_energy_supplied": 12450.80,
    "gross_energy_consumed": 12450.80,
    "customer_fast_charge_delivered": 7520.40,
    "customer_swap_energy_equivalent_delivered": 3662.10,
    "total_served_energy_equivalent": 11182.50,
    "total_losses_and_auxiliary": 1268.30,
    "loss_breakdown": {
      "charger_conversion_loss": 523.50,
      "swap_pack_charging_loss": 406.90,
      "bess_round_trip_loss": 38.20,
      "station_auxiliary_load": 149.80,
      "distribution_loss": 149.90
    }
  },
  "renewable_accounting_mwh": {
    "available": 4820.50,
    "utilized": 4510.20,
    "curtailed": 310.30,
    "utilization_pct": 93.56
  },
  "reserve_compliance": true,
  "no_double_counting_audit": "PASSED: Swap pack usable energy (2.25 kWh/pack) counted ONCE in service reliability numerator. Subsequent pack charging energy is accounted strictly as an electrical demand flow.",
  "provenance": "SYNTHETIC"
}
```
