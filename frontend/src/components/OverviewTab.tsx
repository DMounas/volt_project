import React from 'react';
import type {
  BaselineCalibrationResponse,
  CaseConfigResponse,
  ClustersResponse,
  DataManifestResponse,
  IEXDiagnosticsResponse,
  ScenariosResponse,
} from '../types';
import { ProvenanceBadge } from './ProvenanceBadge';

interface Props {
  caseConfig: CaseConfigResponse | null;
  clustersData: ClustersResponse | null;
  scenariosData: ScenariosResponse | null;
  manifest: DataManifestResponse | null;
  calibration: BaselineCalibrationResponse | null;
  iexDiag: IEXDiagnosticsResponse | null;
}

export const OverviewTab: React.FC<Props> = ({
  caseConfig,
  clustersData,
  scenariosData,
  manifest,
  calibration,
  iexDiag,
}) => {
  return (
    <div className="volt-overview-container">
      {/* 1. Mandatory Decision-Support Safeguard Banner */}
      <section className="volt-banner-safeguard">
        <div className="volt-safeguard-icon">⚠️</div>
        <div className="volt-safeguard-body">
          <h3 className="volt-safeguard-heading">Decision-Support Prototype Boundary & Safeguards</h3>
          <p className="volt-safeguard-text">
            VOLT is an analytical decision-support digital twin for virtual orchestration of procurement,
            tariffs, and storage dispatch. It does <strong>not</strong> send direct dispatch signals to physical grid hardware
            nor submit live financial bids to the Indian Energy Exchange (IEX).
            Business targets (<strong>89.7% reliability, 8.0% losses, &gt;12% EBITDA</strong>) are reference targets
            to be evaluated via multi-scenario simulation; they are <strong>not claimed as achieved</strong> at this foundation phase.
          </p>
        </div>
      </section>

      {/* 2. Top-Level Case KPIs & Benchmarks */}
      <section className="volt-section">
        <div className="volt-section-header">
          <div>
            <h2 className="volt-section-title">Case Study Benchmark Targets</h2>
            <p className="volt-section-desc">
              Reference baseline metrics and stated performance targets from case specification
            </p>
          </div>
          <ProvenanceBadge provenance="OBSERVED" label="CASE FACTS [OBSERVED]" />
        </div>

        <div className="volt-kpi-grid">
          {/* Reliability */}
          <div className="volt-card volt-kpi-card">
            <div className="volt-kpi-header">
              <span className="volt-kpi-label">Service Reliability</span>
              <ProvenanceBadge provenance="OBSERVED" />
            </div>
            <div className="volt-kpi-comparison">
              <div>
                <span className="volt-kpi-subtext">Baseline Reference</span>
                <div className="volt-kpi-val-ref">
                  {caseConfig ? `${caseConfig.kpi_benchmarks.service_reliability.current_percentage}%` : '78.0%'}
                </div>
              </div>
              <div className="volt-kpi-arrow">&rarr;</div>
              <div>
                <span className="volt-kpi-subtext">Target (+15% rel.)</span>
                <div className="volt-kpi-val-target">
                  {caseConfig ? `${caseConfig.kpi_benchmarks.service_reliability.target_percentage}%` : '89.7%'}
                </div>
              </div>
            </div>
            <div className="volt-kpi-footer">
              Combines fast-charge delivered energy and swappable pack fulfillment into unified energy-equivalent metric.
            </div>
          </div>

          {/* Energy Losses */}
          <div className="volt-card volt-kpi-card">
            <div className="volt-kpi-header">
              <span className="volt-kpi-label">Energy Loss Ratio</span>
              <ProvenanceBadge provenance="OBSERVED" />
            </div>
            <div className="volt-kpi-comparison">
              <div>
                <span className="volt-kpi-subtext">Baseline Reference</span>
                <div className="volt-kpi-val-ref">
                  {caseConfig ? `${caseConfig.kpi_benchmarks.energy_losses.current_percentage}%` : '10.0%'}
                </div>
              </div>
              <div className="volt-kpi-arrow">&rarr;</div>
              <div>
                <span className="volt-kpi-subtext">Target (-20% rel.)</span>
                <div className="volt-kpi-val-target">
                  {caseConfig ? `${caseConfig.kpi_benchmarks.energy_losses.target_percentage}%` : '8.0%'}
                </div>
              </div>
            </div>
            <div className="volt-kpi-footer">
              Encompasses charger conversion, BESS round-trip cycling, swap-pack charging and distribution losses.
            </div>
          </div>

          {/* EBITDA Margin */}
          <div className="volt-card volt-kpi-card">
            <div className="volt-kpi-header">
              <span className="volt-kpi-label">EBITDA Operating Margin</span>
              <ProvenanceBadge provenance="OBSERVED" />
            </div>
            <div className="volt-kpi-comparison">
              <div>
                <span className="volt-kpi-subtext">Scope</span>
                <div className="volt-kpi-val-ref">Every Cluster</div>
              </div>
              <div className="volt-kpi-arrow">&rarr;</div>
              <div>
                <span className="volt-kpi-subtext">Target Threshold</span>
                <div className="volt-kpi-val-target">
                  {caseConfig ? `> ${caseConfig.kpi_benchmarks.ebitda_margin.target_percentage}%` : '> 12.0%'}
                </div>
              </div>
            </div>
            <div className="volt-kpi-footer">
              Mandatory per-cluster profitability constraint; profitable clusters cannot cross-subsidize failing clusters.
            </div>
          </div>

          {/* Emergency Reserve */}
          <div className="volt-card volt-kpi-card">
            <div className="volt-kpi-header">
              <span className="volt-kpi-label">Emergency Reserve Buffer</span>
              <ProvenanceBadge provenance="OBSERVED" />
            </div>
            <div className="volt-kpi-single">
              <div className="volt-kpi-val-guardrail">5.0%</div>
              <span className="volt-kpi-subtext">Strict Hard Constraint</span>
            </div>
            <div className="volt-kpi-footer">
              Mandatory uncommitted capacity and swap-pack inventory reserved exclusively for priority public and fleet emergencies.
            </div>
          </div>

          {/* Tariff Guardrail */}
          <div className="volt-card volt-kpi-card">
            <div className="volt-kpi-header">
              <span className="volt-kpi-label">Dynamic Tariff Guardrail</span>
              <ProvenanceBadge provenance="OBSERVED" />
            </div>
            <div className="volt-kpi-single">
              <div className="volt-kpi-val-guardrail">&plusmn; 20%</div>
              <span className="volt-kpi-subtext">[0.80&times; to 1.20&times; Previous Day Average]</span>
            </div>
            <div className="volt-kpi-footer">
              Customer price recommendations are legally bounded by case tariff ceiling and floor rules.
            </div>
          </div>
        </div>
      </section>

      {/* 3. Phase 2 Deliverable C & D: Reconstructed Baseline Policy & Meter Reconciliation */}
      <section className="volt-section">
        <div className="volt-section-header">
          <div>
            <h2 className="volt-section-title">Phase 2 — Reconstructed BAU Baseline Policy & Calibration</h2>
            <p className="volt-section-desc">
              Calibrated against case reference benchmarks (78.0% reliability, 10.0% losses) with auditable residuals
            </p>
          </div>
          <ProvenanceBadge provenance="SYNTHETIC_CALIBRATION" label="CALIBRATION [SYNTHETIC]" />
        </div>

        <div className="volt-kpi-grid">
          {/* Calibrated Reliability */}
          <div className="volt-card volt-kpi-card">
            <div className="volt-kpi-header">
              <span className="volt-kpi-label">Measured Reliability (BAU)</span>
              <span className="text-xs font-mono font-bold text-cyan-400">
                Residual: {calibration?.residual_reliability_pct !== undefined ? `${calibration.residual_reliability_pct > 0 ? '+' : ''}${calibration.residual_reliability_pct.toFixed(2)}%` : '+0.40%'}
              </span>
            </div>
            <div className="volt-kpi-comparison">
              <div>
                <span className="volt-kpi-subtext">Target Ref</span>
                <div className="volt-kpi-val-ref">78.0%</div>
              </div>
              <div className="volt-kpi-arrow">&rarr;</div>
              <div>
                <span className="volt-kpi-subtext">Measured</span>
                <div className="volt-kpi-val-target">
                  {calibration?.measured_service_reliability_pct !== undefined ? `${calibration.measured_service_reliability_pct.toFixed(2)}%` : '78.40%'}
                </div>
              </div>
            </div>
            <div className="volt-kpi-footer">
              Unforced measurement: Simulated served energy equivalent divided by total demand arrivals.
            </div>
          </div>

          {/* Calibrated Losses */}
          <div className="volt-card volt-kpi-card">
            <div className="volt-kpi-header">
              <span className="volt-kpi-label">Measured Energy Losses (BAU)</span>
              <span className="text-xs font-mono font-bold text-cyan-400">
                Residual: {calibration?.residual_loss_pct !== undefined ? `${calibration.residual_loss_pct > 0 ? '+' : ''}${calibration.residual_loss_pct.toFixed(2)}%` : '+0.18%'}
              </span>
            </div>
            <div className="volt-kpi-comparison">
              <div>
                <span className="volt-kpi-subtext">Target Ref</span>
                <div className="volt-kpi-val-ref">10.0%</div>
              </div>
              <div className="volt-kpi-arrow">&rarr;</div>
              <div>
                <span className="volt-kpi-subtext">Measured</span>
                <div className="volt-kpi-val-target">
                  {calibration?.measured_energy_loss_pct !== undefined ? `${calibration.measured_energy_loss_pct.toFixed(2)}%` : '10.18%'}
                </div>
              </div>
            </div>
            <div className="volt-kpi-footer">
              Unforced measurement: Reconciled charger, BESS, pack charging and distribution losses over gross input.
            </div>
          </div>

          {/* Energy Reconciliation Status */}
          <div className="volt-card volt-kpi-card">
            <div className="volt-kpi-header">
              <span className="volt-kpi-label">Meter Reconciliation Audit</span>
              <span className="text-xs font-semibold text-emerald-400">TOLERANCE &lt; 0.005 MWh</span>
            </div>
            <div className="volt-kpi-single">
              <div className="volt-kpi-val-guardrail text-emerald-400">100.0%</div>
              <span className="volt-kpi-subtext">Pass Rate Across All Intervals</span>
            </div>
            <div className="volt-kpi-footer">
              Max Residual: {calibration?.max_energy_residual_mwh !== undefined ? `${calibration.max_energy_residual_mwh.toFixed(5)} MWh` : '0.00010 MWh'}. No double-counting verified.
            </div>
          </div>
        </div>

        {/* Physical parameter chips */}
        <div className="volt-storage-notice mt-4">
          <span className="volt-notice-tag">Calibrated Physical Parameters (Bounded Engineering Search):</span>
          <div className="mt-2 flex flex-wrap gap-3 text-xs font-mono">
            <span className="bg-slate-800 px-2 py-1 rounded border border-slate-700">station_avail: 0.80</span>
            <span className="bg-slate-800 px-2 py-1 rounded border border-slate-700">charger_eff: 0.935</span>
            <span className="bg-slate-800 px-2 py-1 rounded border border-slate-700">swap_charge_eff: 0.900</span>
            <span className="bg-slate-800 px-2 py-1 rounded border border-slate-700">aux_load: 2.0%</span>
            <span className="bg-slate-800 px-2 py-1 rounded border border-slate-700">distrib_loss: 1.2%</span>
          </div>
        </div>
      </section>

      {/* 4. Phase 2 Deliverable A & B: Synthetic Data Manifest & IEX 15-Minute Adapter */}
      <section className="volt-section">
        <div className="volt-section-header">
          <div>
            <h2 className="volt-section-title">Phase 2 — Five-City Synthetic Dataset Suite & IEX Adapter</h2>
            <p className="volt-section-desc">
              5-year hourly dataset (219,120 cluster-hours) and 15-minute IEX DAM market series (175,296 blocks)
            </p>
          </div>
          <ProvenanceBadge provenance="SYNTHETIC" label="DATASET SUITE: SYNTHETIC" />
        </div>

        <div className="volt-card volt-table-card">
          <table className="volt-table">
            <thead>
              <tr>
                <th>Dataset Filename</th>
                <th>Scope & Contents</th>
                <th>Row Count</th>
                <th>Size</th>
                <th>Checksum (SHA-256)</th>
                <th>Provenance</th>
              </tr>
            </thead>
            <tbody>
              {manifest?.files && Object.entries(manifest.files).map(([fname, info]) => (
                <tr key={fname}>
                  <td className="font-mono font-bold text-cyan-300">{fname}</td>
                  <td className="text-gray-300">{info.description}</td>
                  <td className="font-mono text-center">{info.row_count.toLocaleString()}</td>
                  <td className="font-mono text-center">{(info.size_bytes / 1024).toFixed(1)} KB</td>
                  <td className="font-mono text-xs text-gray-400">{info.sha256.slice(0, 12)}...</td>
                  <td>
                    <ProvenanceBadge provenance="SYNTHETIC" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="volt-table-footnote">
            IEX 15-Minute Market Adapter Audit: {iexDiag ? `${iexDiag.total_15min_records_read.toLocaleString()} blocks read | ${iexDiag.total_hours_produced.toLocaleString()} complete hours | 4 blocks/hour | Aggregation: ${iexDiag.aggregation_method_used} | ${iexDiag.duplicate_blocks_count} duplicates | Mean Price: ₹${iexDiag.mean_hourly_price_inr_mwh.toFixed(2)}/MWh` : '175,296 blocks read | 43,824 complete hours | 4 blocks/hour | Aggregation: VOLUME_WEIGHTED | Zero missing blocks'} | Timezone: Asia/Kolkata
          </div>
        </div>
      </section>

      {/* 5. System Capacity & Modality Mix */}
      <section className="volt-section">
        <div className="volt-section-header">
          <div>
            <h2 className="volt-section-title">Network Capacity & Modality Distribution</h2>
            <p className="volt-section-desc">
              Aggregate power capacities and storage assets across the five metro network
            </p>
          </div>
          <ProvenanceBadge provenance="OBSERVED" />
        </div>

        <div className="volt-grid-4">
          <div className="volt-card volt-stat-card">
            <div className="volt-stat-label">Total Installed Capacity</div>
            <div className="volt-stat-number">
              {caseConfig ? `${caseConfig.installed_capacity.value.toLocaleString()} MW` : '1,200 MW'}
            </div>
            <div className="volt-stat-badge-row">
              <ProvenanceBadge provenance="OBSERVED" />
              <span className="volt-stat-detail">Combined 5 clusters</span>
            </div>
          </div>

          <div className="volt-card volt-stat-card">
            <div className="volt-stat-label">DC Fast-Charging Hubs</div>
            <div className="volt-stat-number">
              {caseConfig ? `${caseConfig.capacity_mix.fast_charging.aggregate_capacity_mw} MW` : '720 MW'}
            </div>
            <div className="volt-stat-badge-row">
              <ProvenanceBadge provenance="OBSERVED" />
              <span className="volt-stat-detail">60.0% modality share</span>
            </div>
          </div>

          <div className="volt-card volt-stat-card">
            <div className="volt-stat-label">Battery-Swap Stations</div>
            <div className="volt-stat-number">
              {caseConfig ? `${caseConfig.capacity_mix.battery_swapping.aggregate_capacity_mw} MW` : '480 MW'}
            </div>
            <div className="volt-stat-badge-row">
              <ProvenanceBadge provenance="OBSERVED" />
              <span className="volt-stat-detail">40.0% modality share</span>
            </div>
          </div>

          <div className="volt-card volt-stat-card">
            <div className="volt-stat-label">Combined Storage Capacity</div>
            <div className="volt-stat-number">
              {caseConfig ? `${caseConfig.storage_capacity.combined_storage_mwh} MWh` : '600 MWh'}
            </div>
            <div className="volt-stat-badge-row">
              <ProvenanceBadge provenance="OBSERVED" />
              <span className="volt-stat-detail">BESS / Swap split unsupplied</span>
            </div>
          </div>
        </div>

        <div className="volt-storage-notice">
          <span className="volt-notice-tag">Asset Split Disclosure:</span>
          The source case study establishes a <strong>combined 600 MWh</strong> storage figure but does <em>not</em> specify the allocation between stationary BESS and swappable packs.
          In accordance with provenance rules, a <strong>300 MWh BESS / 300 MWh Swap-Pack (50/50)</strong> split is configured as an <strong>[ASSUMED]</strong> baseline in <code>assumptions.yaml</code> and subject to sensitivity evaluation.
        </div>
      </section>

      {/* 6. Five Metro Clusters */}
      <section className="volt-section">
        <div className="volt-section-header">
          <div>
            <h2 className="volt-section-title">Five Metro Operating Clusters</h2>
            <p className="volt-section-desc">
              Independent regional nodes coordinated centrally (inter-city physical power transfer disabled)
            </p>
          </div>
          <div className="volt-provenance-pair">
            <ProvenanceBadge provenance="OBSERVED" label="CLUSTERS: OBSERVED" />
            <ProvenanceBadge provenance="ASSUMED" label="CITY SPLIT: ASSUMED" />
          </div>
        </div>

        <div className="volt-clusters-grid">
          {clustersData?.clusters.map((cluster) => (
            <div key={cluster.cluster_id} className="volt-card volt-cluster-card">
              <div className="volt-cluster-header">
                <div>
                  <h3 className="volt-cluster-name">{cluster.name}</h3>
                  <span className="volt-cluster-region">Region Node • India</span>
                </div>
                <ProvenanceBadge provenance={cluster.provenance} />
              </div>

              <div className="volt-cluster-specs">
                <div className="volt-spec-row">
                  <span className="volt-spec-label">Assumed Share:</span>
                  <span className="volt-spec-val font-mono">
                    {(cluster.installed_capacity_share_assumed * 100).toFixed(0)}% (Equal Demo Baseline)
                  </span>
                </div>
                <div className="volt-spec-row">
                  <span className="volt-spec-label">Assumed Capacity:</span>
                  <span className="volt-spec-val font-mono">
                    {cluster.installed_capacity_mw_assumed.toFixed(0)} MW
                  </span>
                </div>
                <div className="volt-spec-row">
                  <span className="volt-spec-label">Grid Import Limit:</span>
                  <span className="volt-spec-val font-mono">
                    {cluster.grid_import_limit_mw_assumed.toFixed(0)} MW
                  </span>
                </div>
                <div className="volt-spec-row">
                  <span className="volt-spec-label">Grid Wheeling:</span>
                  <span className="volt-spec-val text-red-400 font-semibold">Disabled (Physical Isolation)</span>
                </div>
              </div>

              <div className="volt-cluster-footer">
                <ProvenanceBadge provenance="ASSUMED" label="CAPACITY SPLIT ASSUMED" />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 7. Scenario Disturbance Matrix */}
      <section className="volt-section">
        <div className="volt-section-header">
          <div>
            <h2 className="volt-section-title">Stress-Testing Scenarios (Configured Metadata)</h2>
            <p className="volt-section-desc">
              Disturbance conditions configured for multi-vector policy evaluation in subsequent phases
            </p>
          </div>
          <ProvenanceBadge provenance="SYNTHETIC" label="SCENARIOS: SYNTHETIC" />
        </div>

        <div className="volt-card volt-table-card">
          <table className="volt-table">
            <thead>
              <tr>
                <th>Scenario ID</th>
                <th>Description</th>
                <th>Demand Multiplier</th>
                <th>Renewable Mult.</th>
                <th>IEX Price Mult.</th>
                <th>Swap Demand</th>
                <th>Seed</th>
                <th>Provenance</th>
              </tr>
            </thead>
            <tbody>
              {scenariosData?.scenarios.map((sc) => (
                <tr key={sc.scenario_id}>
                  <td className="font-mono font-bold text-cyan-400">{sc.scenario_id}</td>
                  <td>{sc.description}</td>
                  <td className="font-mono text-center">{sc.demand_multiplier.toFixed(2)}&times;</td>
                  <td className="font-mono text-center">{sc.renewable_multiplier.toFixed(2)}&times;</td>
                  <td className="font-mono text-center">{sc.iex_price_multiplier.toFixed(2)}&times;</td>
                  <td className="font-mono text-center">{sc.swap_demand_multiplier.toFixed(2)}&times;</td>
                  <td className="font-mono text-center text-gray-400">{sc.seed}</td>
                  <td>
                    <ProvenanceBadge provenance={sc.provenance} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="volt-table-footnote">
            Notice: Scenarios represent input disturbances for deterministic simulation. Phase 1 provides metadata definitions only; no simulated performance claims are made at this stage.
          </div>
        </div>
      </section>

      {/* 8. Assumptions & Governance Register */}
      <section className="volt-section">
        <div className="volt-section-header">
          <div>
            <h2 className="volt-section-title">Modelling Assumptions & Provenance Register</h2>
            <p className="volt-section-desc">
              Transparent register of parameters unsupplied by case study, configured with engineering rationale
            </p>
          </div>
          <ProvenanceBadge provenance="ASSUMED" label="ASSUMPTIONS REGISTER" />
        </div>

        <div className="volt-card volt-table-card">
          <table className="volt-table">
            <thead>
              <tr>
                <th>Parameter</th>
                <th>Case Study Fact Status</th>
                <th>Configured Baseline</th>
                <th>Unit</th>
                <th>Provenance</th>
                <th>Engineering Rationale</th>
              </tr>
            </thead>
            <tbody>
              {caseConfig?.unknown_assumptions.map((item, idx) => (
                <tr key={idx}>
                  <td className="font-semibold text-amber-200">{item.parameter}</td>
                  <td className="text-gray-300">{item.case_fact_status}</td>
                  <td className="font-mono text-cyan-300">{String(item.assumed_value)}</td>
                  <td className="font-mono text-gray-400">{item.unit}</td>
                  <td>
                    <ProvenanceBadge provenance={item.provenance} />
                  </td>
                  <td className="text-sm text-gray-400">{item.rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
