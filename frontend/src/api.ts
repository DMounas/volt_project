import type {
  BaselineCalibrationResponse,
  CaseConfigResponse,
  ClustersResponse,
  DataManifestResponse,
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
