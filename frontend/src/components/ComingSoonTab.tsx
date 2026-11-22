import React from 'react';
import type { TabKey } from './Navigation';

interface Props {
  tab: TabKey;
}

const TAB_INFO: Record<Exclude<TabKey, 'overview'>, {
  title: string;
  phase: string;
  description: string;
  deliverables: string[];
  safeguard: string;
}> = {
  simulation: {
    title: 'Live Digital-Twin Simulation',
    phase: 'Phase 4 & Phase 6',
    description: 'Simulates hourly state transitions across charging dispensers, swap bays, stationary BESS, and grid interconnection under disturbance scenarios.',
    deliverables: [
      'Hourly discrete-event execution of direct charging and battery-swap sessions',
      'Dynamic power balance: Solar/Wind + DISCOM + IEX + BESS discharge = Loads + Losses',
      'Battery degradation wear accumulation and SOH degradation tracking',
      'Evaluation against reconstructed business-as-usual and price-only heuristics',
    ],
    safeguard: 'Will not fabricate live hardware telemetry. Simulation outputs will carry strict SYNTHETIC provenance tags.',
  },
  forecasts: {
    title: 'Predictive Intelligence & Market Forecasts',
    phase: 'Phase 3',
    description: 'Probabilistic time series forecasts for fast-charging demand, swap requests, open-access renewable generation, and IEX market prices.',
    deliverables: [
      'P10, P50, and P90 quantile forecasts for hourly energy demand and pack swap counts',
      'Day-Ahead and Real-Time IEX market clearing price distribution models',
      'Chronological rolling-origin backtesting against seasonal-naive baselines',
      'Weather-integrated renewable generation forecasting (solar irradiance and wind speed)',
    ],
    safeguard: 'Evaluated chronologically without random train/test data leakage. Quantile pinball loss and MAE/WAPE metrics will be reported by city.',
  },
  optimization: {
    title: 'Optimization Decisions & Explainability',
    phase: 'Phase 5',
    description: 'Risk-aware Mixed-Integer Linear Program (MILP) co-optimizing procurement, storage dispatch, customer flexibility, and dynamic pricing.',
    deliverables: [
      'HiGHS / Pyomo MILP formulation with CVaR tail-risk penalty',
      'Hourly procurement decisions across contracted renewables, DISCOMs, and IEX',
      'Why This Decision? panel showing active binding constraints and cost deltas',
      'Deterministic safe heuristic fallback triggered on timeout or infeasibility',
    ],
    safeguard: 'Zero fabricated schedules. Infeasibility or fallback status will be surfaced transparently in the decision audit trail.',
  },
  batteries: {
    title: 'Battery Intelligence & Inventory Passport',
    phase: 'Phase 4',
    description: 'Decoupled state estimator and asset tracker distinguishing stationary grid BESS from commercial swappable battery pack inventory.',
    deliverables: [
      'Stationary BESS: Hourly SOC trajectory, charge/discharge power, and cycle throughput',
      'Swap-Pack Cohorts: Ready, charging, depleted, maintenance, and emergency reserve counts',
      'Battery passport metadata tracking pack-level SOH and degradation wear',
      'Strict separation: Swap packs never discharge to the utility grid',
    ],
    safeguard: 'Stationary BESS power rating is decoupled from MWh storage capacity. 5% emergency reserve remains strictly uncommitted.',
  },
  reports: {
    title: 'Benchmark Reports & Sensitivity Analysis',
    phase: 'Phase 7 & Phase 8',
    description: 'Auditable policy benchmark comparisons, ablation studies, and sensitivity tests on unsupplied assumptions.',
    deliverables: [
      'Apples-to-apples comparison across Baseline, Price-Only, Deterministic MILP, and VOLT Proposed policies',
      'Cluster-by-cluster EBITDA margin breakdown (operating margin proxy)',
      'Sensitivity analysis on city capacity shares, 600 MWh asset split, and degradation cost curves',
      'Reproducible evidence pack for judges with fixed scenario seeds',
    ],
    safeguard: 'No claim of hitting 89.7% reliability or 8% loss targets will be made until backed by reproducible multi-scenario simulation runs.',
  },
};

export const ComingSoonTab: React.FC<Props> = ({ tab }) => {
  if (tab === 'overview') return null;

  const info = TAB_INFO[tab];

  return (
    <div className="volt-coming-soon-container">
      <div className="volt-card volt-coming-soon-card">
        <div className="volt-coming-soon-badge">
          <span>{info.phase}</span>
          <span className="volt-badge-muted">Scheduled Implementation</span>
        </div>

        <h2 className="volt-coming-soon-title">{info.title}</h2>
        <p className="volt-coming-soon-desc">{info.description}</p>

        <div className="volt-coming-soon-section">
          <h3 className="volt-subheading">Planned Core Deliverables:</h3>
          <ul className="volt-feature-list">
            {info.deliverables.map((item, idx) => (
              <li key={idx} className="volt-feature-item">
                <span className="volt-check-icon">▹</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="volt-coming-soon-safeguard">
          <span className="volt-safeguard-tag">Phase 1 Architecture Boundary:</span>
          <p>{info.safeguard}</p>
        </div>
      </div>
    </div>
  );
};
