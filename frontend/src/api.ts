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

// ==========================================
// Phase 4: Customer Flexibility API Endpoints
// ==========================================
import type {
  CustomerRequestsSummaryResponse,
  CustomerSegmentsResponse,
  FlexibilityEnvelopesResponse,
  FlexibilityScenariosResponse,
  FlexibilitySummaryResponse,
  IncentivesSummaryResponse,
  ScenarioEvaluationResult,
  TariffRecommendation,
} from './types';

export async function fetchCustomerSegments(): Promise<CustomerSegmentsResponse> {
  const res = await fetch(`${API_BASE}/customers/segments`);
  if (!res.ok) throw new Error(`Failed to fetch customer segments: ${res.statusText}`);
  return res.json();
}

export async function fetchRequestsSummary(): Promise<CustomerRequestsSummaryResponse> {
  const res = await fetch(`${API_BASE}/customers/requests/summary`);
  if (!res.ok) throw new Error(`Failed to fetch customer requests summary: ${res.statusText}`);
  return res.json();
}

export async function fetchFlexibilitySummary(clusterId?: string): Promise<FlexibilitySummaryResponse> {
  const params = new URLSearchParams();
  if (clusterId && clusterId.toLowerCase() !== 'all') params.append('cluster_id', clusterId);
  const url = `${API_BASE}/flexibility/summary${params.toString() ? `?${params.toString()}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch flexibility summary: ${res.statusText}`);
  return res.json();
}

export async function fetchFlexibilityEnvelopes(
  clusterId?: string,
  modality?: string,
  segment?: string,
  offset: number = 0,
  limit: number = 50
): Promise<FlexibilityEnvelopesResponse> {
  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (clusterId && clusterId.toLowerCase() !== 'all') params.append('cluster_id', clusterId);
  if (modality && modality.toLowerCase() !== 'all') params.append('modality', modality);
  if (segment && segment.toLowerCase() !== 'all') params.append('segment', segment);
  const res = await fetch(`${API_BASE}/flexibility/envelopes?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch flexibility envelopes: ${res.statusText}`);
  return res.json();
}

export async function evaluateFlexibilityScenario(
  scenarioId: string = 'NORMAL',
  clusterId?: string,
  seed?: number
): Promise<ScenarioEvaluationResult> {
  const res = await fetch(`${API_BASE}/flexibility/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scenario_id: scenarioId,
      cluster_id: clusterId && clusterId.toLowerCase() !== 'all' ? clusterId : null,
      seed: seed ?? null,
    }),
  });
  if (!res.ok) throw new Error(`Scenario evaluation failed: ${res.statusText}`);
  return res.json();
}

export async function fetchFlexibilityScenarios(): Promise<FlexibilityScenariosResponse> {
  const res = await fetch(`${API_BASE}/flexibility/scenarios`);
  if (!res.ok) throw new Error(`Failed to fetch flexibility scenarios: ${res.statusText}`);
  return res.json();
}

export async function recommendTariff(payload: {
  cluster_id: string;
  service_type: string;
  previous_day_average_tariff_inr_per_kwh: number;
  forecast_procurement_cost_inr_per_kwh?: number;
  forecast_demand_mw?: number;
  available_capacity_mw?: number;
  forecast_solar_surplus_mw?: number;
}): Promise<TariffRecommendation> {
  const res = await fetch(`${API_BASE}/tariffs/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Tariff recommendation failed: ${res.statusText}`);
  return res.json();
}

export async function fetchIncentivesSummary(): Promise<IncentivesSummaryResponse> {
  const res = await fetch(`${API_BASE}/incentives/summary`);
  if (!res.ok) throw new Error(`Failed to fetch incentives summary: ${res.statusText}`);
  return res.json();
}
