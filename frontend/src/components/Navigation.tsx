import React from 'react';

export type TabKey =
  | 'overview'
  | 'flexibility'
  | 'forecasts'
  | 'simulation'
  | 'optimization'
  | 'batteries'
  | 'reports';

interface Props {
  activeTab: TabKey;
  onSelectTab: (tab: TabKey) => void;
}

export const Navigation: React.FC<Props> = ({ activeTab, onSelectTab }) => {
  const tabs: { key: TabKey; label: string; phase: string; activePhase: boolean }[] = [
    { key: 'overview', label: 'Overview', phase: 'Phase 1 Active', activePhase: true },
    { key: 'flexibility', label: 'Customer Flexibility', phase: 'Phase 4 Active', activePhase: true },
    { key: 'forecasts', label: 'Forecasts', phase: 'Phase 3 Active', activePhase: true },
    { key: 'optimization', label: 'Optimization Decisions', phase: 'Phase 5 Active', activePhase: true },
    { key: 'simulation', label: 'Dispatch Simulation', phase: 'Phase 6', activePhase: false },
    { key: 'batteries', label: 'Battery Intelligence', phase: 'Phase 6', activePhase: false },
    { key: 'reports', label: 'Reports', phase: 'Phase 7', activePhase: false },
  ];

  return (
    <nav className="volt-nav">
      <div className="volt-nav-container">
        {tabs.map((tab) => {
          const isCurrent = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => onSelectTab(tab.key)}
              className={`volt-tab-btn ${isCurrent ? 'volt-tab-active' : ''}`}
            >
              <span className="volt-tab-title">{tab.label}</span>
              <span className={`volt-tab-phase ${tab.activePhase ? 'volt-phase-current' : 'volt-phase-future'}`}>
                {tab.phase}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
