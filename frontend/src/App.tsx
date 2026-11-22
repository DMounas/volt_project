import React, { useEffect, useState } from 'react';
import { fetchCaseConfig, fetchClusters, fetchHealth, fetchScenarios } from './api';
import { ComingSoonTab } from './components/ComingSoonTab';
import { Header } from './components/Header';
import { Navigation } from './components/Navigation';
import type { TabKey } from './components/Navigation';
import { OverviewTab } from './components/OverviewTab';
import type { CaseConfigResponse, ClustersResponse, HealthResponse, ScenariosResponse } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [caseConfig, setCaseConfig] = useState<CaseConfigResponse | null>(null);
  const [clustersData, setClustersData] = useState<ClustersResponse | null>(null);
  const [scenariosData, setScenariosData] = useState<ScenariosResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const [h, c, cl, sc] = await Promise.all([
          fetchHealth().catch(() => null),
          fetchCaseConfig().catch((e) => {
            console.warn('Could not load case config from API:', e);
            return null;
          }),
          fetchClusters().catch((e) => {
            console.warn('Could not load clusters from API:', e);
            return null;
          }),
          fetchScenarios().catch((e) => {
            console.warn('Could not load scenarios from API:', e);
            return null;
          }),
        ]);

        if (isMounted) {
          setHealth(h);
          setCaseConfig(c);
          setClustersData(cl);
          setScenariosData(sc);
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to initialize platform data');
          setLoading(false);
        }
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="volt-app">
      <Header health={health} loading={loading} />
      <Navigation activeTab={activeTab} onSelectTab={setActiveTab} />

      <main className="volt-main-content">
        {error && (
          <div className="volt-error-banner">
            <span>Connection Warning:</span> {error} (Falling back to local configuration specification)
          </div>
        )}

        {activeTab === 'overview' ? (
          <OverviewTab
            caseConfig={caseConfig}
            clustersData={clustersData}
            scenariosData={scenariosData}
          />
        ) : (
          <ComingSoonTab tab={activeTab} />
        )}
      </main>

      <footer className="volt-footer">
        <div className="volt-footer-inner">
          <div className="volt-footer-col">
            <span className="font-bold text-gray-200">VOLT Orchestration Platform</span>
            <span className="text-gray-400 text-xs">
              Virtual Orchestration of Load, Tariffs & Energy • Phase 1 Baseline
            </span>
          </div>
          <div className="volt-footer-col text-right">
            <span className="text-xs text-gray-400">
              Provenance Rules: OBSERVED (Case Facts) • ASSUMED (Model Inputs) • SYNTHETIC (Disturbances)
            </span>
            <span className="text-xs text-gray-500">Decision-Support Prototype • Asia/Kolkata</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
