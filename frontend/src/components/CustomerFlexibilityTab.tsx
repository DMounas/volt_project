import React, { useEffect, useState } from 'react';
import {
  evaluateFlexibilityScenario,
  fetchCustomerSegments,
  fetchFlexibilityEnvelopes,
  fetchFlexibilityScenarios,
  fetchRequestsSummary,
  recommendTariff,
} from '../api';
import { ProvenanceBadge } from './ProvenanceBadge';
import type {
  CustomerRequestsSummaryResponse,
  CustomerSegmentsResponse,
  FlexibilityEnvelope,
  FlexibilityScenarioMetadata,
  ScenarioEvaluationResult,
  TariffRecommendation,
} from '../types';

export const CustomerFlexibilityTab: React.FC = () => {
  // State
  const [selectedCluster, setSelectedCluster] = useState<string>('all');
  const [selectedScenario, setSelectedScenario] = useState<string>('NORMAL');
  const [selectedModality, setSelectedModality] = useState<string>('all');
  const [simSeed, setSimSeed] = useState<number>(42);

  const [segmentsData, setSegmentsData] = useState<CustomerSegmentsResponse | null>(null);
  const [requestsSummary, setRequestsSummary] = useState<CustomerRequestsSummaryResponse | null>(null);
  const [scenarioCatalog, setScenarioCatalog] = useState<FlexibilityScenarioMetadata[]>([]);
  const [scenarioResult, setScenarioResult] = useState<ScenarioEvaluationResult | null>(null);
  const [envelopes, setEnvelopes] = useState<FlexibilityEnvelope[]>([]);
  const [tariffRec, setTariffRec] = useState<TariffRecommendation | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load initial static catalogs
  useEffect(() => {
    Promise.all([
      fetchCustomerSegments().catch(() => null),
      fetchRequestsSummary().catch(() => null),
      fetchFlexibilityScenarios().catch(() => null),
    ]).then(([segs, reqs, scs]) => {
      if (segs) setSegmentsData(segs);
      if (reqs) setRequestsSummary(reqs);
      if (scs) setScenarioCatalog(scs.scenarios);
    });
  }, []);

  // Run scenario evaluation and query envelopes when cluster/scenario/seed changes
  useEffect(() => {
    let isMounted = true;
    setEvaluating(true);
    setError(null);

    Promise.all([
      evaluateFlexibilityScenario(selectedScenario, selectedCluster, simSeed),
      fetchFlexibilityEnvelopes(
        selectedCluster,
        selectedModality !== 'all' ? selectedModality : undefined,
        undefined,
        0,
        30
      ),
      recommendTariff({
        cluster_id: selectedCluster !== 'all' ? selectedCluster : 'delhi_ncr',
        service_type: selectedModality === 'BATTERY_SWAP' ? 'BATTERY_SWAP' : 'FAST_CHARGE',
        previous_day_average_tariff_inr_per_kwh: 11.50,
        forecast_procurement_cost_inr_per_kwh: selectedScenario.includes('IEX') ? 11.44 : 5.20,
        forecast_demand_mw: selectedScenario.includes('CONGESTION') ? 220.0 : 160.0,
        available_capacity_mw: 240.0,
      }).catch(() => null),
    ])
      .then(([scRes, envRes, trf]) => {
        if (isMounted) {
          setScenarioResult(scRes);
          if (envRes) setEnvelopes(envRes.envelopes);
          if (trf) setTariffRec(trf);
          setLoading(false);
          setEvaluating(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to evaluate customer flexibility scenario');
          setLoading(false);
          setEvaluating(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedCluster, selectedScenario, selectedModality, simSeed]);

  const clusterOptions = [
    { id: 'all', name: 'All Metro Clusters' },
    { id: 'delhi_ncr', name: 'Delhi NCR' },
    { id: 'mumbai_mmr', name: 'Mumbai MMR' },
    { id: 'bengaluru', name: 'Bengaluru' },
    { id: 'hyderabad', name: 'Hyderabad' },
    { id: 'chennai', name: 'Chennai' },
  ];

  const getReasonBadgeClass = (reason: string) => {
    switch (reason) {
      case 'EMERGENCY_NON_SHIFTABLE':
        return 'badge-emergency';
      case 'PRIORITY_RESERVE_NON_SHIFTABLE':
        return 'badge-priority';
      case 'NOT_OPTED_IN':
        return 'badge-opt-out';
      case 'DEADLINE_CONSTRAINED':
        return 'badge-deadline';
      case 'PARTIALLY_FLEXIBLE':
        return 'badge-partial';
      case 'FLEXIBLE_WITHIN_WINDOW':
        return 'badge-flexible';
      default:
        return 'badge-default';
    }
  };

  return (
    <div className="volt-tab-container">
      {/* 1. Header Banner & Epistemic Disclosure */}
      <div className="volt-tab-header">
        <div className="volt-tab-header-main">
          <h2 className="volt-tab-title-text">
            Customer Service Windows, Demand Flexibility & Dynamic Tariffs
          </h2>
          <div className="volt-badge-row">
            <ProvenanceBadge provenance="SYNTHETIC" />
            <ProvenanceBadge provenance="ASSUMED" />
            <span className="volt-badge-phase">Phase 4 Active</span>
          </div>
        </div>
        <p className="volt-tab-desc">
          Evaluates deadline-constrained customer charging sessions, separates non-shiftable demand from
          voluntary flexible load, computes logistic acceptance probabilities, and enforces the regulatory
          dynamic tariff boundaries [0.80x–1.20x previous day average].
          {requestsSummary && (
            <span className="block mt-1 text-cyan-400 font-mono text-xs">
              Reconciled Disaggregated Requests: {requestsSummary.total_requests.toLocaleString()} sessions (
              {requestsSummary.total_fast_charge_mwh.toFixed(1)} MWh Fast Charge /{' '}
              {requestsSummary.total_swap_packs.toLocaleString()} Swap Packs) • Reconciliation{' '}
              {requestsSummary.reconciliation_passed ? 'PASSED (≤0.05% tolerance)' : 'FAILED'}
            </span>
          )}
        </p>
        <div className="volt-disclosure-box">
          <span className="font-semibold text-cyan-400">Epistemic Disclosure:</span> All customer requests,
          segment shares, opt-in rates, and logistic acceptance parameters are algorithmic synthetic models for
          engineering demonstration only. VOLT never delays emergency or priority fleet operations.
          Retail energy tariffs and voluntary flexibility incentives are decoupled accounting lines.
        </div>
      </div>

      {error && (
        <div className="volt-error-banner">
          <span>Simulation Warning:</span> {error}
        </div>
      )}

      {loading && (
        <div className="volt-card text-center py-8 text-cyan-400">
          <span className="text-sm font-semibold">Initializing customer flexibility intelligence & synthetic requests...</span>
        </div>
      )}

      {/* 2. Interactive Control Bar */}
      <div className="volt-card volt-control-bar">
        <div className="volt-control-grid">
          <div className="volt-control-group">
            <label className="volt-label">Metro Cluster Filter</label>
            <select
              value={selectedCluster}
              onChange={(e) => setSelectedCluster(e.target.value)}
              className="volt-select"
            >
              {clusterOptions.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div className="volt-control-group">
            <label className="volt-label">Flexibility & Disturbance Scenario</label>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              className="volt-select"
            >
              <option value="NORMAL">NORMAL — Baseline Operating Conditions</option>
              {scenarioCatalog.map((s) => (
                <option key={s.scenario_id} value={s.scenario_id}>
                  {s.scenario_id} — {s.name}
                </option>
              ))}
            </select>
          </div>

          <div className="volt-control-group">
            <label className="volt-label">Service Modality</label>
            <select
              value={selectedModality}
              onChange={(e) => setSelectedModality(e.target.value)}
              className="volt-select"
            >
              <option value="all">All Modalities (Fast Charge + Swap)</option>
              <option value="FAST_CHARGE">Fast Charging Only (kWh)</option>
              <option value="BATTERY_SWAP">Battery Swapping Only (Packs)</option>
            </select>
          </div>

          <div className="volt-control-group">
            <label className="volt-label">Monte Carlo Seed</label>
            <div className="flex gap-2">
              <input
                type="number"
                value={simSeed}
                onChange={(e) => setSimSeed(parseInt(e.target.value) || 42)}
                className="volt-input w-24"
              />
              <button
                onClick={() => setSimSeed((prev) => prev + 1)}
                className="volt-btn volt-btn-primary"
                title="Increment seed to simulate new stochastic realization"
              >
                Re-seed 🎲
              </button>
            </div>
          </div>
        </div>

        {evaluating && (
          <div className="text-xs text-cyan-400 mt-2 flex items-center gap-2">
            <span className="volt-spinner-sm"></span> Evaluating customer flexibility envelopes across requests...
          </div>
        )}
      </div>

      {/* 3. Demand Decomposition KPI Cards */}
      <div className="volt-metric-grid">
        <div className="volt-metric-card border-l-4 border-blue-500">
          <span className="volt-metric-label">Total Evaluated Demand</span>
          <span className="volt-metric-value text-blue-400">
            {scenarioResult ? `${(scenarioResult.total_demand_kwh / 1000).toFixed(2)} MWh` : '—'}
          </span>
          <span className="volt-metric-sub">
            {scenarioResult?.total_requests.toLocaleString() || '0'} active customer sessions
          </span>
        </div>

        <div className="volt-metric-card border-l-4 border-rose-500">
          <span className="volt-metric-label">Non-Shiftable Demand</span>
          <span className="volt-metric-value text-rose-400">
            {scenarioResult ? `${(scenarioResult.non_shiftable_demand_kwh / 1000).toFixed(2)} MWh` : '—'}
          </span>
          <span className="volt-metric-sub">
            {scenarioResult && scenarioResult.total_demand_kwh > 0
              ? `${((scenarioResult.non_shiftable_demand_kwh / scenarioResult.total_demand_kwh) * 100).toFixed(1)}% (Emergency + Non-Opt-in)`
              : '—'}
          </span>
        </div>

        <div className="volt-metric-card border-l-4 border-amber-500">
          <span className="volt-metric-label">Eligible Flexible Envelope</span>
          <span className="volt-metric-value text-amber-400">
            {scenarioResult ? `${(scenarioResult.eligible_flexible_demand_kwh / 1000).toFixed(2)} MWh` : '—'}
          </span>
          <span className="volt-metric-sub">
            {scenarioResult && scenarioResult.total_demand_kwh > 0
              ? `${((scenarioResult.eligible_flexible_demand_kwh / scenarioResult.total_demand_kwh) * 100).toFixed(1)}% of total demand`
              : '—'}
          </span>
        </div>

        <div className="volt-metric-card border-l-4 border-cyan-500">
          <span className="volt-metric-label">Opted-In Flexible Load</span>
          <span className="volt-metric-value text-cyan-400">
            {scenarioResult ? `${(scenarioResult.opted_in_demand_kwh / 1000).toFixed(2)} MWh` : '—'}
          </span>
          <span className="volt-metric-sub">
            Explicit voluntary consent given
          </span>
        </div>

        <div className="volt-metric-card border-l-4 border-emerald-500">
          <span className="volt-metric-label">Expected Accepted Shifting</span>
          <span className="volt-metric-value text-emerald-400">
            {scenarioResult ? `${(scenarioResult.expected_accepted_demand_kwh / 1000).toFixed(2)} MWh` : '—'}
          </span>
          <span className="volt-metric-sub">
            Realized (Seed {simSeed}): {scenarioResult ? `${(scenarioResult.realized_accepted_demand_kwh / 1000).toFixed(2)} MWh` : '—'}
          </span>
        </div>
      </div>

      {/* 4. Customer Segment Breakdown */}
      <div className="volt-card">
        <div className="volt-card-header">
          <h3 className="volt-card-title">Customer Segment Behavioral Profiles & Elasticity</h3>
          <span className="text-xs text-gray-400">Provenance: ASSUMED (Sensitivity Bands)</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mt-3">
          {segmentsData?.segments.map((seg) => {
            const segMetrics = scenarioResult?.segment_metrics[seg.segment];
            return (
              <div
                key={seg.segment}
                className={`p-4 rounded-lg border ${
                  seg.segment === 'EMERGENCY'
                    ? 'bg-rose-950/20 border-rose-800/40'
                    : seg.segment === 'PRIORITY_FLEET'
                    ? 'bg-amber-950/20 border-amber-800/40'
                    : 'bg-slate-900/50 border-slate-800'
                }`}
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold text-sm text-gray-200">{seg.segment}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-semibold ${
                      seg.is_shiftable
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/40'
                        : 'bg-rose-950 text-rose-400 border border-rose-800/40'
                    }`}
                  >
                    {seg.is_shiftable ? 'Shiftable' : 'Protected'}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mb-3">{seg.description}</p>
                <div className="text-xs space-y-1 text-gray-300">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Base Share:</span>
                    <span className="font-mono">{(seg.share_assumed * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Opt-In Rate:</span>
                    <span className="font-mono">{(seg.opt_in_rate_assumed * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Max Deferral:</span>
                    <span className="font-mono">{seg.max_deferral_minutes} min</span>
                  </div>
                  <div className="border-t border-slate-800 pt-2 mt-2">
                    <div className="flex justify-between text-cyan-400 font-semibold">
                      <span>Requests:</span>
                      <span>{segMetrics?.requests || 0}</span>
                    </div>
                    <div className="flex justify-between text-emerald-400 font-semibold">
                      <span>Accepted kWh:</span>
                      <span>{((segMetrics?.accepted_kwh || 0)).toFixed(0)}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 5. Dynamic Tariff Policy & Decoupled Financials */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Dynamic Tariff Policy */}
        <div className="volt-card">
          <div className="volt-card-header">
            <h3 className="volt-card-title">Dynamic Tariff Policy (Regulatory Bounded)</h3>
            <span className="text-xs text-cyan-400 font-semibold">Case Guardrail: [0.80x, 1.20x]</span>
          </div>
          <div className="mt-3 space-y-4">
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-3 bg-slate-900/60 rounded border border-slate-800">
                <span className="text-xs text-gray-400 block">Regulatory Floor (0.80x)</span>
                <span className="text-lg font-bold font-mono text-emerald-400">
                  ₹{tariffRec?.tariff_min_inr_per_kwh.toFixed(2) || '9.20'}/kWh
                </span>
              </div>
              <div className="p-3 bg-slate-900/60 rounded border border-cyan-800/40">
                <span className="text-xs text-cyan-400 block">Prev Day Reference</span>
                <span className="text-lg font-bold font-mono text-white">
                  ₹{tariffRec?.previous_day_average_tariff_inr_per_kwh.toFixed(2) || '11.50'}/kWh
                </span>
              </div>
              <div className="p-3 bg-slate-900/60 rounded border border-slate-800">
                <span className="text-xs text-gray-400 block">Regulatory Ceiling (1.20x)</span>
                <span className="text-lg font-bold font-mono text-rose-400">
                  ₹{tariffRec?.tariff_max_inr_per_kwh.toFixed(2) || '13.80'}/kWh
                </span>
              </div>
            </div>

            <div className="p-4 bg-slate-950/70 rounded-lg border border-slate-800 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-300">Raw Unconstrained Tariff Recommendation:</span>
                <span className="font-mono text-base font-semibold text-gray-200">
                  ₹{tariffRec?.raw_tariff_inr_per_kwh.toFixed(2) || '11.50'}/kWh
                </span>
              </div>
              <div className="flex justify-between items-center pt-2 border-t border-slate-800">
                <span className="text-sm font-bold text-white">Final Bounded Retail Tariff:</span>
                <span className="font-mono text-xl font-bold text-cyan-400">
                  ₹{tariffRec?.final_tariff_inr_per_kwh.toFixed(2) || '11.50'}/kWh
                </span>
              </div>
              <div className="flex items-center gap-2 pt-1">
                <span className="text-xs text-gray-400">Clamping State:</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded font-bold ${
                    tariffRec?.clamped
                      ? 'bg-amber-950 text-amber-400 border border-amber-800/50'
                      : 'bg-emerald-950 text-emerald-400 border border-emerald-800/50'
                  }`}
                >
                  {tariffRec?.clamping_direction === 'NONE'
                    ? 'Within [0.80x, 1.20x] Band'
                    : `Clamped to ${tariffRec?.clamping_direction}`}
                </span>
              </div>
            </div>

            {tariffRec?.adjustment_reasons && (
              <div className="text-xs text-gray-400 space-y-1">
                <span className="font-semibold text-gray-300">Adjustment Policy Audit Log:</span>
                <ul className="list-disc list-inside space-y-0.5 text-slate-400">
                  {tariffRec.adjustment_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Right: Decoupled Accounting & Service Quality */}
        <div className="volt-card">
          <div className="volt-card-header">
            <h3 className="volt-card-title">Decoupled Financial Accounting & Service Quality</h3>
            <span className="text-xs text-emerald-400 font-semibold">Strict Separation Guardrail</span>
          </div>
          <div className="mt-3 space-y-4">
            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="p-3 bg-slate-900/60 rounded border border-slate-800">
                <span className="text-xs text-gray-400 block">Retail Tariff Revenue</span>
                <span className="text-lg font-bold font-mono text-cyan-400">
                  ₹{scenarioResult ? (scenarioResult.total_retail_revenue_inr / 1000).toFixed(1) : '0.0'}k
                </span>
                <span className="text-[10px] text-gray-500 block">Customer Energy Billing</span>
              </div>
              <div className="p-3 bg-slate-900/60 rounded border border-slate-800">
                <span className="text-xs text-gray-400 block">Separate Incentive Expense</span>
                <span className="text-lg font-bold font-mono text-amber-400">
                  ₹{scenarioResult ? (scenarioResult.total_incentive_cost_inr / 1000).toFixed(1) : '0.0'}k
                </span>
                <span className="text-[10px] text-gray-500 block">Voluntary Operating Cost</span>
              </div>
            </div>

            <div className="p-3 bg-cyan-950/20 border border-cyan-800/30 rounded text-xs text-cyan-300">
              <span className="font-bold">Decoupling Invariant:</span> Flexibility incentives are paid
              separately as operational expenses and are NEVER blended into the retail tariff as a single discount.
              This prevents double-counting savings in future Phase 5 optimization.
            </div>

            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800 text-center">
              <div className="p-2 bg-slate-950 rounded">
                <span className="text-[11px] text-gray-400 block">Deadline Violations</span>
                <span className="text-base font-bold text-emerald-400">
                  {scenarioResult?.deadline_violations || 0}
                </span>
                <span className="text-[10px] text-gray-500 block">100% Guaranteed</span>
              </div>
              <div className="p-2 bg-slate-950 rounded">
                <span className="text-[11px] text-gray-400 block">Priority Protected</span>
                <span className="text-base font-bold text-blue-400">
                  {scenarioResult?.protected_priority_requests || 0} reqs
                </span>
                <span className="text-[10px] text-gray-500 block">5% Reserve Safe</span>
              </div>
              <div className="p-2 bg-slate-950 rounded">
                <span className="text-[11px] text-gray-400 block">Avg Wait Time</span>
                <span className="text-base font-bold text-slate-200">
                  {scenarioResult?.average_wait_minutes || 0} min
                </span>
                <span className="text-[10px] text-gray-500 block">Across Fleet</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 6. Request Inspector & Flexibility Window Explorer */}
      <div className="volt-card">
        <div className="volt-card-header">
          <h3 className="volt-card-title">Customer Request Inspector & Service Window Envelopes</h3>
          <span className="text-xs text-gray-400">
            Showing candidate sessions with explainable reason codes
          </span>
        </div>
        <div className="overflow-x-auto mt-3">
          <table className="volt-table w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-gray-400">
                <th className="py-2 px-3">Request ID</th>
                <th className="py-2 px-3">Cluster</th>
                <th className="py-2 px-3">Modality</th>
                <th className="py-2 px-3">Segment</th>
                <th className="py-2 px-3 text-right">Requested</th>
                <th className="py-2 px-3 text-right">Non-Shiftable</th>
                <th className="py-2 px-3 text-right">Flexible</th>
                <th className="py-2 px-3 text-center">Opt-In</th>
                <th className="py-2 px-3">Service Window & Reason Code</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {envelopes.slice(0, 15).map((env) => (
                <tr key={env.request_id} className="hover:bg-slate-900/40">
                  <td className="py-2 px-3 font-semibold text-cyan-400">{env.request_id}</td>
                  <td className="py-2 px-3 capitalize text-gray-300">{env.cluster_id.replace('_', ' ')}</td>
                  <td className="py-2 px-3">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] ${
                        env.request_type === 'FAST_CHARGE'
                          ? 'bg-blue-950 text-blue-300'
                          : 'bg-purple-950 text-purple-300'
                      }`}
                    >
                      {env.request_type === 'FAST_CHARGE' ? 'Fast Charge' : 'Battery Swap'}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-gray-300">{env.customer_segment}</td>
                  <td className="py-2 px-3 text-right text-white">
                    {env.request_type === 'FAST_CHARGE'
                      ? `${env.requested_energy_kwh.toFixed(1)} kWh`
                      : `${env.requested_pack_count || 1} packs`}
                  </td>
                  <td className="py-2 px-3 text-right text-rose-400">
                    {env.request_type === 'FAST_CHARGE'
                      ? `${env.non_shiftable_energy_kwh.toFixed(1)} kWh`
                      : `${env.non_shiftable_pack_count || 0} packs`}
                  </td>
                  <td className="py-2 px-3 text-right text-emerald-400">
                    {env.request_type === 'FAST_CHARGE'
                      ? `${env.flexible_energy_kwh.toFixed(1)} kWh`
                      : `${env.flexible_pack_count || 0} packs`}
                  </td>
                  <td className="py-2 px-3 text-center">
                    {env.flexibility_opt_in ? (
                      <span className="text-emerald-400 font-bold">✓</span>
                    ) : (
                      <span className="text-gray-600">✗</span>
                    )}
                  </td>
                  <td className="py-2 px-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${getReasonBadgeClass(
                        env.reason_code
                      )}`}
                    >
                      {env.reason_code}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
