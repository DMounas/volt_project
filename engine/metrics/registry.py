"""VOLT Engine - Metric Definitions, Accounting Registry, and KPI Formulas.

Defines the audited, single-source-of-truth formulas and boundary definitions
for all VOLT metrics across controllers, digital twins, benchmarks, and APIs.
Strictly enforces:
- Explicit meter boundaries (Customer Boundary, Substation Feeder, Storage Terminals)
- Separate fast-charge and swap-pack fill rates
- Integer-only swap pack fulfilment (no mixing packs and MWh)
- Non-anticipativity and provenance tagging (SYNTHETIC, ASSUMED, OBSERVED)
- Financial decoupling: retail revenue vs wholesale procurement vs incentives
- EBITDA reported strictly as NOT_EVALUABLE when corporate OpEx is unavailable.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
from engine.provenance import Provenance


class PolicySemantics(str, Enum):
    """Canonical policy identifiers with explicit comparison semantics."""
    HISTORICAL_REFERENCE = "HISTORICAL_REFERENCE"  # Case reference benchmark (78% rel, 10% loss)
    CALIBRATED_BAU = "CALIBRATED_BAU"              # Reconstructed uncoordinated simulator (78.4% rel, 10.18% loss)
    FALLBACK_HEURISTIC = "FALLBACK_HEURISTIC"      # Rule-based safe scheduler when solver unavailable
    OPEN_LOOP_MILP = "OPEN_LOOP_MILP"              # Open-loop 24h static optimization schedule
    CLOSED_LOOP_MPC = "CLOSED_LOOP_MPC"            # Receding-horizon 1h-apply re-optimizing controller


@dataclass(frozen=True)
class MetricDefinition:
    """Metadata specification for an audited metric."""
    key: str
    name: str
    unit: str
    formula: str
    numerator: str
    denominator: str
    boundary: str
    target_value: Optional[float]
    interpretation: str


METRIC_REGISTRY: dict[str, MetricDefinition] = {
    "energy_service_reliability_pct": MetricDefinition(
        key="energy_service_reliability_pct",
        name="Energy Service Reliability",
        unit="%",
        formula="100.0 * (total_energy_delivered_mwh / total_energy_requested_mwh)",
        numerator="Delivered energy at customer vehicle connector boundary (MWh)",
        denominator="Total energy requested during operating hours (MWh)",
        boundary="Customer Vehicle / Charger Output Boundary",
        target_value=89.7,
        interpretation="Percentage of requested energy successfully delivered without balking or rationing.",
    ),
    "fast_charge_fill_rate_pct": MetricDefinition(
        key="fast_charge_fill_rate_pct",
        name="Fast-Charge Energy Fill Rate",
        unit="%",
        formula="100.0 * (fc_energy_delivered_mwh / fc_energy_requested_mwh)",
        numerator="Fast-charge energy dispensed to EV batteries (MWh)",
        denominator="Total fast-charge demand requested (MWh)",
        boundary="DC Fast Charger Dispenser Output",
        target_value=90.0,
        interpretation="Service fulfilment rate specifically for fast-charging sessions.",
    ),
    "swap_pack_fill_rate_pct": MetricDefinition(
        key="swap_pack_fill_rate_pct",
        name="Swap Pack Fulfilment Rate",
        unit="%",
        formula="100.0 * (swap_packs_served / swap_packs_requested)",
        numerator="Fully charged battery packs dispensed to 2W/3W drivers (integer packs)",
        denominator="Total battery pack swap requests received (integer packs)",
        boundary="Battery Swapping Station Dispensing Bay",
        target_value=95.0,
        interpretation="Fulfilment rate in discrete integer packs; never mixed with continuous MWh.",
    ),
    "energy_loss_ratio_pct": MetricDefinition(
        key="energy_loss_ratio_pct",
        name="System Energy Loss Ratio",
        unit="%",
        formula="100.0 * (total_system_losses_mwh / gross_energy_procured_mwh)",
        numerator="Substation Tx + BESS conversion + Swap charger + Local distribution losses (MWh)",
        denominator="Gross energy drawn from 33kV/66kV grid feeders + on-site solar/wind (MWh)",
        boundary="Grid Interconnection Feeder & Substation Inflow Boundary",
        target_value=8.0,
        interpretation="Comprehensive electrical efficiency loss from substation to vehicle connector.",
    ),
    "renewable_share_pct": MetricDefinition(
        key="renewable_share_pct",
        name="Renewable Utilization Share",
        unit="%",
        formula="100.0 * (renewable_energy_used_mwh / total_energy_served_mwh)",
        numerator="Contracted/on-site solar and wind dispatched to load or BESS (MWh)",
        denominator="Total energy supplied to EV chargers and BESS charging (MWh)",
        boundary="Substation AC Bus & Renewable PPA Meter",
        target_value=35.0,
        interpretation="Fraction of served energy originating directly or via storage from renewable PPA.",
    ),
    "procurement_cost_inr": MetricDefinition(
        key="procurement_cost_inr",
        name="Wholesale Energy Procurement Cost",
        unit="INR",
        formula="sum(discom_energy_mwh * discom_tariff) + sum(iex_energy_mwh * iex_price) + sum(ren_energy_mwh * ren_tariff)",
        numerator="Total disbursements to DISCOMs, IEX market, and Renewable IPPs (INR)",
        denominator="None (Total sum over horizon)",
        boundary="Utility Wholesale Settlement Gateways",
        target_value=None,
        interpretation="Direct energy procurement cost paid to wholesale suppliers.",
    ),
    "retail_tariff_revenue_inr": MetricDefinition(
        key="retail_tariff_revenue_inr",
        name="Retail Customer Charging Revenue",
        unit="INR",
        formula="sum(fc_kwh_dispensed * dynamic_tariff_inr) + sum(packs_swapped * swap_fee_inr)",
        numerator="Total collections from EV fleet operators and retail drivers (INR)",
        denominator="None (Total sum over horizon)",
        boundary="Customer Billing Gateway",
        target_value=None,
        interpretation="Gross customer revenue under regulated dynamic tariffs and fixed swap fees.",
    ),
    "flexibility_incentives_inr": MetricDefinition(
        key="flexibility_incentives_inr",
        name="Customer Flexibility Incentives Paid",
        unit="INR",
        formula="sum(opted_in_shifted_energy_kwh * incentive_rate_inr_kwh)",
        numerator="Incentives and credits disbursed to customers shifting charge windows (INR)",
        denominator="None (Total sum over horizon)",
        boundary="Customer Flexibility Settlement Ledger",
        target_value=None,
        interpretation="Expenditure incurred to induce demand shifting during peak tariff periods.",
    ),
    "battery_degradation_expense_inr": MetricDefinition(
        key="battery_degradation_expense_inr",
        name="Battery Degradation Expense",
        unit="INR",
        formula="sum(bess_throughput_mwh) * degradation_rate_inr_mwh",
        numerator="Degradation cost allocated at INR 2,500/MWh BESS throughput (INR)",
        denominator="None",
        boundary="BESS Terminal Lifecycle Ledger",
        target_value=None,
        interpretation="Amortised cell capacity fade cost reflecting cycling wear.",
    ),
    "gross_procurement_margin_inr": MetricDefinition(
        key="gross_procurement_margin_inr",
        name="Gross Procurement Margin",
        unit="INR",
        formula="retail_tariff_revenue_inr - procurement_cost_inr - flexibility_incentives_inr",
        numerator="Retail Revenue minus Wholesale Procurement minus Customer Incentives (INR)",
        denominator="None",
        boundary="Consolidated Commercial Margin Boundary",
        target_value=None,
        interpretation="Net energy trading and charging margin before capital wear and corporate OpEx.",
    ),
    "net_operating_contribution_inr": MetricDefinition(
        key="net_operating_contribution_inr",
        name="Net Operating Contribution",
        unit="INR",
        formula="gross_procurement_margin_inr - battery_degradation_expense_inr - variable_om_inr",
        numerator="Gross Procurement Margin minus Degradation minus Variable O&M (INR)",
        denominator="None",
        boundary="Operating Segment Contribution Boundary",
        target_value=None,
        interpretation="Operating contribution available to cover fixed corporate OpEx, leases, and debt.",
    ),
    "ebitda_disclosure": MetricDefinition(
        key="ebitda_disclosure",
        name="EBITDA Margin Evaluation",
        unit="Status Tag",
        formula="NOT_EVALUABLE (Corporate fixed OpEx, land leases, and tax schedules missing)",
        numerator="N/A",
        denominator="N/A",
        boundary="Corporate Statutory Financial Boundary",
        target_value=12.0,
        interpretation="Formally non-evaluable under GAAP/Ind AS in this operational scheduling prototype.",
    ),
}


class MetricsRegistryService:
    """Service to compute and validate registered metrics."""

    @staticmethod
    def get_metric_definition(key: str) -> Optional[MetricDefinition]:
        return METRIC_REGISTRY.get(key)

    @staticmethod
    def list_all_definitions() -> list[MetricDefinition]:
        return list(METRIC_REGISTRY.values())

    @staticmethod
    def compute_service_reliability(served_mwh: float, requested_mwh: float) -> float:
        if requested_mwh <= 0.0:
            return 100.0 if served_mwh >= 0.0 else 0.0
        return round(100.0 * (served_mwh / requested_mwh), 2)

    @staticmethod
    def compute_swap_fill_rate(served_packs: int, requested_packs: int) -> float:
        if requested_packs <= 0:
            return 100.0 if served_packs >= 0 else 0.0
        return round(100.0 * (served_packs / requested_packs), 2)

    @staticmethod
    def compute_loss_ratio(total_losses_mwh: float, gross_input_mwh: float) -> float:
        if gross_input_mwh <= 0.0:
            return 0.0
        return round(100.0 * (total_losses_mwh / gross_input_mwh), 2)

    @staticmethod
    def compute_renewable_share(renewable_used_mwh: float, total_served_mwh: float) -> float:
        if total_served_mwh <= 0.0:
            return 0.0
        return round(100.0 * (renewable_used_mwh / total_served_mwh), 2)

    @staticmethod
    def get_ebitda_missing_data_list() -> list[str]:
        return [
            "Corporate SG&A and headquarters administrative expenses",
            "Site land lease and concession agreements per metro hub",
            "Station equipment depreciation treatment (Straight-Line vs WDV)",
            "Transformer & switchgear capital debt servicing / financing costs",
            "State-specific corporate income tax, GST input tax credits, and surcharge schedules",
        ]
