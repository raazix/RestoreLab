/**
 * RestoreLab Frontend API Client
 * Typed communication with FastAPI backend endpoints.
 */

export interface SystemStatus {
  restic_installed: boolean
  restic_binary_path: string | null
  repository_path: string
  database_path: string
  lab_source: string
  lab_restore: string
  lab_experiments: string
  supermemory_enabled: boolean
  supermemory_namespace: string
  command_timeout_seconds: number
  max_source_scan_mb: number
}

export interface DashboardMetrics {
  total_backups: number
  total_restores: number
  passed_restores: number
  verification_ratio: number
  open_incidents_count: number
  last_integrity_check_passed: boolean | null
  recent_backup_runs: BackupRun[]
  recent_restore_attempts: RestoreAttempt[]
  open_incidents: Incident[]
}

export interface BackupRun {
  run_id: string
  timestamp: string
  source_path: string
  snapshot_id: string | null
  status: 'success' | 'failed' | 'warning'
  manifest_id: string | null
  total_files: number
  total_bytes: number
  duration_seconds: number
  raw_output: string
}

export interface RestoreAttempt {
  attempt_id: string
  timestamp: string
  snapshot_id: string
  target_path: string
  status: 'PASSED' | 'FAILED' | 'WARNING' | 'INCONCLUSIVE'
  original_manifest_id: string | null
  restored_manifest_id: string | null
  matched_files: number
  corrupted_files: number
  missing_files: number
  extra_files: number
  duration_seconds: number
  details: string
}

export interface DiagnosticFinding {
  rule_id: string
  rule_version: string
  certainty: 'confirmed' | 'likely' | 'unknown'
  root_cause: string
  evidence_facts: string[]
  recommended_checks: string[]
  prescriptive_remediations: string[]
  kb_reference_id?: string | null
}

export interface Incident {
  incident_id: string
  created_at: string
  title: string
  status: 'open' | 'investigating' | 'mitigated' | 'resolved' | 'closed'
  severity: 'critical' | 'high' | 'medium' | 'low'
  category: string
  operation_type: 'backup' | 'restore' | 'check' | 'experiment' | 'manifest_scan'
  operation_id?: string | null
  symptoms: string[]
  raw_evidence: Record<string, any>
  findings: DiagnosticFinding[]
  verified_resolution?: string | null
  resolved_by?: string | null
  resolved_at?: string | null
  notes: string[]
}

export interface Snapshot {
  id: string
  short_id: string
  time: string
  paths: string[]
  tags?: string[]
  hostname?: string
  username?: string
}

export interface FileDiffEntry {
  path: string
  status: 'MATCHED' | 'CORRUPTED' | 'MISSING' | 'EXTRA'
  expected_hash?: string | null
  actual_hash?: string | null
  expected_size?: number | null
  actual_size?: number | null
}

export interface VerificationReport {
  id: string
  snapshot_id: string
  timestamp: string
  status: 'PASSED' | 'FAILED' | 'WARNING' | 'INCONCLUSIVE' | 'NOT_RUN'
  original_manifest_id: string
  restored_manifest_id?: string | null
  restore_target_path: string
  resolved_content_path: string
  restore_duration_seconds: number
  verification_duration_seconds: number
  comparison_result?: {
    is_match: boolean
    matched_count: number
    corrupted_count: number
    missing_count: number
    extra_count: number
    file_diffs?: FileDiffEntry[]
  }
  diagnostics_summary: string
}

export interface SearchResult {
  score: number
  source_type: 'knowledge_base' | 'historical_incident'
  reference_id: string
  title: string
  snippet: string
  match_reason: string
  metadata: Record<string, any>
}

export interface KnowledgeArticle {
  article_id: string
  title: string
  category: string
  problem_symptoms: string
  preconditions: string
  diagnostic_checks: string
  verified_cause: string
  resolution_steps: string
  verification_procedure: string
  known_limitations: string
}

export interface ExperimentScenario {
  id: string
  title: string
  description: string
  expected_outcome: string
  target_rule_id: string
  deterministic_rule: string
  preconditions: string[]
}

export interface ExperimentResult {
  scenario_id: string
  success: boolean
  duration_seconds: number
  symptom_observed: string
  findings: DiagnosticFinding[]
  scratchpad_purged: boolean
  details: string
}

export interface SettingsView {
  restic_binary_path: string
  repository_path: string
  database_path: string
  lab_source: string
  lab_restore: string
  lab_experiments: string
  command_timeout_seconds: number
  max_source_scan_mb: number
  max_manifest_files: number
  log_level: string
  supermemory_enabled: boolean
  supermemory_api_url: string
  supermemory_namespace: string
  supermemory_key_configured: boolean
}

const API_BASE = '/api'

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!res.ok) {
    let errMessage = `HTTP ${res.status}: ${res.statusText}`
    try {
      const errData = await res.json()
      if (errData.detail) errMessage = errData.detail
    } catch {
      // ignore
    }
    throw new Error(errMessage)
  }

  return res.json()
}

export const api = {
  // System & Dashboard
  getSystemStatus: () => request<SystemStatus>('/system/status'),
  getDashboard: () => request<DashboardMetrics>('/dashboard'),

  // Backups
  getBackups: (limit = 50) => request<BackupRun[]>(`/backups?limit=${limit}`),
  generateSampleData: () => request<{ success: boolean; message: string; file_count: number; total_bytes: number; files: string[] }>('/backups/generate-sample', { method: 'POST' }),
  generateManifest: () => request<any>('/backups/manifest', { method: 'POST' }),
  initRepo: () => request<any>('/backups/init-repo', { method: 'POST' }),
  runBackup: (tags: string[] = ['manual', 'lab']) => request<any>('/backups/run', { method: 'POST', body: JSON.stringify({ tags }) }),
  checkRepo: (read_data = false) => request<any>('/backups/check', { method: 'POST', body: JSON.stringify({ read_data }) }),

  // Snapshots & Restore
  getSnapshots: () => request<Snapshot[]>('/snapshots'),
  verifyRestore: (snapshot_id: string, subfolder?: string) => request<VerificationReport>('/restore/verify', { method: 'POST', body: JSON.stringify({ snapshot_id, subfolder }) }),

  // Incidents
  getIncidents: (status?: string, limit = 50) => request<Incident[]>(`/incidents${status ? `?status=${status}&` : '?'}limit=${limit}`),
  getIncident: (id: string) => request<Incident>(`/incidents/${id}`),
  updateIncident: (id: string, data: { status: string; resolution?: string; note?: string }) => request<Incident>(`/incidents/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  previewSanitizedTelemetry: (id: string) => request<any>(`/incidents/${id}/preview-sanitized`, { method: 'POST' }),
  syncSupermemory: (id: string, consent: boolean) => request<any>(`/incidents/${id}/sync-supermemory`, { method: 'POST', body: JSON.stringify({ consent }) }),

  // Knowledge Base
  searchKnowledge: (query: string, use_supermemory = false, limit = 10) => request<SearchResult[]>(`/knowledge/search?query=${encodeURIComponent(query)}&use_supermemory=${use_supermemory}&limit=${limit}`),
  getKnowledgeArticles: () => request<KnowledgeArticle[]>('/knowledge/articles'),

  // Experiments
  getExperiments: () => request<ExperimentScenario[]>('/experiments'),
  runExperiment: (scenario_id: string) => request<ExperimentResult>(`/experiments/${scenario_id}/run`, { method: 'POST' }),

  // Reports
  getIncidentReport: (id: string) => request<{ incident_id: string; title: string; sha256_fingerprint: string; markdown: string }>(`/reports/incident/${id}`),
  getRestoreReport: (attempt_id: string) => request<{ attempt_id: string; snapshot_id: string; status: string; sha256_fingerprint: string; markdown: string }>(`/reports/restore/${attempt_id}`),

  // Settings
  getSettings: () => request<SettingsView>('/settings'),
  testSupermemory: () => request<{ success: boolean; message: string; namespace: string; api_url: string }>('/settings/test-supermemory', { method: 'POST' }),
}
