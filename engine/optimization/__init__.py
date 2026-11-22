"""VOLT Engine - Optimization Module.

Responsibilities:
- Mixed-Integer Linear Programming (MILP) formulation for multi-cluster energy orchestration.
- Risk-aware objective combining expected operating cost and CVaR tail risk.
- Physical hard constraints: power balance, line import limits, storage dynamics, tariff guardrails, 5% emergency reserve.
- Safe heuristic fallback mechanism when solver exceeds time limit or encounters numerical infeasibility.
- Clear causality breakdown: Reason codes and binding constraint identification for each decision.
"""

from engine.optimization.schemas import (
    BESSInitialState,
    ClusterDailySchedule,
    ClusterHorizonInput,
    DynamicTariffTier,
    HourlyClusterDecision,
    OptimizationKPIs,
    OptimizationMode,
    OptimizationResult,
    ScenarioWeight,
    SolverMetadata,
    SolverStatus,
    SwapInitialState,
)
from engine.optimization.cohorts import CohortAggregator, ServiceCohort
from engine.optimization.model_builder import ModelBuilder
from engine.optimization.objective import ObjectiveBuilder
from engine.optimization.solver import SolverManager
from engine.optimization.extract import SolutionExtractor
from engine.optimization.validation import OptimizationValidator
from engine.optimization.fallback import HeuristicFallbackScheduler
from engine.optimization.comparison import PolicyComparisonEngine
from engine.optimization.pipeline import OptimizationPipeline

__all__ = [
    "BESSInitialState",
    "ClusterDailySchedule",
    "ClusterHorizonInput",
    "DynamicTariffTier",
    "HourlyClusterDecision",
    "OptimizationKPIs",
    "OptimizationMode",
    "OptimizationResult",
    "ScenarioWeight",
    "SolverMetadata",
    "SolverStatus",
    "SwapInitialState",
    "CohortAggregator",
    "ServiceCohort",
    "ModelBuilder",
    "ObjectiveBuilder",
    "SolverManager",
    "SolutionExtractor",
    "OptimizationValidator",
    "HeuristicFallbackScheduler",
    "PolicyComparisonEngine",
    "OptimizationPipeline",
]
