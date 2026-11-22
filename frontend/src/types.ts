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


// =====================================================================
// Phase 5: Optimization Types
// =====================================================================

export type OptimizationMode = 'BAU_BASELINE' | 'DETERMINISTIC_P50' | 'RISK_AWARE_CVAR';

export type SolverStatus =
  | 'OPTIMAL'
  | 'FEASIBLE_GAP'
  | 'INFEASIBLE'
  | 'TIME_LIMIT'
  | 'SOLVER_UNAVAILABLE'
  | 'ERROR'
  | 'FALLBACK_HEURISTIC';

export type DynamicTariffTier = '0.80x' | '0.90x' | '1.00x' | '1.10x' | '1.20x';

export interface HourlyClusterDecision {
  cluster_id: string;
  hour: number;
  discom_mw: number;
  iex_mw: number;
  renewable_used_mwh: number;
  renewable_curtailed_mwh: number;
  bess_charge_mw: number;
  bess_discharge_mw: number;
  bess_soc_mwh: number;
  bess_reserve_compliant: boolean;
  swap_packs_served: number;
  swap_packs_charging: number;
  swap_packs_ready: number;
  swap_packs_depleted: number;
  swap_charge_power_mw: number;
  swap_reserve_compliant: boolean;
  fc_demand_requested_mwh: number;
  fc_demand_served_mwh: number;
  fc_demand_shifted_mwh: number;
  fc_unserved_slack_mwh: number;
  selected_tariff_tier: DynamicTariffTier;
  tariff_inr_per_kwh: number;
  tariff_revenue_inr: number;
  incentive_spend_inr: number;
  losses_mwh: number;
  power_headroom_mw: number;
  power_headroom_compliant: boolean;
  binding_constraints: string[];
}

export interface OptimizationKPIs {
  service_reliability_pct: number;
  fast_charge_fill_rate_pct: number;
  swap_pack_fill_rate_pct: number;
  energy_loss_pct: number;
  renewable_share_pct: number;
  power_capacity_headroom_mw: number;
  power_headroom_reserve_compliant: boolean;
  bess_emergency_reserve_compliant: boolean;
  swap_emergency_reserve_compliant: boolean;
  deadline_violations_count: number;
  unserved_critical_mwh: number;
  total_energy_requested_mwh: number;
  total_energy_served_mwh: number;
  total_procurement_cost_inr: number;
  total_retail_revenue_inr: number;
  total_flexibility_incentive_inr: number;
  total_degradation_cost_inr: number;
  net_operating_cost_inr: number;
  cvar_tail_risk_cost_inr: number;
  ebitda_operating_margin_pct?: number | null;
  ebitda_status: string;
}

export interface SolverMetadata {
  solver_name: string;
  solver_version: string;
  solver_status: SolverStatus;
  termination_condition: string;
  solve_time_seconds: number;
  objective_value: number;
  best_bound?: number | null;
  mip_gap?: number | null;
  iterations?: number | null;
  variables_count: number;
  constraints_count: number;
  is_fallback: boolean;
  infeasibility_reasons: string[];
}

export interface OptimizationRunResponse {
  run_id: string;
  mode: OptimizationMode;
  timestamp: string;
  clusters: string[];
  scenarios_evaluated: string[];
  solver_metadata: SolverMetadata;
  kpis: OptimizationKPIs;
  provenance: Provenance;
  disclaimer: string;
}

export interface OptimizationSummaryResponse {
  run_id: string;
  mode: OptimizationMode;
  solver_status: SolverStatus;
  solve_time_seconds: number;
  mip_gap?: number | null;
  objective_value: number;
  kpis: OptimizationKPIs;
  cluster_summaries: Record<
    string,
    {
      service_reliability_pct: number;
      total_energy_served_mwh: number;
      net_operating_cost_inr: number;
      renewable_utilization_pct: number;
      energy_loss_pct: number;
    }
  >;
  provenance: Provenance;
}

export interface OptimizationDecisionsResponse {
  cluster_id: string;
  mode: OptimizationMode;
  decisions: HourlyClusterDecision[];
  provenance: Provenance;
}

export interface PolicyComparisonData {
  mode: string;
  solver_status: string;
  solve_time_seconds?: number;
  mip_gap?: number | null;
  service_reliability_pct: number;
  energy_loss_pct: number;
  renewable_share_pct: number;
  net_operating_cost_inr: number;
  procurement_cost_inr: number;
  retail_revenue_inr: number;
  cvar_tail_risk_inr: number;
  min_power_headroom_mw: number;
  cost_saving_inr?: number;
  cost_saving_pct?: number;
  reliability_uplift_pct?: number;
  tail_risk_hedge_inr?: number;
}

export interface OptimizationCompareResponse {
  comparison_summary: {
    bau_baseline: PolicyComparisonData;
    deterministic_p50: PolicyComparisonData;
    risk_aware_cvar: PolicyComparisonData;
  };
  invariants_verified: Record<string, boolean>;
  provenance: Provenance;
}

export interface ScenarioCatalogItem {
  scenario_id: string;
  probability: number;
  description: string;
  provenance: Provenance;
}

export interface OptimizationScenariosCatalogResponse {
  scenarios: ScenarioCatalogItem[];
  alpha_confidence: number;
  provenance: Provenance;
}

// ==========================================
// Phase 6: Digital Twin & Rolling MPC Types
// ==========================================

export type ShockScenarioType =
  | 'NORMAL_OPERATION'
  | 'EVENING_DEMAND_SURGE'
  | 'SOLAR_CLOUD_DROP'
  | 'WIND_LULL'
  | 'IEX_PRICE_SPIKE'
  | 'GRID_IMPORT_RESTRICTION'
  | 'SWAP_INVENTORY_SHORTAGE'
  | 'HEATWAVE_COMPOUND'
  | 'COMBINED_MULTI_CITY_CRISIS'
  | 'RECOVERY_AFTER_CRISIS';

export type SimulationPolicy =
  | 'BAU_BASELINE'
  | 'OPEN_LOOP_P50'
  | 'OPEN_LOOP_CVAR'
  | 'CLOSED_LOOP_MPC_P50'
  | 'CLOSED_LOOP_MPC_CVAR';

export interface ScenarioItem {
  id: string;
  name: string;
  description: string;
  severity: string;
  start_hour: number;
  duration_hours: number;
  affected_clusters: string[];
  forecast_visibility: string;
  multipliers: Record<string, any>;
}

export interface SimulationScenariosCatalogResponse {
  scenarios: ScenarioItem[];
  count: number;
  provenance: Provenance;
}

export interface DigitalTwinKPIs {
  service_reliability_pct: number;
  fast_charge_fill_rate_pct: number;
  swap_pack_fill_rate_pct: number;
  swap_energy_fill_rate_pct: number;
  emergency_service_violations_count: number;
  priority_service_violations_count: number;
  deadline_violations_count: number;
  mean_waiting_time_minutes: number;
  p95_waiting_time_minutes: number;
  max_waiting_time_minutes: number;
  deferred_energy_eventually_served_mwh: number;
  deferred_energy_unserved_mwh: number;
  total_energy_requested_mwh: number;
  total_energy_served_mwh: number;
  total_discom_energy_mwh: number;
  total_iex_energy_mwh: number;
  total_renewable_energy_mwh: number;
  renewable_utilization_pct: number;
  renewable_curtailment_mwh: number;
  bess_throughput_mwh: number;
  bess_final_soc_mwh: number;
  swap_final_ready_packs: number;
  total_losses_mwh: number;
  energy_loss_pct: number;
  energy_balance_residual_mwh: number;
  reserve_violations_count: number;
  procurement_cost_inr: number;
  retail_tariff_revenue_inr: number;
  flexibility_incentive_inr: number;
  bess_degradation_cost_inr: number;
  net_operating_contribution_inr: number;
  ebitda_status: string;
  forecast_mae_demand_mwh: number;
  forecast_mae_renewable_mwh: number;
  forecast_mae_price_inr: number;
  mean_solve_time_seconds: number;
  max_solve_time_seconds: number;
  fallback_events_count: number;
  cvar_tail_risk_cost_inr: number;
}

export interface EBITDAEvaluation {
  status: string;
  ebitda_margin_pct?: number | null;
  missing_components: string[];
  explanation: string;
  provenance: Provenance;
}

export interface SimulationRunResponse {
  run_id: string;
  scenario_id: string;
  policy: SimulationPolicy;
  horizon_hours: number;
  seed: number;
  clusters: string[];
  kpis: DigitalTwinKPIs;
  ebitda: EBITDAEvaluation;
  invariants_verified: Record<string, boolean>;
  provenance: Provenance;
  disclaimer: string;
}

export interface SimulationTimelineResponse {
  run_id: string;
  scenario_id: string;
  policy: SimulationPolicy;
  timeline: Array<{
    hour: number;
    timestamp: string;
    is_fallback: boolean;
    solver_status: string;
    clusters: Record<string, any>;
    actions: Record<string, any>;
  }>;
  provenance: Provenance;
}

export interface DecisionExplanation {
  timestamp: string;
  hour: number;
  cluster_id: string;
  detected_operating_condition: string;
  binding_constraints: string[];
  procurement_choice_reason: string;
  storage_dispatch_reason: string;
  flexible_demand_decision: string;
  tariff_recommendation_reason: string;
  headroom_reserve_status: string;
  cost_decomposition: Record<string, number>;
  solver_status: string;
  is_fallback: boolean;
  fallback_reason?: string | null;
  provenance: Provenance;
}

export interface SimulationExplainabilityResponse {
  run_id: string;
  explanations: DecisionExplanation[];
  provenance: Provenance;
}

export interface SimulationEventsResponse {
  run_id: string;
  scenario_id: string;
  scenario_details: Record<string, any>;
  provenance: Provenance;
}

export interface PolicyComparisonMetric {
  policy: string;
  service_reliability_pct: number;
  energy_loss_pct: number;
  renewable_share_pct: number;
  total_energy_served_mwh: number;
  procurement_cost_inr: number;
  retail_revenue_inr: number;
  net_operating_contribution_inr: number;
  fallback_events_count: number;
  ebitda_status: string;
}

export interface SimulationComparisonResponse {
  run_id: string;
  scenario_id: string;
  horizon_hours: number;
  policies: Record<string, PolicyComparisonMetric>;
  cost_saving_mpc_vs_bau_pct: number;
  service_uplift_mpc_vs_bau_pct: number;
  loss_reduction_mpc_vs_bau_pct: number;
  ebitda_disclosure: EBITDAEvaluation;
  provenance: Provenance;
}

export interface MPCStatusResponse {
  controller_status: string;
  preferred_solver: string;
  available_solvers: string[];
  default_horizon_hours: number;
  control_step_hours: number;
  receding_horizon: boolean;
  invariants_enforced: string[];
  timestamp: string;
}
