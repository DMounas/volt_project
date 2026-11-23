# VOLT: Reproducibility Guide & Verification Playbook

This document provides exact, end-to-end instructions for reproducing all data generation, forecasting models, test suites, benchmarks, and UI dashboards on a clean workstation.

---

## 1. Environment Setup

### 1.1 Python Virtual Environment
- **Prerequisites:** Python 3.10+ (tested on Python 3.14.0).
- **Setup:**
  ```powershell
  python -m venv .venv
  .venv\Scripts\activate   # On Windows (or 'source .venv/bin/activate' on Linux/macOS)
  python -m pip install --upgrade pip
  pip install -e .
  ```

### 1.2 Frontend Environment
- **Prerequisites:** Node.js v18+ and npm.
- **Setup:**
  ```powershell
  cd frontend
  npm install
  npm run build
  cd ..
  ```

---

## 2. Synthetic Data Generation & Baseline Calibration

Generate all synthetic weather, market, cluster demand, and customer request datasets:

```powershell
# 1. Generate 3-year chronological weather, IEX price, and cluster demand data
python scripts/generate_synthetic_data.py --start-year 2023 --end-year 2025 --seed 42

# 2. Run historical BAU baseline calibration routine
python scripts/run_baseline_calibration.py --output reports/baseline_calibration_report.md

# 3. Generate disaggregated customer fast-charge and battery-swap request streams
python scripts/generate_customer_requests.py --seed 42
```

---

## 3. Automated Test Suite Execution

Run the complete test suite (unit tests, property tests, invariant tests, and API integration tests):

```powershell
# Run full pytest suite (132+ tests)
python -m pytest engine/tests backend/tests -v

# Run targeted fast test suites
python -m pytest engine/tests/test_digital_twin_mpc.py -v
python -m pytest backend/tests/test_benchmark_api.py -v
```

---

## 4. Benchmark & Sensitivity CLI Execution

### 4.1 Full 4-Policy Benchmark Evaluation
Execute the standardized benchmark across all 10 scenarios and 5 fixed seeds:

```powershell
# Run final benchmark evaluation
python scripts/run_final_benchmarks.py --seeds 42,43,44,45,46 --scenarios all --horizon 24

# Diagnostic quick run (6 hours, seed 42)
python scripts/run_final_benchmarks.py --seeds 42 --scenarios NORMAL_OPERATION,HEATWAVE_COMPOUND --horizon 6
```
Outputs generated:
- `reports/benchmark_results/raw_runs.json`
- `reports/benchmark_results/raw_runs.csv`
- `reports/benchmark_results/benchmark_summary.json`
- `reports/FINAL_BENCHMARK_RESULTS.md`

### 4.2 Sensitivity & Ablation Studies
Execute the parameter sensitivity and system ablation studies:

```powershell
python scripts/run_sensitivities_and_ablations.py --horizon 6 --seeds 42
```
Outputs generated:
- `reports/benchmark_results/ablations.json`
- `reports/benchmark_results/sensitivities.json`

### 4.3 Scalability & Solver Failure Telemetry
Measure solver scaling across cities/horizons and verify deterministic fallback:

```powershell
python scripts/run_scalability_and_failure_tests.py
```
Outputs generated:
- `reports/benchmark_results/scalability_and_failure_modes.json`

---

## 5. Running the Application

### 5.1 Backend Server
```powershell
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation available at `http://localhost:8000/docs`.

### 5.2 Frontend Dashboard
```powershell
cd frontend
npm run dev
```
Interactive dashboard opens at `http://localhost:5173`.
