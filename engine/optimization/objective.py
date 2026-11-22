"""Objective function builder for the MILP energy orchestrator.

Implements risk-aware formulation:
    min Expected_Cost + lambda_risk * CVaR_alpha(Scenario_Cost)

Where:
    - Expected_Cost = sum_s ( pi_s * Scenario_Cost_s )
    - Scenario_Cost_s = DISCOM + IEX + Renewable + BESS_Degradation + Incentives - Retail_Revenue + Penalties
    - CVaR_alpha = eta + (1 / (1 - alpha)) * sum_s ( pi_s * u_s )
    - u_s >= Scenario_Cost_s - eta
    - u_s >= 0

Guarantees:
    - Pure linear objective (no price * quantity non-linear terms)
    - Decoupled retail tariff revenue from incentive cash expenses
    - Zero double-counting of renewable opportunity costs
"""

from typing import Any
import pyomo.environ as pyo


class ObjectiveBuilder:
    """Builds risk-aware objective expressions and scenario cost ledgers."""

    def __init__(
        self,
        cvar_alpha: float = 0.95,
        risk_weight_lambda: float = 0.20,
        unmet_critical_penalty: float = 25000.0,  # INR/MWh
        unmet_flexible_penalty: float = 8000.0,   # INR/MWh
        bess_degradation_cost_inr_per_mwh: float = 1250.0,
        swap_degradation_cost_inr_per_mwh: float = 650.0,
        renewable_curtailment_penalty: float = 500.0,  # INR/MWh
    ):
        self.cvar_alpha = cvar_alpha
        self.risk_weight_lambda = risk_weight_lambda
        self.unmet_critical_penalty = unmet_critical_penalty
        self.unmet_flexible_penalty = unmet_flexible_penalty
        self.bess_degradation_cost = bess_degradation_cost_inr_per_mwh
        self.swap_degradation_cost = swap_degradation_cost_inr_per_mwh
        self.curtailment_penalty = renewable_curtailment_penalty

    def attach_objective(
        self,
        model: pyo.ConcreteModel,
        scenarios: list[str],
        probabilities: dict[str, float],
        clusters: list[str],
        horizon: list[int],
        cohorts: list[Any],
        is_risk_aware: bool = True,
    ) -> None:
        """Construct and attach the complete objective function to the Pyomo model."""

        # 1. Define scenario cost expression
        def scenario_cost_rule(m, s):
            cost_expr = 0.0

            for c in clusters:
                for t in horizon:
                    # DISCOM procurement
                    cost_expr += m.p_discom[c, t, s] * m.param_discom_tariff[c, t, s]
                    # IEX procurement
                    cost_expr += m.p_iex[c, t, s] * m.param_iex_price[c, t, s]
                    # Renewable procurement (contracted PPA rate)
                    cost_expr += m.e_ren_used[c, t, s] * m.param_ren_tariff[c, t, s]
                    # Renewable curtailment penalty (if configured)
                    cost_expr += m.e_ren_curt[c, t, s] * self.curtailment_penalty
                    # Stationary BESS degradation (discharge throughput wear)
                    cost_expr += m.p_bess_dis[c, t, s] * self.bess_degradation_cost
                    # Swap pack charging throughput wear
                    cost_expr += m.p_swap_ch[c, t, s] * self.swap_degradation_cost
                    # Flexibility incentives paid to customers (cash Opex)
                    cost_expr += m.incentive_spend[c, t, s]
                    # Retail dynamic tariff revenue (credited against cost)
                    cost_expr -= m.tariff_revenue[c, t, s]

            # Unserved customer demand penalties
            for k in m.COHORTS:
                cost_expr += m.u_slack_crit[k, s] * self.unmet_critical_penalty
                cost_expr += m.u_slack_flex[k, s] * self.unmet_flexible_penalty

            return cost_expr

        model.scenario_cost = pyo.Expression(model.SCENARIOS, rule=scenario_cost_rule)

        # 2. Expected cost across scenarios
        def expected_cost_rule(m):
            return sum(probabilities[s] * m.scenario_cost[s] for s in scenarios)

        model.expected_cost = pyo.Expression(rule=expected_cost_rule)

        # 3. CVaR Tail Risk Variables & Constraints (if risk-aware and multiple scenarios)
        if is_risk_aware and len(scenarios) > 1 and self.risk_weight_lambda > 0.0:
            model.cvar_eta = pyo.Var(domain=pyo.Reals)
            model.cvar_u = pyo.Var(model.SCENARIOS, domain=pyo.NonNegativeReals)

            def cvar_tail_constraint_rule(m, s):
                return m.cvar_u[s] >= m.scenario_cost[s] - m.cvar_eta

            model.cvar_tail_con = pyo.Constraint(model.SCENARIOS, rule=cvar_tail_constraint_rule)

            def cvar_rule(m):
                inv_alpha = 1.0 / (1.0 - self.cvar_alpha)
                tail_sum = sum(probabilities[s] * m.cvar_u[s] for s in scenarios)
                return m.cvar_eta + inv_alpha * tail_sum

            model.cvar_risk = pyo.Expression(rule=cvar_rule)

            def total_risk_objective_rule(m):
                return m.expected_cost + self.risk_weight_lambda * m.cvar_risk

            model.total_objective = pyo.Objective(rule=total_risk_objective_rule, sense=pyo.minimize)
        else:
            # Deterministic or Risk-Neutral Expected Cost
            def risk_neutral_objective_rule(m):
                return m.expected_cost

            model.total_objective = pyo.Objective(rule=risk_neutral_objective_rule, sense=pyo.minimize)
