export type Provenance = 'OBSERVED' | 'ASSUMED' | 'SYNTHETIC' | 'SYNTHETIC_CALIBRATION';

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

// Phase 2 Types
export interface FileInfo {
  path: string;
  row_count: number;
  size_bytes: number;
  sha256: string;
  description: string;
}

export interface DataManifestResponse {
  manifest_version: string;
  generator_version: string;
  provenance: Provenance;
  random_seed: number;
  demo_mode: boolean;
  date_range: {
    start: string;
    end: string;
    total_hours_per_cluster: number;
    total_cluster_hours: number;
    timezone: string;
  };
  clusters: string[];
  config_hashes: Record<string, string>;
  files: Record<string, FileInfo>;
  methodology_disclaimer: string;
}

export interface BaselineCalibrationResponse {
  target_service_reliability_pct: number;
  target_energy_loss_pct: number;
  measured_service_reliability_pct: number;
  measured_energy_loss_pct: number;
  residual_reliability_pct: number;
  residual_loss_pct: number;
  total_objective_error: number;
  calibrated_parameters: Record<string, any>;
  parameter_bounds: Record<string, any>;
  calibration_sample_hours: number;
  energy_reconciliation_pass_rate_pct: number;
  max_energy_residual_mwh: number;
  status: string;
  provenance: string;
  notes: string;
}

export interface IEXDiagnosticsResponse {
  total_15min_records_read: number;
  total_hours_produced: number;
  aggregation_method_used: string;
  complete_hours_count: number;
  incomplete_hours_count: number;
  duplicate_blocks_count: number;
  out_of_order_blocks_count: number;
  missing_blocks_details: Array<Record<string, any>>;
  total_cleared_energy_mwh?: number;
  average_cleared_power_mw?: number;
  min_hourly_price_inr_mwh: number;
  max_hourly_price_inr_mwh: number;
  mean_hourly_price_inr_mwh: number;
  provenance: Provenance;
}

export interface TargetMetadata {
  target_name: string;
  display_name: string;
  unit: string;
  scope: string;
  non_negative: boolean;
}

export interface HorizonPoint {
  horizon_hour: number;
  target_timestamp: string;
  p10: number;
  p50: number;
  p90: number;
}

export interface ForecastResponse {
  origin_timestamp: string;
  target_name: string;
  target_display_name: string;
  target_unit: string;
  cluster_id: string;
  model_family: string;
  training_date_range: { start: string; end: string };
  provenance: Provenance;
  horizons: HorizonPoint[];
  evaluation_metrics?: Record<string, any>;
}

export interface ForecastSummaryResponse {
  available_targets: TargetMetadata[];
  available_clusters: string[];
  training_date_range: { start: string; end: string };
  validation_date_range: { start: string; end: string };
  test_date_range: { start: string; end: string };
  model_family: string;
  provenance: Provenance;
  total_models_trained: number;
}

export interface ForecastMetricsResponse {
  evaluation_split: string;
  metrics: Record<string, any>;
  provenance: Provenance;
}

// ==========================================
// Phase 4: Customer Flexibility Types
// ==========================================
export type CustomerSegment =
  | 'EMERGENCY'
  | 'PRIORITY_FLEET'
  | 'RIDE_HAILING'
  | 'LOGISTICS_FLEET'
  | 'PRIVATE_EV';

export type ServiceType = 'FAST_CHARGE' | 'BATTERY_SWAP';

export interface SegmentInfo {
  segment: CustomerSegment;
  priority_rank: number;
  share_assumed: number;
  opt_in_rate_assumed: number;
  max_wait_minutes: number;
  max_deferral_minutes: number;
  flexible_fraction: number;
  is_shiftable: boolean;
  description: string;
  provenance: string;
}

export interface CustomerSegmentsResponse {
  total_segments: number;
  segments: SegmentInfo[];
  provenance: string;
  disclaimer: string;
}

export interface RequestClusterSummary {
  cluster_id: string;
  fast_charge_requests: number;
  swap_requests: number;
  total_fast_charge_kwh: number;
  total_swap_packs: number;
  reconciliation_pass_rate_pct: number;
}

export interface CustomerRequestsSummaryResponse {
  total_requests: number;
  total_fast_charge_requests: number;
  total_battery_swap_requests: number;
  total_fast_charge_mwh: number;
  total_swap_mwh: number;
  total_swap_packs: number;
  reconciliation_passed: boolean;
  cluster_summaries: RequestClusterSummary[];
  provenance: string;
  disclaimer: string;
}

export interface FlexibilitySummaryResponse {
  total_demand_kwh: number;
  non_shiftable_demand_kwh: number;
  eligible_flexible_demand_kwh: number;
  opted_in_demand_kwh: number;
  expected_accepted_demand_kwh: number;
  realized_accepted_demand_kwh: number;
  protected_priority_requests: number;
  protected_priority_demand_kwh: number;
  deadline_violations: number;
  modality_breakdown: Record<string, any>;
  segment_breakdown: Record<string, any>;
  provenance: string;
}

export interface FlexibilityEnvelope {
  request_id: string;
  cluster_id: string;
  request_type: ServiceType;
  customer_segment: CustomerSegment;
  arrival_ts: string;
  earliest_start_ts: string;
  deadline_ts: string;
  requested_energy_kwh: number;
  minimum_service_energy_kwh: number;
  non_shiftable_energy_kwh: number;
  flexible_energy_kwh: number;
  requested_pack_count?: number;
  minimum_pack_count?: number;
  non_shiftable_pack_count?: number;
  flexible_pack_count?: number;
  pack_capacity_kwh?: number;
  eligible_time_slots: string[];
  max_deferral_minutes: number;
  flexibility_opt_in: boolean;
  is_deferrable: boolean;
  reason_code: string;
  service_risk_score: number;
  provenance: string;
  assumption_reference: string;
}

export interface FlexibilityEnvelopesResponse {
  total_count: number;
  offset: number;
  limit: number;
  envelopes: FlexibilityEnvelope[];
  provenance: string;
}

export interface TariffRecommendation {
  cluster_id: string;
  service_type: ServiceType;
  timestamp: string;
  previous_day_average_tariff_inr_per_kwh: number;
  tariff_min_inr_per_kwh: number;
  tariff_max_inr_per_kwh: number;
  raw_tariff_inr_per_kwh: number;
  final_tariff_inr_per_kwh: number;
  clamped: boolean;
  clamping_direction: string;
  pricing_factors: Record<string, number>;
  adjustment_reasons: string[];
  provenance: string;
}

export interface IncentiveOffer {
  offer_id: string;
  request_id: string;
  cluster_id: string;
  customer_segment: CustomerSegment;
  service_type: ServiceType;
  proposed_shift_kwh: number;
  proposed_shift_packs?: number;
  proposed_slots: string[];
  baseline_tariff_inr_per_kwh: number;
  effective_tariff_inr_per_kwh: number;
  incentive_amount_inr: number;
  incentive_rate_inr_per_kwh: number;
  expected_acceptance_probability: number;
  expected_accepted_energy_kwh: number;
  expected_accepted_packs?: number;
  stochastic_realized_acceptance?: boolean;
  realized_accepted_energy_kwh?: number;
  estimated_incentive_cost_inr: number;
  estimated_operational_benefit_inr?: number;
  net_expected_value_inr?: number;
  evaluable: boolean;
  status: string;
  reason_codes: string[];
  offer_expiration_ts: string;
  provenance: string;
}

export interface ScenarioIncentiveSummary {
  scenario_id: string;
  scenario_name: string;
  description: string;
  expected_accepted_demand_kwh: number;
  realized_accepted_demand_kwh: number;
  total_retail_revenue_inr: number;
  total_incentive_cost_inr: number;
  net_financial_impact_inr: number;
  average_wait_minutes: number;
}

export interface IncentivesSummaryResponse {
  scenarios: ScenarioIncentiveSummary[];
  provenance: string;
  disclaimer: string;
}

export interface FlexibilityScenarioMetadata {
  scenario_id: string;
  name: string;
  description: string;
  seed: number;
  parameters: Record<string, any>;
  provenance: string;
}

export interface FlexibilityScenariosResponse {
  total_scenarios: number;
  scenarios: FlexibilityScenarioMetadata[];
  provenance: string;
}

export interface ScenarioEvaluationResult {
  scenario_id: string;
  scenario_name: string;
  description: string;
  seed: number;
  total_requests: number;
  total_demand_kwh: number;
  non_shiftable_demand_kwh: number;
  eligible_flexible_demand_kwh: number;
  opted_in_demand_kwh: number;
  expected_accepted_demand_kwh: number;
  realized_accepted_demand_kwh: number;
  deadline_violations: number;
  protected_priority_requests: number;
  protected_priority_demand_kwh: number;
  total_retail_revenue_inr: number;
  total_incentive_cost_inr: number;
  average_wait_minutes: number;
  average_effective_tariff_inr_per_kwh: number;
  cluster_metrics: Record<string, any>;
  modality_metrics: Record<string, any>;
  segment_metrics: Record<string, any>;
  sample_envelopes: FlexibilityEnvelope[];
  sample_offers: IncentiveOffer[];
  provenance: string;
}
