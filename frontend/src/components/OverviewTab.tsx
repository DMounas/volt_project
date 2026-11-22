import React from 'react';
import type { CaseConfigResponse, ClustersResponse, ScenariosResponse } from '../types';
import { ProvenanceBadge } from './ProvenanceBadge';

interface Props {
  caseConfig: CaseConfigResponse | null;
  clustersData: ClustersResponse | null;
  scenariosData: ScenariosResponse | null;
}

export const OverviewTab: React.FC<Props> = ({
  caseConfig,
  clustersData,
  scenariosData,
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

      {/* 3. System Capacity & Modality Mix */}
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

      {/* 4. Five Metro Clusters */}
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

      {/* 5. Scenario Disturbance Matrix */}
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

      {/* 6. Assumptions & Governance Register */}
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
