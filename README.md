# VOLT — Virtual Orchestration of Load, Tariffs & Energy

**Decision-Support Digital Twin for Multi-City EV Fast-Charging & Battery-Swapping Operations**

---

## 1. Executive Overview

**VOLT** is a decision-support digital twin and energy orchestration platform designed for a five-city commercial EV fast-charging and battery-swapping network in India across **Delhi NCR, Mumbai MMR, Bengaluru, Hyderabad, and Chennai**.

VOLT co-optimizes:
1. Wholesale energy procurement from open-access renewables, DISCOM tariffs, and Indian Energy Exchange (IEX) Day-Ahead/Real-Time markets;
2. Stationary Battery Energy Storage System (BESS) dispatch;
3. Swappable battery pack replenishment and inventory transitions;
4. Customer dynamic tariffs and flexibility incentive windows within strict regulatory bounds;
5. Mandatory uncommitted emergency reserves for priority public and fleet services.

> **CRITICAL METHODOLOGICAL NOTICE:**  
> VOLT is an analytical prototype and decision-support simulation, **NOT** a live grid-control system or authorized IEX market-bidding gateway. It operates under rolling Model Predictive Control (MPC) in a virtual simulation environment.

---

## 2. Source-Provided Case Facts vs. Modelling Assumptions

VOLT enforces strict provenance tracking across every parameter:
- **`OBSERVED`**: Real-world facts directly extracted from the project case study.
- **`ASSUMED`**: Explicit, configurable engineering assumptions with sensitivity ranges.
- **`SYNTHETIC`**: Algorithmically generated disturbance profiles for stress testing.
- **`SYNTHETIC_CALIBRATION`**: Empirically calibrated simulation parameters tuned within bounded physical ranges to reproduce historical reference metrics without metric forcing.

| Metric / Parameter | Value / Range | Provenance | Specification Treatment |
|---|---|---|---|
| **Operational Clusters** | Delhi NCR, Mumbai MMR, Bengaluru, Hyderabad, Chennai | `OBSERVED` | Five electrically isolated nodes; physical inter-city power wheeling is strictly prohibited. |
| **Installed Power Capacity** | 1,200 MW combined | `OBSERVED` | System-wide capacity. City allocation is unknown and assumed at 20% (240 MW) per cluster baseline. |
| **Modality Mix** | 60% DC Fast-Charging (720 MW) / 40% Swap Stations (480 MW) | `OBSERVED` | Aggregate modality power capacities. |
| **Combined Storage Capacity** | 600 MWh combined | `OBSERVED` | Asset split between stationary BESS and swap packs is unknown; assumed 50/50 (300 MWh / 300 MWh) baseline in `assumptions.yaml`. |
| **Renewable Sourcing** | 35% reference share | `OBSERVED` | Portfolio open-access volume benchmark; not a rigid 35% hourly generation quota. |
| **Service Reliability** | Current 78.0% baseline &rarr; Target 89.7% | `OBSERVED` | Stated business target (15% relative improvement); not claimed as achieved in Phase 1. |
| **Energy Losses** | Current 10.0% baseline &rarr; Target 8.0% | `OBSERVED` | Stated reduction target (20% relative reduction); evaluated via physical simulation. |
| **EBITDA Operating Margin** | Target > 12.0% per cluster | `OBSERVED` | Accounting operating margin target evaluated cluster-by-cluster and consolidated. |
| **Emergency Reserve Buffer** | 5.0% uncommitted capacity and swap inventory | `OBSERVED` | Non-negotiable hard constraint reserved for emergency services. |
| **Customer Dynamic Tariff Bound** | 0.80&times; to 1.20&times; previous-day average tariff | `OBSERVED` | Regulatory guardrail bounding algorithmic tariff and rebate recommendations. |

---

## 3. System Architecture

```text
┌────────────────────────────────────────────────────────┐
│                   React + TypeScript UI                │
│    (Overview, Simulation, Forecasts, Optimization)     │
└───────────────────────────▲────────────────────────────┘
                            │ REST / JSON (FastAPI)
┌───────────────────────────┴────────────────────────────┐
│                    VOLT Backend API                    │
│   ├── /api/v1/health                                   │
│   ├── /api/v1/config/case                              │
│   ├── /api/v1/clusters                                 │
│   └── /api/v1/scenarios                                │
└───────────────────────────▲────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────┐
│                      VOLT Engine                       │
│  ├── data/          Ingestion & 15-min IEX adapters    │
│  ├── forecasting/   Probabilistic quantile models      │
│  ├── scenarios/     Correlated stress disturbance sets │
│  ├── customer/      Service windows & tariff bounds    │
│  ├── batteries/     Decoupled BESS & swap pack physics │
│  ├── optimization/  Pyomo MILP with CVaR & fallback   │
│  ├── control/       Rolling MPC feedback orchestrator  │
│  ├── simulation/    Discrete-event digital twin        │
│  └── metrics/       Reliability, losses, EBITDA audits │
└────────────────────────────────────────────────────────┘
```

---

## 4. Repository Structure

```text
volt/
├── README.md                           # Master documentation
├── VOLT_Technical_Specification_v1.md # Baseline specification
├── pyproject.toml                     # Python dependencies and pytest configuration
├── .env.example                       # Environment template
├── .gitignore                         # Git exclusion rules
├── docker-compose.yml                 # PostgreSQL & container services
├── configs/
│   ├── case_study.yaml                # Source-provided case facts ONLY
│   ├── assumptions.yaml               # Unknown parameters, rationale, bounds & calibrated values
│   ├── scenarios.yaml                 # Disturbance scenarios (NORMAL, CRISIS, etc.)
│   └── model.yaml                     # MPC temporal & solver configuration
├── data/
│   └── synthetic/                     # Generated 5-city compressed datasets & manifest
│       ├── cluster_hourly.csv.gz       # 219,120 rows across 5 clusters (2022-2026)
│       ├── iex_dam_15min.csv.gz        # 876,480 rows 15-minute IEX DAM market data
│       ├── battery_pack_hourly.csv.gz  # 219,120 rows battery pack inventory tracking
│       ├── customer_requests.csv.gz    # Representative hourly charging requests
│       ├── swap_events.csv.gz          # Hourly swap events and pack transitions
│       └── data_manifest.json          # Integrity hashes, row counts, and date bounds
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py                    # FastAPI application with Phase 1 & 2 routes
│   │   ├── api/routes/                # Endpoints (/health, /case, /clusters, /scenarios, /data, /baseline)
│   │   ├── schemas/                   # Pydantic schemas with provenance tracking
│   │   ├── services/                  # Configuration & synthetic data services
│   │   └── db/                        # PostgreSQL connection pool & session manager
│   └── tests/                         # Backend API & service tests
├── engine/
│   ├── provenance.py                  # Provenance enum (OBSERVED, ASSUMED, SYNTHETIC, SYNTHETIC_CALIBRATION)
│   ├── units.py                       # Unit conversion utilities (MW, MWh, kWh, INR)
│   ├── validation.py                  # Physical constraint validators
│   ├── data/                          # Synthetic data generator & 15-min IEX adapters
│   │   ├── synthetic_generator.py     # Deterministic 5-city vectorized synthetic data generator
│   │   └── iex_adapter.py             # IEX 15-min to hourly weighted aggregation adapter
│   ├── forecasting/                   # Demand, price & renewable forecasters
│   ├── scenarios/                     # Multi-vector scenario generator
│   ├── customer/                      # Customer flexibility & incentive bounds
│   ├── batteries/                     # Separate BESS and swap pack models
│   ├── optimization/                  # MILP formulation & solver interfaces
│   ├── control/                       # Rolling-horizon MPC loop
│   ├── simulation/                    # Digital-twin discrete simulator & baseline policy
│   │   ├── baseline_policy.py         # Business-as-Usual (BAU) heuristic dispatch policy
│   │   └── baseline_calibration.py    # Bounded parameter search against reference KPIs
│   ├── metrics/                       # Energy reconciliation, reliability & loss audits
│   │   └── reconciliation.py          # Strict meter-boundary energy balance auditor
│   └── tests/                         # Engine unit & validation tests
├── frontend/                          # React + TypeScript dashboard (Vite + TailwindCSS)
├── scripts/
│   ├── generate_synthetic_data.py     # CLI to generate reproducible 5-city dataset
│   └── run_baseline_calibration.py    # CLI to calibrate BAU policy to 78% reliability & 10% losses
├── reports/
│   ├── phase2_data_quality.md         # Synthetic data quality audit and integrity hashes
│   └── phase2_baseline_calibration.md # Calibration residuals and meter reconciliation report
└── docs/
    ├── data_dictionary.md             # Logical entity schemas & energy balance records
    ├── assumptions_register.md        # Register of all unsupplied assumptions & calibrated params
    └── api_contracts.md               # API endpoint specifications (v1 to v8)
```

---

## 5. Getting Started & Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- (Optional) Docker and Docker Compose (for PostgreSQL container)

### Step 1: Environment Setup
```powershell
# Copy environment configuration
cp .env.example .env
```

### Step 2: Generate Synthetic Datasets
Generate the complete 5-year, 5-city dataset (2022-01-01 to 2026-12-31, 219,120 cluster-hours):
```powershell
# Full 5-year dataset generation (deterministic, gzip-compressed)
python scripts/generate_synthetic_data.py --full

# Or quick demo dataset (30 days):
python scripts/generate_synthetic_data.py --demo
```

### Step 3: Run Baseline Policy & Bounded Calibration
Calibrate the physical dispatch simulation to reproduce the historical reference conditions (78.0% reliability, 10.0% losses):
```powershell
python scripts/run_baseline_calibration.py
```

### Step 4: Run Tests
From the project root:
```powershell
python -m pytest
```
Output confirms all 42 tests pass across engine units, physical validations, synthetic generator, IEX adapter, BAU policy, energy reconciliation, and backend API routes.

### Step 5: Running the Backend
From the project root:
```powershell
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive Swagger docs available at: `http://localhost:8000/docs`

Key API routes available:
- `GET /api/v1/health` — System status and PostgreSQL connection
- `GET /api/v1/config/case` — Source-provided case parameters
- `GET /api/v1/data/manifest` — Data integrity manifest and file checksums
- `GET /api/v1/data/summary` — Aggregate statistics across all 5 clusters
- `GET /api/v1/data/iex/diagnostics` — IEX 15-min adapter validation diagnostics
- `GET /api/v1/baseline/calibration` — Calibration parameters and residuals
- `GET /api/v1/baseline/simulation` — Simulated hourly dispatch and energy balance

### Step 6: Running the Frontend
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser to inspect the interactive digital twin dashboard.

---

## 6. Phase 2 Calibration & Verification Summary

### Bounded Baseline Calibration Results
Calibration was executed via bounded grid search over physical operational parameters without any post-hoc metric forcing or KPI overrides:

| Metric | Reference Baseline | Measured Simulated | Residual | Status |
|---|---|---|---|---|
| **Service Reliability** | 78.00% (`OBSERVED`) | **78.40%** | +0.40% | **PASSED** (within &plusmn;1.5% bound) |
| **Energy Losses** | 10.00% (`OBSERVED`) | **10.18%** | +0.18% | **PASSED** (within &plusmn;0.8% bound) |
| **Cumulative Residual** | — | **0.58%** | — | Optimal calibrated configuration |

**Calibrated Physical Parameters (`SYNTHETIC_CALIBRATION`):**
- Station Availability Factor: `0.800` (80.0% average uptime)
- Charger Efficiency: `0.935` (93.5% AC-DC conversion efficiency)
- Swap Charging Efficiency: `0.900` (90.0% pack recharge efficiency)
- Auxiliary Station Load: `0.020` (2.0% base facility parasitic load)
- Distribution Loss Factor: `0.012` (1.2% internal distribution losses)

### Energy Reconciliation Audit
- **Audited Time Steps:** 3,600 cluster-hours across all 5 clusters.
- **Balance Audit Pass Rate:** **100.0%** (3,600 / 3,600).
- **Maximum Balance Residual:** **0.00010 MWh** (0.0011% relative tolerance, well below the 0.01% threshold).
- **Double-Counting Verification:** Swap energy delivered to EV batteries ($E_{\text{swap,delivered}}$) is strictly decoupled from subsequent pack replenishment energy ($E_{\text{swap,charge}}$).

---

## 7. Current Implementation Boundaries (Phase 2)

1. **Forecasting Models (Phase 3):** LightGBM/CatBoost quantile forecasters and neural temporal models are deferred to Phase 3. Forecasters are currently stubbed via runtime protocols.
2. **Dynamic Tariffs & Flexibility (Phase 4):** Customer flexibility response models and price-elastic demand shifting will be integrated in Phase 4.
3. **MILP Mathematical Optimization (Phase 5):** The dispatch in Phase 2 utilizes a deterministic heuristic Business-as-Usual (BAU) baseline. Pyomo MILP optimization and CVaR risk formulation will be implemented in Phase 5.
4. **Rolling-Horizon MPC (Phase 6):** Feedback-driven rolling-horizon closed-loop MPC orchestration is scheduled for Phase 6.
5. **Live Grid Execution:** VOLT is an analytical digital twin and simulation prototype. It does not interface with live SCADA, hardware switches, or submit binding financial bids to the Indian Energy Exchange.
6. **Target Feasibility:** Stated business targets (89.7% reliability, 8.0% losses, >12% EBITDA) are long-term business goals evaluated during optimized simulation, not baseline achievements.
