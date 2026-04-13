import type {
  Anomaly,
  AnomalyDetail,
  ScanRun,
  DetectionRule,
  AnomalyStats,
  PaginatedResponse,
  AnomalyStatus,
  AnomalySeverity,
  PatchAnomalyRequest,
  ScanTriggerRequest,
  AnomalyExplanation,
} from './types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8011';

// Generic fetch wrapper with error handling
async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

// ---- Anomaly endpoints ----

export interface ListAnomaliesParams {
  page?: number;
  page_size?: number;
  severity?: AnomalySeverity;
  status?: AnomalyStatus;
  company_code?: string;
  scan_run_id?: string;
  search?: string;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  date_from?: string;
  date_to?: string;
}

export function listAnomalies(
  params: ListAnomaliesParams = {}
): Promise<PaginatedResponse<Anomaly>> {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return apiFetch<PaginatedResponse<Anomaly>>(
    `/api/v1/anomaly-detective/anomalies${qs ? `?${qs}` : ''}`
  );
}

export function getAnomaly(id: string): Promise<AnomalyDetail> {
  return apiFetch<AnomalyDetail>(`/api/v1/anomaly-detective/anomalies/${id}`);
}

export function patchAnomaly(
  id: string,
  payload: PatchAnomalyRequest
): Promise<AnomalyDetail> {
  return apiFetch<AnomalyDetail>(`/api/v1/anomaly-detective/anomalies/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function patchAnomaliesBulk(
  ids: string[],
  payload: PatchAnomalyRequest
): Promise<{ updated: number }> {
  return apiFetch<{ updated: number }>('/api/v1/anomaly-detective/anomalies/bulk', {
    method: 'PATCH',
    body: JSON.stringify({ ids, ...payload }),
  });
}

export function requestAnomalyExplanation(id: string): Promise<AnomalyExplanation> {
  return apiFetch<AnomalyExplanation>(
    `/api/v1/anomaly-detective/anomalies/${id}/explain`,
    { method: 'POST' }
  );
}

export function getAnomalyStats(): Promise<AnomalyStats> {
  return apiFetch<AnomalyStats>('/api/v1/anomaly-detective/anomalies/stats');
}

// ---- Scan run endpoints ----

export interface ListScansParams {
  page?: number;
  page_size?: number;
  company_code?: string;
  status?: string;
}

export function listScanRuns(
  params: ListScansParams = {}
): Promise<PaginatedResponse<ScanRun>> {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return apiFetch<PaginatedResponse<ScanRun>>(
    `/api/v1/anomaly-detective/scans${qs ? `?${qs}` : ''}`
  );
}

export function getScanRun(id: string): Promise<ScanRun> {
  return apiFetch<ScanRun>(`/api/v1/anomaly-detective/scans/${id}`);
}

export function triggerScan(payload: ScanTriggerRequest): Promise<ScanRun> {
  return apiFetch<ScanRun>('/api/v1/anomaly-detective/scans', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ---- Detection rule endpoints ----

export function listDetectionRules(): Promise<DetectionRule[]> {
  return apiFetch<DetectionRule[]>('/api/v1/rules');
}

export function updateDetectionRule(
  id: string,
  payload: Partial<DetectionRule>
): Promise<DetectionRule> {
  return apiFetch<DetectionRule>(`/api/v1/rules/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}
