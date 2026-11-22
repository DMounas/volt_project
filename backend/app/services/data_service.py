"""Service for dataset inspection, IEX adapter diagnostics, and baseline simulation audits."""

import json
from pathlib import Path
from typing import Any, Optional
import pandas as pd
from backend.app.schemas.baseline_schemas import (
    BaselineCalibrationResponse,
    BaselineSimulationResponse,
    IEXDiagnosticsResponse,
)
from backend.app.schemas.data_schemas import (
    ClusterHourlySummaryItem,
    DataManifestResponse,
    DataSummaryResponse,
    HourlyDataPoint,
    HourlyDataResponse,
)
from engine.data.iex_adapter import IEXMarketAdapter
from engine.metrics.reconciliation import EnergyReconciliationAuditor
from engine.provenance import Provenance
from engine.simulation.baseline_calibration import BaselineCalibrator
from engine.simulation.baseline_policy import BaselineConfig, BaselineSimulationEngine


class DataService:
    """Provides high-performance access to synthetic data, adapter diagnostics, and simulation reports."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/synthetic")
        self._summary_cache: Optional[DataSummaryResponse] = None
        self._calib_cache: Optional[BaselineCalibrationResponse] = None

    def get_manifest(self) -> DataManifestResponse:
        """Load and return the master synthetic data manifest."""
        manifest_path = self.data_dir / "data_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"Data manifest not found at {manifest_path}. Run generate_synthetic_data.py first."
            )

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return DataManifestResponse(**data)

    def get_data_summary(self) -> DataSummaryResponse:
        """Compute and return aggregated statistics for all five clusters."""
        if self._summary_cache is not None:
            return self._summary_cache

        cluster_file = self.data_dir / "cluster_hourly.csv.gz"
        if not cluster_file.exists():
            raise FileNotFoundError(f"Cluster dataset not found at {cluster_file}")

        df = pd.read_csv(cluster_file, compression="gzip")
        manifest = self.get_manifest()

        summaries: list[ClusterHourlySummaryItem] = []
        for cid, group in df.groupby("cluster_id"):
            summaries.append(
                ClusterHourlySummaryItem(
                    cluster_id=str(cid),
                    cluster_name=str(group["cluster_name"].iloc[0]),
                    hours_count=len(group),
                    mean_temperature_c=round(float(group["temperature_c"].mean()), 1),
                    mean_fast_charge_demand_mwh=round(float(group["fast_charge_demand_mwh"].mean()), 2),
                    max_fast_charge_demand_mwh=round(float(group["fast_charge_demand_mwh"].max()), 2),
                    mean_swap_requests=round(float(group["swap_requests"].mean()), 1),
                    max_swap_requests=int(group["swap_requests"].max()),
                    mean_renewable_available_mwh=round(float(group["renewable_available_mwh"].mean()), 2),
                    max_renewable_available_mwh=round(float(group["renewable_available_mwh"].max()), 2),
                    provenance=Provenance.SYNTHETIC,
                )
            )

        resp = DataSummaryResponse(
            total_clusters=len(summaries),
            total_hours_per_cluster=manifest.date_range["total_hours_per_cluster"],
            total_cluster_hours=manifest.date_range["total_cluster_hours"],
            date_range={
                "start": manifest.date_range["start"],
                "end": manifest.date_range["end"],
            },
            cluster_summaries=summaries,
            provenance=Provenance.SYNTHETIC,
        )
        self._summary_cache = resp
        return resp

    def get_hourly_timeseries(
        self, cluster_id: str, limit: int = 168, offset: int = 0
    ) -> HourlyDataResponse:
        """Return paginated hourly time series records for a cluster."""
        cluster_file = self.data_dir / "cluster_hourly.csv.gz"
        if not cluster_file.exists():
            raise FileNotFoundError(f"Cluster dataset not found at {cluster_file}")

        df = pd.read_csv(cluster_file, compression="gzip")
        sub_df = df[df["cluster_id"] == cluster_id].iloc[offset : offset + limit]

        points = [
            HourlyDataPoint(
                timestamp=str(row["timestamp"]),
                cluster_id=str(row["cluster_id"]),
                temperature_c=float(row["temperature_c"]),
                fast_charge_demand_mwh=float(row["fast_charge_demand_mwh"]),
                swap_requests=int(row["swap_requests"]),
                swap_energy_equivalent_mwh=float(row["swap_energy_equivalent_mwh"]),
                solar_available_mwh=float(row["solar_available_mwh"]),
                wind_available_mwh=float(row["wind_available_mwh"]),
                renewable_available_mwh=float(row["renewable_available_mwh"]),
                discom_tariff_inr_mwh=float(row["discom_tariff_inr_mwh"]),
                iex_projected_price_inr_mwh=float(row["iex_projected_price_inr_mwh"]),
                provenance=Provenance.SYNTHETIC,
            )
            for _, row in sub_df.iterrows()
        ]

        total_pts = int((df["cluster_id"] == cluster_id).sum())
        return HourlyDataResponse(
            cluster_id=cluster_id,
            total_points=total_pts,
            limit=limit,
            offset=offset,
            data=points,
            provenance=Provenance.SYNTHETIC,
        )

    def get_iex_diagnostics(self, sample_records: int = 4000) -> IEXDiagnosticsResponse:
        """Run IEX adapter over a sample of 15-minute market records and return diagnostic audit."""
        iex_file = self.data_dir / "iex_dam_15min.csv.gz"
        if not iex_file.exists():
            raise FileNotFoundError(f"IEX 15-minute dataset not found at {iex_file}")

        df_15min = pd.read_csv(iex_file, compression="gzip", nrows=sample_records)
        adapter = IEXMarketAdapter()
        _, diag = adapter.aggregate_15min_to_hourly(df_15min)

        return IEXDiagnosticsResponse(
            total_15min_records_read=diag.total_15min_records_read,
            total_hours_produced=diag.total_hours_produced,
            aggregation_method_used=diag.aggregation_method_used,
            complete_hours_count=diag.complete_hours_count,
            incomplete_hours_count=diag.incomplete_hours_count,
            duplicate_blocks_count=diag.duplicate_blocks_count,
            out_of_order_blocks_count=diag.out_of_order_blocks_count,
            missing_blocks_details=diag.missing_blocks_details,
            total_cleared_energy_mwh=diag.total_cleared_energy_mwh,
            average_cleared_power_mw=diag.average_cleared_power_mw,
            min_hourly_price_inr_mwh=diag.min_hourly_price_inr_mwh,
            max_hourly_price_inr_mwh=diag.max_hourly_price_inr_mwh,
            mean_hourly_price_inr_mwh=diag.mean_hourly_price_inr_mwh,
            provenance=Provenance.SYNTHETIC,
        )

    def get_baseline_calibration(self) -> BaselineCalibrationResponse:
        """Return the baseline policy calibration report and residuals."""
        if self._calib_cache is not None:
            return self._calib_cache

        cluster_file = self.data_dir / "cluster_hourly.csv.gz"
        if not cluster_file.exists():
            raise FileNotFoundError(f"Cluster dataset not found at {cluster_file}")

        df_slice = pd.read_csv(cluster_file, compression="gzip", nrows=1680)
        calibrator = BaselineCalibrator()
        _, report = calibrator.calibrate(df_slice)

        resp = BaselineCalibrationResponse(
            target_service_reliability_pct=report.target_service_reliability_pct,
            target_energy_loss_pct=report.target_energy_loss_pct,
            measured_service_reliability_pct=report.measured_service_reliability_pct,
            measured_energy_loss_pct=report.measured_energy_loss_pct,
            residual_reliability_pct=report.residual_reliability_pct,
            residual_loss_pct=report.residual_loss_pct,
            total_objective_error=report.total_objective_error,
            calibrated_parameters=report.calibrated_parameters,
            parameter_bounds=report.parameter_bounds,
            calibration_sample_hours=report.calibration_sample_hours,
            energy_reconciliation_pass_rate_pct=report.energy_reconciliation_pass_rate_pct,
            max_energy_residual_mwh=report.max_energy_residual_mwh,
            status=report.status,
            provenance=report.provenance,
            notes=report.notes,
        )
        self._calib_cache = resp
        return resp

    def get_baseline_simulation(self, sample_hours: int = 168) -> BaselineSimulationResponse:
        """Run and audit baseline policy over sample hours across five clusters."""
        cluster_file = self.data_dir / "cluster_hourly.csv.gz"
        if not cluster_file.exists():
            raise FileNotFoundError(f"Cluster dataset not found at {cluster_file}")

        # sample_hours per cluster * 5 clusters
        df_sim = pd.read_csv(cluster_file, compression="gzip", nrows=sample_hours * 5)
        engine = BaselineSimulationEngine()
        records, summary = engine.run_simulation(df_sim)

        auditor = EnergyReconciliationAuditor()
        audit_res = auditor.audit_run(records)

        return BaselineSimulationResponse(
            total_intervals_audited=audit_res["total_intervals_audited"],
            reconciled_intervals_count=audit_res["reconciled_intervals_count"],
            reconciliation_pass_rate_pct=audit_res["reconciliation_pass_rate_pct"],
            is_fully_reconciled=audit_res["is_fully_reconciled"],
            measured_kpis=audit_res["measured_kpis"],
            residuals=audit_res["residuals"],
            energy_accounting_mwh=audit_res["energy_accounting_mwh"],
            renewable_accounting_mwh=audit_res["renewable_accounting_mwh"],
            reserve_compliance=summary["reserve_compliance"],
            no_double_counting_audit=audit_res["no_double_counting_audit"],
            provenance=Provenance.SYNTHETIC,
        )


data_service = DataService()
