import React, { useEffect, useState } from 'react';
import {
  fetchBaselineCalibration,
  fetchCaseConfig,
  fetchClusters,
  fetchDataManifest,
  fetchHealth,
  fetchIEXDiagnostics,
  fetchScenarios,
} from './api';
import { ComingSoonTab } from './components/ComingSoonTab';
import { Header } from './components/Header';
import { Navigation } from './components/Navigation';
import type { TabKey } from './components/Navigation';
import { OverviewTab } from './components/OverviewTab';
import type {
  BaselineCalibrationResponse,
  CaseConfigResponse,
  ClustersResponse,
  DataManifestResponse,
  HealthResponse,
  IEXDiagnosticsResponse,
  ScenariosResponse,
} from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [caseConfig, setCaseConfig] = useState<CaseConfigResponse | null>(null);
  const [clustersData, setClustersData] = useState<ClustersResponse | null>(null);
  const [scenariosData, setScenariosData] = useState<ScenariosResponse | null>(null);
  const [manifest, setManifest] = useState<DataManifestResponse | null>(null);
  const [calibration, setCalibration] = useState<BaselineCalibrationResponse | null>(null);
  const [iexDiag, setIexDiag] = useState<IEXDiagnosticsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const [h, c, cl, sc, m, cal, iex] = await Promise.all([
          fetchHealth().catch(() => null),
          fetchCaseConfig().catch(() => null),
          fetchClusters().catch(() => null),
          fetchScenarios().catch(() => null),
          fetchDataManifest().catch(() => null),
          fetchBaselineCalibration().catch(() => null),
          fetchIEXDiagnostics().catch(() => null),
        ]);

        if (isMounted) {
          setHealth(h);
          setCaseConfig(c);
          setClustersData(cl);
          setScenariosData(sc);
          setManifest(m);
          setCalibration(cal);
          setIexDiag(iex);
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
            manifest={manifest}
            calibration={calibration}
            iexDiag={iexDiag}
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
              Virtual Orchestration of Load, Tariffs & Energy • Phase 2 Verified Baseline
            </span>
          </div>
          <div className="volt-footer-col text-right">
            <span className="text-xs text-gray-400">
              Provenance Rules: OBSERVED (Case Facts) • ASSUMED (Model Inputs) • SYNTHETIC (Disturbances) • SYNTHETIC_CALIBRATION (BAU)
            </span>
            <span className="text-xs text-gray-500">Decision-Support Prototype • Asia/Kolkata</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
