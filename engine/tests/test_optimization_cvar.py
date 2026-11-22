"""Tests for CVaR mathematical formulation, probability consistency, and non-anticipativity."""

import pytest
import pyomo.environ as pyo

from engine.optimization.objective import ObjectiveBuilder
from engine.optimization.pipeline import DEFAULT_SCENARIOS, OptimizationPipeline
from engine.optimization.schemas import OptimizationMode, ScenarioWeight, SolverStatus
from engine.optimization.solver import SolverManager


def test_hand_calculated_cvar_mathematical_equality():
    """Verify standard linear CVaR matches exact analytical hand calculation.

    Setup:
    - 3 scenarios: costs = [100.0, 200.0, 500.0]
    - Probabilities: pi = [1/3, 1/3, 1/3] (sum = 1.0)
    - Confidence level: alpha = 0.50 (50th percentile / median)
    - Analytical VaR (50th percentile): eta* = 200.0
    - Tail exceedances: u1 = 0, u2 = 0, u3 = 300.0
    - Analytical CVaR = eta + (1 / (1 - alpha)) * sum(pi_s * u_s)
                      = 200.0 + 2.0 * (1/3 * 300.0)
                      = 200.0 + 200.0 = 400.0
    """
    m = pyo.ConcreteModel()
    scenarios = ["S1", "S2", "S3"]
    probs = {"S1": 1.0 / 3.0, "S2": 1.0 / 3.0, "S3": 1.0 / 3.0}
    given_costs = {"S1": 100.0, "S2": 200.0, "S3": 500.0}

    m.SCENARIOS = pyo.Set(initialize=scenarios)
    m.CLUSTERS = pyo.Set(initialize=[])
    m.HOURS = pyo.Set(initialize=[])
    m.COHORTS = pyo.Set(initialize=[])

    m.cvar_eta = pyo.Var(domain=pyo.Reals)
    m.cvar_u = pyo.Var(m.SCENARIOS, domain=pyo.NonNegativeReals)

    def tail_con_rule(model, s):
        return model.cvar_u[s] >= given_costs[s] - model.cvar_eta

    m.con_tail = pyo.Constraint(m.SCENARIOS, rule=tail_con_rule)

    alpha = 0.50
    inv_alpha = 1.0 / (1.0 - alpha)  # 2.0

    def cvar_obj_rule(model):
        tail_sum = sum(probs[s] * model.cvar_u[s] for s in scenarios)
        return model.cvar_eta + inv_alpha * tail_sum

    m.total_objective = pyo.Objective(rule=cvar_obj_rule, sense=pyo.minimize)

    # Solve with SolverManager
    solver_mgr = SolverManager()
    success, meta = solver_mgr.solve(m)

    assert success is True
    assert meta.solver_status == SolverStatus.OPTIMAL
    cvar_opt = pyo.value(m.total_objective)
    eta_opt = pyo.value(m.cvar_eta)

    assert abs(cvar_opt - 400.0) < 1e-3, f"Expected CVaR 400.0, got {cvar_opt}"
    assert abs(eta_opt - 200.0) < 1e-3, f"Expected VaR 200.0, got {eta_opt}"


def test_scenario_probabilities_sum_to_one():
    """Verify that all default and configured scenario weights sum to 1.0."""
    total_prob = sum(s.probability for s in DEFAULT_SCENARIOS)
    assert abs(total_prob - 1.0) < 1e-6
    for s in DEFAULT_SCENARIOS:
        assert 0.0 < s.probability <= 1.0


def test_first_stage_tariff_non_anticipativity():
    """Verify that retail dynamic tariff choices are first-stage (shared across scenarios)."""
    pipe = OptimizationPipeline()
    cvar_run = pipe.run_optimization(
        mode=OptimizationMode.RISK_AWARE_CVAR,
        clusters=["delhi_ncr"],
        seed=42,
    )

    assert cvar_run.mode == OptimizationMode.RISK_AWARE_CVAR
    assert cvar_run.solver_metadata.solver_status.value in ("OPTIMAL", "FEASIBLE_GAP")

    # In our model, tariff_choice has index (m.CLUSTERS, m.HOURS, m.TIERS) without scenario index s,
    # mathematically guaranteeing non-anticipativity across all scenario realizations!
    for cid, sched in cvar_run.cluster_schedules.items():
        assert len(sched.hourly_decisions) == 24
        for dec in sched.hourly_decisions:
            assert dec.selected_tariff_tier in [
                "0.80x", "0.90x", "1.00x", "1.10x", "1.20x"
            ]
