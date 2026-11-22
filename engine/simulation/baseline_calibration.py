"""VOLT Engine - Baseline Policy Calibration.

Responsibilities:
- Bounded parameter calibration aligning the reconstructed Business-As-Usual (BAU)
  policy to case reference values under normal operating conditions:
    * Reference 1: Service Reliability = 78.0%
    * Reference 2: Energy Losses = 10.0%
- Physical parameter tuning strictly within realistic engineering bounds.
- NEVER forces or post-hoc overrides measured numerator or denominator values.
- Transparently reports parameter bounds, selected values, objective error, and residuals.
"""

from dataclasses import asdict, dataclass
from typing import Any, Optional
import pandas as pd
from engine.metrics.reconciliation import EnergyReconciliationAuditor
from engine.simulation.baseline_policy import BaselineConfig, BaselineSimulationEngine


@dataclass
class CalibrationParameterBounds:
    """Allowed physical bounds for calibration parameters."""

    station_availability_min: float = 0.72
    station_availability_max: float = 0.88

    charger_efficiency_min: float = 0.90
    charger_efficiency_max: float = 0.95

    swap_charge_efficiency_min: float = 0.86
    swap_charge_efficiency_max: float = 0.93

    auxiliary_load_pct_min: float = 0.015
    auxiliary_load_pct_max: float = 0.040

    distribution_loss_pct_min: float = 0.010
    distribution_loss_pct_max: float = 0.025


@dataclass
class BaselineCalibrationReport:
    """Auditable calibration report documenting parameter selection and KPI residuals."""

    target_service_reliability_pct: float = 78.0
    target_energy_loss_pct: float = 10.0

    measured_service_reliability_pct: float = 0.0
    measured_energy_loss_pct: float = 0.0

    residual_reliability_pct: float = 0.0
    residual_loss_pct: float = 0.0
    total_objective_error: float = 0.0

    calibrated_parameters: dict[str, Any] = None
    parameter_bounds: dict[str, Any] = None
    calibration_sample_hours: int = 0
    energy_reconciliation_pass_rate_pct: float = 100.0
    max_energy_residual_mwh: float = 0.0

    status: str = "CALIBRATED"
    provenance: str = "SYNTHETIC_CALIBRATION"
    notes: str = (
        "Reconstructed baseline parameters were bounded and calibrated to match 78% reliability and "
        "10% losses under the normal reference dataset without forcing or overriding measured outputs."
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return asdict(self)


class BaselineCalibrator:
    """Executes bounded parameter optimization to calibrate the BAU baseline."""

    def __init__(self, bounds: Optional[CalibrationParameterBounds] = None):
        self.bounds = bounds or CalibrationParameterBounds()

    def calibrate(
        self,
        calibration_df: pd.DataFrame,
        target_reliability: float = 78.0,
        target_losses: float = 10.0,
        tolerance_error: float = 0.75,
    ) -> tuple[BaselineConfig, BaselineCalibrationReport]:
        """Run bounded calibration grid search to find parameters matching reference targets.

        Args:
            calibration_df: Normal scenario hourly cluster dataset.
            target_reliability: Target baseline reliability percentage (case fact: 78.0%).
            target_losses: Target baseline loss percentage (case fact: 10.0%).
            tolerance_error: Maximum acceptable cumulative absolute error (|dRel| + |dLoss|).

        Returns:
            Tuple of (optimal BaselineConfig, BaselineCalibrationReport).
        """
        auditor = EnergyReconciliationAuditor()

        # Grid search over physical parameters within allowed engineering bounds
        avail_candidates = [0.76, 0.78, 0.80, 0.82, 0.84]
        loss_candidates = [
            # (charger_eff, swap_eff, aux_pct, dist_pct)
            (0.925, 0.890, 0.024, 0.015),
            (0.930, 0.895, 0.022, 0.014),
            (0.920, 0.885, 0.026, 0.016),
            (0.935, 0.900, 0.020, 0.012),
        ]

        best_config = BaselineConfig()
        best_report: Optional[BaselineCalibrationReport] = None
        lowest_error = float("inf")

        for avail in avail_candidates:
            for ch_eff, sw_eff, aux_pct, dist_pct in loss_candidates:
                cfg = BaselineConfig(
                    station_availability_factor=avail,
                    charger_efficiency=ch_eff,
                    swap_charge_efficiency=sw_eff,
                    auxiliary_load_pct=aux_pct,
                    distribution_loss_pct=dist_pct,
                )

                engine = BaselineSimulationEngine(config=cfg)
                records, _ = engine.run_simulation(calibration_df)
                audit_result = auditor.audit_run(records)

                m_rel = audit_result["measured_kpis"]["measured_service_reliability_pct"]
                m_loss = audit_result["measured_kpis"]["measured_loss_ratio_pct"]

                res_rel = round(m_rel - target_reliability, 2)
                res_loss = round(m_loss - target_losses, 2)
                obj_error = round(abs(res_rel) + abs(res_loss), 2)

                if obj_error < lowest_error:
                    lowest_error = obj_error
                    best_config = cfg

                    best_report = BaselineCalibrationReport(
                        target_service_reliability_pct=target_reliability,
                        target_energy_loss_pct=target_losses,
                        measured_service_reliability_pct=m_rel,
                        measured_energy_loss_pct=m_loss,
                        residual_reliability_pct=res_rel,
                        residual_loss_pct=res_loss,
                        total_objective_error=obj_error,
                        calibrated_parameters={
                            "station_availability_factor": avail,
                            "charger_efficiency": ch_eff,
                            "swap_charge_efficiency": sw_eff,
                            "auxiliary_load_pct": aux_pct,
                            "distribution_loss_pct": dist_pct,
                        },
                        parameter_bounds=asdict(self.bounds),
                        calibration_sample_hours=len(calibration_df),
                        energy_reconciliation_pass_rate_pct=audit_result["reconciliation_pass_rate_pct"],
                        max_energy_residual_mwh=audit_result["residuals"]["max_absolute_residual_mwh"],
                        status="CALIBRATED" if obj_error <= tolerance_error else "BOUNDED_APPROXIMATION",
                    )

        if best_report is None:
            raise RuntimeError("Calibration failed to find a valid parameter set")

        return best_config, best_report
