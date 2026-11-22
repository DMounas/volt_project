"""Tests for solver management, discovery, options configuration, and heuristic fallback."""

import pytest
from engine.optimization.fallback import HeuristicFallbackScheduler
from engine.optimization.pipeline import OptimizationPipeline
from engine.optimization.schemas import OptimizationMode, SolverStatus
from engine.optimization.solver import SolverManager


def test_solver_discovery():
    """Verify that an available solver is discovered (appsi_highs)."""
    mgr = SolverManager()
    solver, name = mgr.find_available_solver()
    assert solver is not None
    assert name in ("appsi_highs", "highs", "glpk", "cbc")


def test_solver_metadata_records_timing_and_gap():
    """Verify that solve time and MIP gap are surfaced in metadata."""
    pipe = OptimizationPipeline()
    res = pipe.run_optimization(mode=OptimizationMode.DETERMINISTIC_P50, time_limit_seconds=15.0, mip_gap=0.01)

    meta = res.solver_metadata
    assert meta.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE_GAP)
    assert meta.solve_time_seconds > 0.0
    assert meta.mip_gap == 0.01
    assert meta.variables_count > 0
    assert meta.constraints_count > 0


def test_heuristic_fallback_scheduler_compliance():
    """Verify fallback scheduler generates compliant emergency reserve and headroom schedule."""
    pipe = OptimizationPipeline()
    inputs = pipe.load_cluster_inputs()
    cohorts = pipe.load_customer_cohorts()

    fallback = HeuristicFallbackScheduler()
    res = fallback.generate_fallback_schedule(inputs, cohorts, reason="Test fallback execution")

    assert res.solver_metadata.is_fallback is True
    assert res.solver_metadata.solver_status == SolverStatus.FALLBACK_HEURISTIC
    assert res.kpis.power_headroom_reserve_compliant is True
    assert res.kpis.bess_emergency_reserve_compliant is True
    assert res.kpis.swap_emergency_reserve_compliant is True
    assert res.kpis.deadline_violations_count == 0


def test_unavailable_solver_handling():
    """Verify that an unavailable solver reports SOLVER_UNAVAILABLE and does not pretend success."""
    mgr = SolverManager(preferred_solver="non_existent_solver_xyz_123")
    # Temporarily override candidates
    mgr.find_available_solver = lambda: (None, "none")

    import pyomo.environ as pyo
    m = pyo.ConcreteModel()
    m.x = pyo.Var()
    m.obj = pyo.Objective(expr=m.x)

    success, meta = mgr.solve(m)
    assert success is False
    assert meta.solver_status == SolverStatus.SOLVER_UNAVAILABLE
    assert meta.is_fallback is True
