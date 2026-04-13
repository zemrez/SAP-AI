// TypeScript interfaces matching the backend Pydantic schemas

export type AnomalySeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
export type AnomalyStatus = 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'FALSE_POSITIVE';
export type ScanStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
export type RuleType = 'STATISTICAL' | 'RULE_BASED' | 'ML' | 'PATTERN';

export interface Anomaly {
  id: string;
  scan_run_id: string;
  rule_id: string;
  rule_name: string;
  severity: AnomalySeverity;
  status: AnomalyStatus;
  risk_score: number; // 0-100
  company_code: string;
  fiscal_year: string;
  fiscal_period: string;
  document_number?: string;
  vendor_id?: string;
  amount?: number;
  currency?: string;
  description: string;
  details: Record<string, unknown>;
  llm_explanation?: string;
  detected_at: string; // ISO datetime
  updated_at: string;
}

export interface ScanRun {
  id: string;
  status: ScanStatus;
  company_code: string;
  fiscal_year: string;
  fiscal_period?: string;
  started_at: string;
  completed_at?: string;
  anomaly_count: number;
  error_message?: string;
  triggered_by: string;
}

export interface DetectionRule {
  id: string;
  name: string;
  description: string;
  rule_type: RuleType;
  enabled: boolean;
  severity: AnomalySeverity;
  parameters: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AnomalyStats {
  total: number;
  by_severity: Record<AnomalySeverity, number>;
  by_status: Record<AnomalyStatus, number>;
  last_scan_at?: string;
  open_critical: number;
  open_high: number;
  recent_trend: 'UP' | 'DOWN' | 'STABLE';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

// Anomaly detail / explanation types
export interface AnomalyExplanation {
  root_cause: string;
  risk_assessment: string;
  recommended_actions: string[];
}

export interface AnomalyTimelineEntry {
  id: string;
  action: string;
  performed_by: string;
  timestamp: string;
  details?: string;
}

export interface AnomalyDetail extends Anomaly {
  explanation?: AnomalyExplanation;
  timeline?: AnomalyTimelineEntry[];
  assigned_to?: string;
  resolution_notes?: string;
  gl_account?: string;
  posting_date?: string;
}

// Scan trigger request
export type ScanType = 'FULL' | 'INCREMENTAL';

export interface ScanTriggerRequest {
  company_code: string;
  date_from?: string;
  date_to?: string;
  scan_type: ScanType;
}

// Patch anomaly request
export interface PatchAnomalyRequest {
  status?: AnomalyStatus;
  assigned_to?: string;
  resolution_notes?: string;
}

// Sort direction
export type SortDirection = 'asc' | 'desc';

export interface SortConfig {
  field: string;
  direction: SortDirection;
}
