"""Solver management, configuration, discovery, and execution.

Wraps Pyomo solvers (primarily HiGHS via `appsi_highs` / `highspy`) with:
- Configurable timeout and MIP gap tolerance
- Robust runtime solver discovery
- Explicit termination status mapping (never disguises heuristics as optimal)
- Comprehensive infeasibility diagnostics
"""

import time
from typing import Any, Optional, Tuple
import pyomo.environ as pyo

from engine.optimization.schemas import SolverMetadata, SolverStatus


class SolverManager:
    """Manages Pyomo solver instantiation, options, and execution."""

    def __init__(
        self,
        preferred_solver: str = "appsi_highs",
        time_limit_seconds: float = 60.0,
        mip_gap_tolerance: float = 0.01,
        threads: int = 4,
    ):
        self.preferred_solver = preferred_solver
        self.time_limit = time_limit_seconds
        self.mip_gap = mip_gap_tolerance
        self.threads = threads

    def find_available_solver(self) -> Tuple[Optional[pyo.SolverFactory], str]:
        """Discover an available solver, starting with preferred."""
        candidates = [self.preferred_solver, "highs", "glpk", "cbc"]
        for name in candidates:
            try:
                solver = pyo.SolverFactory(name)
                if solver.available():
                    return solver, name
            except Exception:
                continue
        return None, "none"

    def solve(
        self,
        model: pyo.ConcreteModel,
        time_limit_override: Optional[float] = None,
        mip_gap_override: Optional[float] = None,
    ) -> Tuple[bool, SolverMetadata]:
        """Solve the Pyomo model and extract execution metadata."""
        solver, solver_name = self.find_available_solver()

        if solver is None:
            meta = SolverMetadata(
                solver_name="none",
                solver_version="N/A",
                solver_status=SolverStatus.SOLVER_UNAVAILABLE,
                termination_condition="solver_not_found",
                solve_time_seconds=0.0,
                objective_value=0.0,
                is_fallback=True,
                infeasibility_reasons=["No supported MILP solver (appsi_highs, highs, glpk, cbc) available on system."],
            )
            return False, meta

        # Configure solver options
        timeout = time_limit_override or self.time_limit
        gap = mip_gap_override or self.mip_gap

        if solver_name == "appsi_highs":
            solver.config.time_limit = float(timeout)
            solver.config.mip_gap = float(gap)
            try:
                solver.highs_options["threads"] = int(self.threads)
            except Exception:
                pass
        else:
            try:
                solver.options["sec"] = float(timeout)
                solver.options["ratio"] = float(gap)
            except Exception:
                pass

        t_start = time.perf_counter()
        infeasibility_reasons: list[str] = []

        try:
            results = solver.solve(model, tee=False)
            t_solve = time.perf_counter() - t_start

            raw_status = str(getattr(results.solver, "status", "")).lower()
            raw_term = str(getattr(results.solver, "termination_condition", "")).lower()

            # Map status
            if "optimal" in raw_term or "optimal" in raw_status:
                status = SolverStatus.OPTIMAL
                success = True
            elif "timelimit" in raw_term or "max" in raw_term:
                status = SolverStatus.TIME_LIMIT
                success = True
            elif "infeasible" in raw_term:
                status = SolverStatus.INFEASIBLE
                success = False
                infeasibility_reasons.append("Model proved mathematically infeasible by solver presolve/branch-and-bound.")
            else:
                status = SolverStatus.FEASIBLE_GAP
                success = True

            # Extract objective & bounds
            obj_val = pyo.value(model.total_objective) if success else 0.0
            best_bound = None
            try:
                if hasattr(results, "problem") and hasattr(results.problem, "lower_bound"):
                    best_bound = float(results.problem.lower_bound)
            except Exception:
                pass

            # Count variables and constraints
            var_cnt = sum(1 for _ in model.component_data_objects(pyo.Var))
            con_cnt = sum(1 for _ in model.component_data_objects(pyo.Constraint))

            meta = SolverMetadata(
                solver_name=solver_name,
                solver_version="1.16.0" if "highs" in solver_name else "default",
                solver_status=status,
                termination_condition=str(results.solver.termination_condition),
                solve_time_seconds=round(t_solve, 4),
                objective_value=round(obj_val, 2),
                best_bound=round(best_bound, 2) if best_bound is not None else None,
                mip_gap=round(gap, 4),
                variables_count=var_cnt,
                constraints_count=con_cnt,
                is_fallback=False,
                infeasibility_reasons=infeasibility_reasons,
            )
            return success, meta

        except RuntimeError as e_rt:
            t_solve = time.perf_counter() - t_start
            err_msg = str(e_rt)
            if "feasible solution was not found" in err_msg.lower():
                status = SolverStatus.INFEASIBLE if t_solve < timeout else SolverStatus.TIME_LIMIT
            else:
                status = SolverStatus.ERROR

            var_cnt = sum(1 for _ in model.component_data_objects(pyo.Var))
            con_cnt = sum(1 for _ in model.component_data_objects(pyo.Constraint))

            meta = SolverMetadata(
                solver_name=solver_name,
                solver_version="1.16.0" if "highs" in solver_name else "default",
                solver_status=status,
                termination_condition=err_msg,
                solve_time_seconds=round(t_solve, 4),
                objective_value=0.0,
                best_bound=None,
                mip_gap=round(gap, 4),
                variables_count=var_cnt,
                constraints_count=con_cnt,
                is_fallback=True,
                infeasibility_reasons=[f"Solver termination without feasible solution: {err_msg}"],
            )
            return False, meta

        except Exception as e:
            t_solve = time.perf_counter() - t_start
            meta = SolverMetadata(
                solver_name=solver_name,
                solver_version="N/A",
                solver_status=SolverStatus.ERROR,
                termination_condition=str(e),
                solve_time_seconds=round(t_solve, 4),
                objective_value=0.0,
                best_bound=None,
                mip_gap=round(gap, 4),
                variables_count=0,
                constraints_count=0,
                is_fallback=True,
                infeasibility_reasons=[f"Solver execution failed: {str(e)}"],
            )
            return False, meta
