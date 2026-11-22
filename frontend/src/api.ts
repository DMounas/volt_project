import type {
  BaselineCalibrationResponse,
  CaseConfigResponse,
  ClustersResponse,
  DataManifestResponse,
  ForecastMetricsResponse,
  ForecastResponse,
  ForecastSummaryResponse,
  HealthResponse,
  IEXDiagnosticsResponse,
  ScenariosResponse,
} from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchCaseConfig(): Promise<CaseConfigResponse> {
  const res = await fetch(`${API_BASE}/config/case`);
  if (!res.ok) throw new Error(`Failed to fetch case config: ${res.statusText}`);
  return res.json();
}

export async function fetchClusters(): Promise<ClustersResponse> {
  const res = await fetch(`${API_BASE}/clusters`);
  if (!res.ok) throw new Error(`Failed to fetch clusters: ${res.statusText}`);
  return res.json();
}

export async function fetchScenarios(): Promise<ScenariosResponse> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error(`Failed to fetch scenarios: ${res.statusText}`);
  return res.json();
}

export async function fetchDataManifest(): Promise<DataManifestResponse> {
  const res = await fetch(`${API_BASE}/data/manifest`);
  if (!res.ok) throw new Error(`Failed to fetch data manifest: ${res.statusText}`);
  return res.json();
}

export async function fetchBaselineCalibration(): Promise<BaselineCalibrationResponse> {
  const res = await fetch(`${API_BASE}/baseline/calibration`);
  if (!res.ok) throw new Error(`Failed to fetch baseline calibration: ${res.statusText}`);
  return res.json();
}

export async function fetchIEXDiagnostics(): Promise<IEXDiagnosticsResponse> {
  const res = await fetch(`${API_BASE}/data/iex/diagnostics`);
  if (!res.ok) throw new Error(`Failed to fetch IEX diagnostics: ${res.statusText}`);
  return res.json();
}

export async function fetchForecastSummary(): Promise<ForecastSummaryResponse> {
  const res = await fetch(`${API_BASE}/forecasts/summary`);
  if (!res.ok) throw new Error(`Failed to fetch forecast summary: ${res.statusText}`);
  return res.json();
}

export async function fetchLatestForecast(
  clusterId: string = 'delhi_ncr',
  targetName: string = 'fast_charge_demand_mwh'
): Promise<ForecastResponse> {
  const params = new URLSearchParams({ cluster_id: clusterId, target_name: targetName });
  const res = await fetch(`${API_BASE}/forecasts/latest?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch forecast: ${res.statusText}`);
  return res.json();
}

export async function runForecast(
  originTimestamp: string,
  clusterId: string = 'delhi_ncr',
  targetName: string = 'fast_charge_demand_mwh'
): Promise<ForecastResponse> {
  const res = await fetch(`${API_BASE}/forecasts/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      origin_timestamp: originTimestamp,
      cluster_id: clusterId,
      target_name: targetName,
    }),
  });
  if (!res.ok) throw new Error(`Forecast run failed: ${res.statusText}`);
  return res.json();
}

export async function fetchForecastMetrics(
  targetName?: string,
  clusterId?: string
): Promise<ForecastMetricsResponse> {
  const params = new URLSearchParams();
  if (targetName) params.append('target_name', targetName);
  if (clusterId) params.append('cluster_id', clusterId);
  const url = `${API_BASE}/forecasts/metrics${params.toString() ? `?${params.toString()}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch forecast metrics: ${res.statusText}`);
  return res.json();
}
