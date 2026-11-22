import type { CaseConfigResponse, ClustersResponse, HealthResponse, ScenariosResponse } from './types';

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
