import React, { useEffect, useState } from 'react';
import { fetchForecastMetrics, fetchForecastSummary, fetchLatestForecast } from '../api';
import { ProvenanceBadge } from './ProvenanceBadge';
import type { ForecastMetricsResponse, ForecastResponse, ForecastSummaryResponse } from '../types';

export const ForecastsTab: React.FC = () => {
  const [summary, setSummary] = useState<ForecastSummaryResponse | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<string>('delhi_ncr');
  const [selectedTarget, setSelectedTarget] = useState<string>('fast_charge_demand_mwh');
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [metrics, setMetrics] = useState<ForecastMetricsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Load summary on mount
  useEffect(() => {
    fetchForecastSummary()
      .then((s) => setSummary(s))
      .catch((err) => console.warn('Could not load forecast summary:', err));
  }, []);

  // Load forecast & metrics when cluster or target changes
  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    // If IEX price is selected, force cluster to national
    const effectiveCluster = selectedTarget === 'iex_clearing_price_inr_mwh' ? 'national' : selectedCluster;

    Promise.all([
      fetchLatestForecast(effectiveCluster, selectedTarget),
      fetchForecastMetrics(selectedTarget, effectiveCluster).catch(() => null),
    ])
      .then(([fc, met]) => {
        if (isMounted) {
          setForecast(fc);
          setMetrics(met);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load forecast data');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedCluster, selectedTarget]);

  // Target label mapper
  const targetLabels: Record<string, { label: string; unit: string; desc: string }> = {
    fast_charge_demand_mwh: {
      label: 'Fast-Charging Demand',
      unit: 'MWh',
      desc: 'Cluster hourly commercial EV fast-charging energy requirement',
    },
    swap_demand_mwh: {
      label: 'Battery Swap Demand',
      unit: 'MWh',
      desc: 'Cluster hourly swappable battery pack energy demand',
    },
    solar_available_mwh: {
      label: 'Solar Availability',
      unit: 'MWh',
      desc: 'Cluster open-access solar farm hourly generation potential',
    },
    wind_available_mwh: {
      label: 'Wind Availability',
      unit: 'MWh',
      desc: 'Cluster open-access wind turbine hourly generation potential',
    },
    iex_clearing_price_inr_mwh: {
      label: 'IEX DAM Market Price',
      unit: 'INR/MWh',
      desc: 'National Indian Energy Exchange Day-Ahead Market clearing price',
    },
  };

  const clusterLabels: Record<string, string> = {
    delhi_ncr: 'Delhi NCR',
    mumbai_mmr: 'Mumbai MMR',
    bengaluru: 'Bengaluru',
    hyderabad: 'Hyderabad',
    chennai: 'Chennai',
    national: 'National Market',
  };

  // Find target metric report if available
  const reportKey = `${selectedTarget}_${selectedTarget === 'iex_clearing_price_inr_mwh' ? 'national' : selectedCluster}`;
  const targetReport = metrics?.metrics?.[reportKey];

  // Helper for rendering SVG forecast chart
  const renderForecastChart = () => {
    if (!forecast || !forecast.horizons || forecast.horizons.length === 0) {
      return null;
    }

    const horizons = forecast.horizons;
    const maxVal = Math.max(...horizons.map((h) => h.p90), 10.0) * 1.15;
    const minVal = 0.0;

    const width = 800;
    const height = 260;
    const padLeft = 60;
    const padRight = 30;
    const padTop = 20;
    const padBottom = 35;
    const plotWidth = width - padLeft - padRight;
    const plotHeight = height - padTop - padBottom;

    const getX = (idx: number) => padLeft + (idx / (horizons.length - 1)) * plotWidth;
    const getY = (val: number) => padTop + plotHeight - ((val - minVal) / (maxVal - minVal)) * plotHeight;

    // Build shaded P10-P90 polygon points
    const topPoints = horizons.map((h, i) => `${getX(i)},${getY(h.p90)}`).join(' ');
    const bottomPoints = [...horizons]
      .reverse()
      .map((h, i) => `${getX(horizons.length - 1 - i)},${getY(h.p10)}`)
      .join(' ');
    const polygonPath = `${topPoints} ${bottomPoints}`;

    // Build P50 line
    const p50Path = horizons.map((h, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(h.p50)}`).join(' ');

    return (
      <div className="w-full overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto bg-slate-900/60 rounded-lg p-2">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((ratio) => {
            const val = minVal + ratio * (maxVal - minVal);
            const y = getY(val);
            return (
              <g key={ratio}>
                <line x1={padLeft} y1={y} x2={width - padRight} y2={y} stroke="#334155" strokeDasharray="3 3" />
                <text x={padLeft - 8} y={y + 4} textAnchor="end" fill="#94a3b8" fontSize="10">
                  {val.toFixed(val >= 1000 ? 0 : 1)}
                </text>
              </g>
            );
          })}

          {/* Shaded P10-P90 uncertainty confidence band */}
          <polygon points={polygonPath} fill="#0284c7" fillOpacity="0.22" stroke="#0284c7" strokeWidth="1" strokeDasharray="2 2" />

          {/* Central P50 median curve */}
          <path d={p50Path} fill="none" stroke="#38bdf8" strokeWidth="2.5" />

          {/* Horizon step markers */}
          {horizons.map((h, i) => (
            <g key={i}>
              <circle cx={getX(i)} cy={getY(h.p50)} r="3.5" fill="#38bdf8" stroke="#0f172a" strokeWidth="1.5" />
              {i % 3 === 0 && (
                <text x={getX(i)} y={height - padBottom + 18} textAnchor="middle" fill="#94a3b8" fontSize="10">
                  +{h.horizon_hour}h
                </text>
              )}
            </g>
          ))}

          {/* Y-Axis Label */}
          <text x={18} y={height / 2} textAnchor="middle" fill="#cbd5e1" fontSize="11" transform={`rotate(-90 18 ${height / 2})`}>
            {forecast.target_unit}
          </text>
        </svg>

        {/* Legend */}
        <div className="flex items-center justify-center gap-6 mt-2 text-xs text-slate-300">
          <div className="flex items-center gap-2">
            <span className="w-4 h-1 bg-[#38bdf8] rounded"></span>
            <span className="font-semibold text-sky-400">P50 Central Forecast (Median)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-3 bg-sky-600/30 border border-sky-400/60 rounded"></span>
            <span>P10–P90 Calibrated Uncertainty Band (80% Interval)</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header Banner & Epistemic Disclosure */}
      <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-5 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-white tracking-wide">Probabilistic Multi-Vector Forecasting (Phase 3)</h2>
              <ProvenanceBadge provenance="SYNTHETIC" />
            </div>
            <p className="text-slate-400 text-sm mt-1">
              Rolling 24-hour ahead quantile predictions (P10, P50, P90) with non-crossing monotonicity and seasonal-naive benchmarking.
              {summary && ` (${summary.total_models_trained} trained quantile model instances active across clusters).`}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-sky-950/70 border border-sky-600/50 text-sky-300 text-xs rounded-full font-mono">
              Model: HistGradientBoosting
            </span>
            <span className="px-3 py-1 bg-emerald-950/70 border border-emerald-600/50 text-emerald-300 text-xs rounded-full font-mono">
              Test: 2025 Untouched Split
            </span>
          </div>
        </div>
      </div>

      {/* Target & Cluster Selectors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Target Selector */}
        <div className="bg-slate-800/60 border border-slate-700/80 rounded-xl p-4">
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Forecast Vector / Target Variable
          </label>
          <select
            value={selectedTarget}
            onChange={(e) => setSelectedTarget(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-sky-500"
          >
            {Object.entries(targetLabels).map(([key, info]) => (
              <option key={key} value={key}>
                {info.label} ({info.unit})
              </option>
            ))}
          </select>
          <p className="text-xs text-slate-400 mt-2 italic">{targetLabels[selectedTarget]?.desc}</p>
        </div>

        {/* Cluster Selector */}
        <div className="bg-slate-800/60 border border-slate-700/80 rounded-xl p-4">
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Operational Cluster / Market Area
          </label>
          <select
            value={selectedTarget === 'iex_clearing_price_inr_mwh' ? 'national' : selectedCluster}
            disabled={selectedTarget === 'iex_clearing_price_inr_mwh'}
            onChange={(e) => setSelectedCluster(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 text-slate-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-sky-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {selectedTarget === 'iex_clearing_price_inr_mwh' ? (
              <option value="national">National Market (Single Uniform Price Area)</option>
            ) : (
              Object.entries(clusterLabels)
                .filter(([k]) => k !== 'national')
                .map(([k, label]) => (
                  <option key={k} value={k}>
                    {label}
                  </option>
                ))
            )}
          </select>
          <p className="text-xs text-slate-400 mt-2">
            {selectedTarget === 'iex_clearing_price_inr_mwh'
              ? 'IEX Day-Ahead clearing price is unified across national synchronous grid'
              : 'Cluster-level isolated node dispatch'}
          </p>
        </div>
      </div>

      {/* Loading or Error State */}
      {loading && (
        <div className="bg-slate-800/40 border border-slate-700 rounded-xl p-8 text-center text-slate-300">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-sky-400 mb-2"></div>
          <div>Loading forecast model artifacts and 24-hour trajectories...</div>
        </div>
      )}

      {error && !loading && (
        <div className="bg-red-950/40 border border-red-700 text-red-300 p-4 rounded-xl text-sm">
          <strong>Forecast Load Warning:</strong> {error}
        </div>
      )}

      {/* Main Forecast Visualization */}
      {!loading && forecast && (
        <div className="bg-slate-800/70 border border-slate-700 rounded-xl p-5 shadow-lg space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-700/60 pb-3 gap-2">
            <div>
              <h3 className="text-lg font-bold text-slate-100">
                24-Hour Probabilistic Trajectory — {forecast.target_display_name}
              </h3>
              <p className="text-xs text-slate-400">
                Forecast Origin: <span className="font-mono text-slate-200">{forecast.origin_timestamp}</span> (Asia/Kolkata)
              </p>
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-2">
              <span>Unit:</span>
              <span className="font-bold text-sky-400">{forecast.target_unit}</span>
            </div>
          </div>

          {/* SVG Chart */}
          {renderForecastChart()}

          {/* Evaluation Metrics Cards (Untouched 2025 Test Split) */}
          {targetReport && (
            <div className="pt-4 border-t border-slate-700/60">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                  Out-Of-Sample Benchmark vs. Incumbent Baseline (2025 Test Set)
                </span>
                <span className="text-xs text-slate-400 font-mono">Evaluation: {targetReport.evaluation_split}</span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-700/60">
                  <div className="text-slate-400 text-xs">Model P50 MAE</div>
                  <div className="text-base font-bold text-sky-400 mt-1">
                    {targetReport.overall_mae} <span className="text-xs font-normal text-slate-400">{forecast.target_unit}</span>
                  </div>
                </div>

                <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-700/60">
                  <div className="text-slate-400 text-xs">Baseline MAE</div>
                  <div className="text-base font-bold text-slate-300 mt-1">
                    {targetReport.baseline_mae} <span className="text-xs font-normal text-slate-400">{forecast.target_unit}</span>
                  </div>
                  <div className="text-[10px] text-slate-500">{targetReport.baseline_name}</div>
                </div>

                <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-700/60">
                  <div className="text-slate-400 text-xs">MAE Improvement</div>
                  <div
                    className={`text-base font-bold mt-1 ${targetReport.mae_improvement_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}
                  >
                    {targetReport.mae_improvement_pct >= 0 ? '+' : ''}
                    {targetReport.mae_improvement_pct}%
                  </div>
                  <div className="text-[10px] text-slate-500">vs. same hour yesterday</div>
                </div>

                <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-700/60">
                  <div className="text-slate-400 text-xs">P10–P90 Coverage</div>
                  <div className="text-base font-bold text-indigo-400 mt-1">{targetReport.coverage_p10_p90_pct}%</div>
                  <div className="text-[10px] text-slate-500">Nominal target: 80%</div>
                </div>

                <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-700/60">
                  <div className="text-slate-400 text-xs">Mean Interval Width</div>
                  <div className="text-base font-bold text-slate-200 mt-1">
                    {targetReport.mean_interval_width} <span className="text-xs font-normal text-slate-400">{forecast.target_unit}</span>
                  </div>
                  <div className="text-[10px] text-slate-500">Sharpness indicator</div>
                </div>

                <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-700/60">
                  <div className="text-slate-400 text-xs">WAPE Error</div>
                  <div className="text-base font-bold text-amber-400 mt-1">{targetReport.overall_wape_pct}%</div>
                  <div className="text-[10px] text-slate-500">Weighted percentage</div>
                </div>
              </div>

              {/* Horizon Stratification Table */}
              {targetReport.horizon_buckets && Object.keys(targetReport.horizon_buckets).length > 0 && (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-left text-xs border border-slate-700/70 rounded-lg overflow-hidden">
                    <thead className="bg-slate-900/90 text-slate-400 font-semibold uppercase">
                      <tr>
                        <th className="py-2 px-3">Horizon Bucket</th>
                        <th className="py-2 px-3">Lead Time</th>
                        <th className="py-2 px-3">MAE ({forecast.target_unit})</th>
                        <th className="py-2 px-3">Baseline MAE</th>
                        <th className="py-2 px-3">Improvement</th>
                        <th className="py-2 px-3">Mean Pinball Loss</th>
                        <th className="py-2 px-3">P10–P90 Coverage</th>
                        <th className="py-2 px-3">Interval Width</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-slate-300">
                      {Object.entries(targetReport.horizon_buckets).map(([k, b]: [string, any]) => (
                        <tr key={k} className="hover:bg-slate-800/40">
                          <td className="py-2 px-3 font-semibold text-slate-200 capitalize">{b.bucket_name.replace('_', ' ')}</td>
                          <td className="py-2 px-3 font-mono text-sky-400">{b.horizon_range}</td>
                          <td className="py-2 px-3 font-bold text-slate-100">{b.mae}</td>
                          <td className="py-2 px-3 text-slate-400">{b.baseline_mae ?? '—'}</td>
                          <td className="py-2 px-3 font-bold text-emerald-400">
                            {b.mae_improvement_pct != null ? `+${b.mae_improvement_pct}%` : '—'}
                          </td>
                          <td className="py-2 px-3 text-slate-300">{b.mean_pinball}</td>
                          <td className="py-2 px-3 font-semibold text-indigo-300">{b.coverage_p10_p90_pct}%</td>
                          <td className="py-2 px-3 text-slate-300">{b.mean_interval_width}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* 24-Step Hourly Trajectory Table */}
          <div className="pt-4 border-t border-slate-700/60">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
              Hourly Trajectory Details (P10, P50, P90)
            </h4>
            <div className="max-h-56 overflow-y-auto border border-slate-700/60 rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900 sticky top-0 text-slate-400 font-semibold uppercase">
                  <tr>
                    <th className="py-2 px-3">Horizon</th>
                    <th className="py-2 px-3">Target Time (IST)</th>
                    <th className="py-2 px-3 text-right">P10 (10th %ile)</th>
                    <th className="py-2 px-3 text-right text-sky-400 font-bold">P50 (Median)</th>
                    <th className="py-2 px-3 text-right">P90 (90th %ile)</th>
                    <th className="py-2 px-3 text-right text-slate-400">Spread (P90-P10)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 text-slate-300">
                  {forecast.horizons.map((h) => {
                    const spread = (h.p90 - h.p10).toFixed(2);
                    return (
                      <tr key={h.horizon_hour} className="hover:bg-slate-800/40">
                        <td className="py-1.5 px-3 font-mono font-bold text-slate-200">+{h.horizon_hour}h</td>
                        <td className="py-1.5 px-3 font-mono text-slate-400">{h.target_timestamp}</td>
                        <td className="py-1.5 px-3 text-right font-mono text-slate-300">{h.p10.toFixed(2)}</td>
                        <td className="py-1.5 px-3 text-right font-mono font-bold text-sky-400">{h.p50.toFixed(2)}</td>
                        <td className="py-1.5 px-3 text-right font-mono text-slate-300">{h.p90.toFixed(2)}</td>
                        <td className="py-1.5 px-3 text-right font-mono text-slate-500">{spread}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
