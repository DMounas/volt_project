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
│   ├── assumptions.yaml               # Unknown parameters, rationale & sensitivity bounds
│   ├── scenarios.yaml                 # Disturbance scenarios (NORMAL, CRISIS, etc.)
│   └── model.yaml                     # MPC temporal & solver configuration
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py                    # FastAPI application
│   │   ├── api/routes/                # Endpoints (/health, /case, /clusters, /scenarios)
│   │   ├── schemas/                   # Pydantic schemas with provenance
│   │   ├── services/                  # Configuration loading & validation service
│   │   └── db/                        # PostgreSQL connection pool & session manager
│   └── tests/                         # Backend API & service tests
├── engine/
│   ├── provenance.py                  # Provenance enum (OBSERVED, ASSUMED, SYNTHETIC)
│   ├── units.py                       # Unit conversion utilities (MW, MWh, kWh, INR)
│   ├── validation.py                  # Physical constraint validators
│   ├── data/                          # Data loaders & IEX adapters
│   ├── forecasting/                   # Demand, price & renewable forecasters
│   ├── scenarios/                     # Multi-vector scenario generator
│   ├── customer/                      # Customer flexibility & incentive bounds
│   ├── batteries/                     # Separate BESS and swap pack models
│   ├── optimization/                  # MILP formulation & solver interfaces
│   ├── control/                       # Rolling-horizon MPC loop
│   ├── simulation/                    # Digital-twin discrete simulator
│   ├── metrics/                       # Case KPI calculators
│   └── tests/                         # Engine unit & validation tests
├── frontend/                          # React + TypeScript dashboard (Vite)
├── scripts/                           # Utility scripts placeholder
├── reports/                           # Simulation reports & export artifacts
└── docs/
    ├── data_dictionary.md             # Logical entity schemas
    ├── assumptions_register.md        # Register of all unsupplied assumptions
    └── api_contracts.md               # API endpoint specifications
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

### Step 2: Running Backend Tests
From the project root:
```powershell
python -m pytest
```
Output confirms all 20 tests pass across engine units, physical validations, and API routes.

### Step 3: Running the Backend
From the project root:
```powershell
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive Swagger docs available at: `http://localhost:8000/docs`

### Step 4: Running the Frontend
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 6. Current Implementation Limitations (Phase 1)

1. **Optimization Models**: No MILP models are solved in Phase 1; solver settings and problem formulation are defined as configurable specifications for Phase 5.
2. **Forecast Models**: Forecasters are defined via runtime protocols; synthetic training pipelines are scheduled for Phase 3.
3. **Live Grid Execution**: VOLT does not connect to live grid infrastructure or place binding orders on the Indian Energy Exchange.
4. **Target Feasibility**: Stated business targets (89.7% reliability, 8.0% losses, >12% EBITDA) are business benchmarks to be evaluated during simulation, not guaranteed outcomes.
