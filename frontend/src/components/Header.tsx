import React from 'react';
import type { HealthResponse } from '../types';

interface Props {
  health: HealthResponse | null;
  loading: boolean;
}

export const Header: React.FC<Props> = ({ health, loading }) => {
  return (
    <header className="volt-header">
      <div className="volt-header-inner">
        <div className="volt-brand">
          <div className="volt-logo-icon">⚡</div>
          <div>
            <div className="volt-title-row">
              <h1 className="volt-main-title">VOLT — Energy Orchestration</h1>
              <span className="volt-badge-prototype">Phase 1 Foundation</span>
            </div>
            <p className="volt-subtitle">
              Decision-Support Digital Twin • Five-City EV Fast-Charging & Battery-Swapping Network
            </p>
          </div>
        </div>

        <div className="volt-header-meta">
          <div className="volt-status-pill">
            <span
              className={`volt-indicator ${
                loading ? 'volt-indicator-loading' : health ? 'volt-indicator-live' : 'volt-indicator-offline'
              }`}
            />
            <span className="volt-meta-text">
              {loading ? 'Connecting API...' : health ? 'API Online' : 'Local Fallback'}
            </span>
          </div>

          <div className="volt-meta-item">
            <span className="volt-meta-label">Timezone:</span>
            <span className="volt-meta-value">Asia/Kolkata (IST)</span>
          </div>

          <div className="volt-meta-item">
            <span className="volt-meta-label">Version:</span>
            <span className="volt-meta-value">v0.1.0</span>
          </div>
        </div>
      </div>
    </header>
  );
};
