export type Provenance = 'OBSERVED' | 'ASSUMED' | 'SYNTHETIC';

export interface MetricItem {
  value: number;
  unit: string;
  provenance: Provenance;
  percentage?: number;
  description?: string;
}

export interface CapacityMixItem {
  share: number;
  percentage: number;
  aggregate_capacity_mw: number;
  unit: string;
  provenance: Provenance;
  description: string;
}

export interface StorageCapacityFact {
  combined_storage_mwh: number;
  unit: string;
  provenance: Provenance;
  asset_split_known: boolean;
  description: string;
}

export interface ReliabilityBenchmark {
  current_reference: number;
  current_percentage: number;
  target: number;
  target_percentage: number;
  relative_increase_percent: number;
  unit: string;
  provenance: Provenance;
  description?: string;
}

export interface EnergyLossBenchmark {
  current_reference: number;
  current_percentage: number;
  target: number;
  target_percentage: number;
  relative_reduction_percent: number;
  unit: string;
  provenance: Provenance;
  description?: string;
}

export interface EbitdaBenchmark {
  target: number;
  target_percentage: number;
  operator: string;
  scope: string;
  unit: string;
  provenance: Provenance;
  description?: string;
}

export interface EmergencyReserveGuardrail {
  value: number;
  percentage: number;
  unit: string;
  scope: string;
  constraint_type: string;
  provenance: Provenance;
  description?: string;
}

export interface CustomerTariffGuardrail {
  min_multiplier: number;
  max_multiplier: number;
  reference_base: string;
  provenance: Provenance;
  description?: string;
}

export interface UnknownAssumptionDisclosure {
  parameter: string;
  case_fact_status: string;
  assumed_value: any;
  unit: string;
  provenance: Provenance;
  rationale: string;
}

export interface CaseConfigResponse {
  title: string;
  specification_version: string;
  currency: string;
  clusters: string[];
  cluster_count: number;
  cluster_provenance: Provenance;
  installed_capacity: MetricItem;
  capacity_mix: {
    fast_charging: CapacityMixItem;
    battery_swapping: CapacityMixItem;
  };
  storage_capacity: StorageCapacityFact;
  renewable_sourcing_reference: MetricItem;
  kpi_benchmarks: {
    service_reliability: ReliabilityBenchmark;
    energy_losses: EnergyLossBenchmark;
    ebitda_margin: EbitdaBenchmark;
  };
  operating_guardrails: {
    emergency_reserve: EmergencyReserveGuardrail;
    customer_tariff_bound: CustomerTariffGuardrail;
  };
  historical_data_specification: {
    duration_years: number;
    time_resolution: string;
    required_series: string[];
    provenance: Provenance;
  };
  unknown_assumptions: UnknownAssumptionDisclosure[];
}

export interface ClusterInfo {
  cluster_id: string;
  name: string;
  provenance: Provenance;
  installed_capacity_share_assumed: number;
  installed_capacity_mw_assumed: number;
  capacity_provenance: Provenance;
  grid_import_limit_mw_assumed: number;
  status: string;
}

export interface ClustersResponse {
  total_clusters: number;
  clusters: ClusterInfo[];
  provenance: Provenance;
  note: string;
}

export interface ScenarioMetadata {
  scenario_id: string;
  name: string;
  description: string;
  demand_multiplier: number;
  renewable_multiplier: number;
  iex_price_multiplier: number;
  swap_demand_multiplier: number;
  initial_pack_ready_fraction: number;
  initial_bess_soc: number;
  probability_weight: number;
  seed: number;
  status: string;
  provenance: Provenance;
}

export interface ScenariosResponse {
  total_scenarios: number;
  scenarios: ScenarioMetadata[];
  provenance: Provenance;
  note: string;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  version: string;
  timestamp: string;
  database: string;
  environment: string;
}
