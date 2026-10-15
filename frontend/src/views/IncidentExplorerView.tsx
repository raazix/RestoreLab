import React, { useEffect, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Send,
  Eye,
  FileText,
  Save,
  Check,
  Search,
  ExternalLink,
  Lock,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Tabs } from '@/components/ui/Tabs'
import { api, Incident, SystemStatus } from '@/lib/api'

interface IncidentExplorerViewProps {
  systemStatus: SystemStatus | null
  onRefreshMetrics: () => void
}

export const IncidentExplorerView: React.FC<IncidentExplorerViewProps> = ({
  systemStatus,
  onRefreshMetrics,
}) => {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [loading, setLoading] = useState(false)

  // Edit states
  const [editStatus, setEditStatus] = useState<string>('open')
  const [editResolution, setEditResolution] = useState<string>('')
  const [savingIncident, setSavingIncident] = useState(false)

  // Supermemory sync states
  const [previewPayload, setPreviewPayload] = useState<any | null>(null)
  const [showPreview, setShowPreview] = useState(false)
  const [consentGiven, setConsentGiven] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<string | null>(null)

  const fetchIncidents = async () => {
    setLoading(true)
    try {
      const data = await api.getIncidents(statusFilter === 'all' ? undefined : statusFilter)
      setIncidents(data)
      if (data.length > 0 && (!selectedIncidentId || !data.some(i => i.incident_id === selectedIncidentId))) {
        setSelectedIncidentId(data[0].incident_id)
        setEditStatus(data[0].status)
        setEditResolution(data[0].verified_resolution || '')
      }
    } catch (err: any) {
      console.error('Failed to fetch incidents', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchIncidents()
  }, [statusFilter])

  const selectedIncident = incidents.find((i) => i.incident_id === selectedIncidentId)

  useEffect(() => {
    if (selectedIncident) {
      setEditStatus(selectedIncident.status)
      setEditResolution(selectedIncident.verified_resolution || '')
      setPreviewPayload(null)
      setShowPreview(false)
      setConsentGiven(false)
      setSyncResult(null)
    }
  }, [selectedIncidentId])

  const handleSaveUpdates = async () => {
    if (!selectedIncidentId) return
    setSavingIncident(true)
    try {
      await api.updateIncident(selectedIncidentId, {
        status: editStatus,
        resolution: editResolution.trim() || undefined,
      })
      await fetchIncidents()
      onRefreshMetrics()
    } catch (err: any) {
      alert(`Failed to save incident: ${err.message}`)
    } finally {
      setSavingIncident(false)
    }
  }

  const handlePreviewSanitization = async () => {
    if (!selectedIncidentId) return
    try {
      const payload = await api.previewSanitizedTelemetry(selectedIncidentId)
      setPreviewPayload(payload)
      setShowPreview(true)
    } catch (err: any) {
      alert(`Preview failed: ${err.message}`)
    }
  }

  const handleSyncSupermemory = async () => {
    if (!selectedIncidentId || !consentGiven) return
    setSyncing(true)
    setSyncResult(null)
    try {
      const res = await api.syncSupermemory(selectedIncidentId, consentGiven)
      setSyncResult(res.message || 'Incident successfully indexed in Supermemory v5 namespace!')
      onRefreshMetrics()
    } catch (err: any) {
      setSyncResult(`Sync Error: ${err.message}`)
    } finally {
      setSyncing(false)
    }
  }

  const statusTabs = [
    { id: 'all', label: 'All Incidents', badge: incidents.length },
    { id: 'open', label: 'Open' },
    { id: 'investigating', label: 'Investigating' },
    { id: 'mitigated', label: 'Mitigated' },
    { id: 'resolved', label: 'Resolved' },
  ]

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* View Header */}
      <div>
        <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
          Incident Explorer & Root Cause Triage
        </h2>
        <p className="text-xs text-zinc-400 mt-1 max-w-2xl leading-relaxed">
          Track failure investigations, review deterministic rule engine findings without
          hallucinations, and sync sanitized incident summaries to Supermemory v5.
        </p>
      </div>

      {/* Filter Tabs */}
      <Tabs
        tabs={statusTabs}
        activeTab={statusFilter}
        onChange={(id) => setStatusFilter(id)}
      />

      {/* Main Split Layout: List on Left, Detail on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Incidents List */}
        <div className="lg:col-span-5 space-y-2 max-h-[calc(100vh-250px)] overflow-y-auto pr-1">
          {incidents.length === 0 ? (
            <Card className="py-12 text-center text-xs text-zinc-500">
              No incidents found matching current status filter.
            </Card>
          ) : (
            incidents.map((inc) => {
              const isSelected = inc.incident_id === selectedIncidentId

              return (
                <div
                  key={inc.incident_id}
                  onClick={() => setSelectedIncidentId(inc.incident_id)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-surface-3 border-indigo-500/40 shadow-subtle'
                      : 'bg-surface-1 border-border-subtle hover:border-border-muted hover:bg-surface-2/60'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono text-[11px] text-zinc-400">
                      {inc.incident_id}
                    </span>
                    <Badge
                      variant={
                        inc.status === 'resolved'
                          ? 'emerald'
                          : inc.severity === 'critical'
                          ? 'rose'
                          : 'amber'
                      }
                      dot={inc.status !== 'resolved'}
                    >
                      {inc.status.toUpperCase()}
                    </Badge>
                  </div>

                  <h4 className="mt-1.5 text-xs font-semibold text-zinc-100 line-clamp-1">
                    {inc.title}
                  </h4>

                  <div className="mt-2 flex items-center justify-between text-[11px] text-zinc-500 font-mono">
                    <span className="capitalize">{inc.operation_type}</span>
                    <span>{new Date(inc.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Right Column: Selected Incident Detail */}
        <div className="lg:col-span-7">
          {selectedIncident ? (
            <Card className="space-y-6">
              {/* Incident Header */}
              <div className="border-b border-border-subtle pb-4">
                <div className="flex items-center justify-between text-xs font-mono text-zinc-500 mb-2">
                  <span>{selectedIncident.incident_id}</span>
                  <span>{new Date(selectedIncident.created_at).toLocaleString()}</span>
                </div>

                <div className="flex items-center gap-2">
                  <Badge
                    variant={selectedIncident.severity === 'critical' ? 'rose' : 'amber'}
                  >
                    {selectedIncident.severity.toUpperCase()}
                  </Badge>
                  <Badge variant="cyan" className="font-mono text-[10px]">
                    Category: {selectedIncident.category}
                  </Badge>
                </div>

                <h3 className="text-base font-bold text-zinc-100 mt-2">
                  {selectedIncident.title}
                </h3>
              </div>

              {/* Symptoms */}
              {selectedIncident.symptoms && selectedIncident.symptoms.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
                    Observable Symptoms
                  </h4>
                  <ul className="space-y-1">
                    {selectedIncident.symptoms.map((s, idx) => (
                      <li
                        key={idx}
                        className="text-xs font-mono bg-surface-2 px-2.5 py-1.5 rounded border border-border-subtle text-zinc-300"
                      >
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Deterministic Diagnostic Findings */}
              {selectedIncident.findings && selectedIncident.findings.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                    Deterministic Diagnostic Findings
                  </h4>

                  {selectedIncident.findings.map((f, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-surface-2 border border-border-subtle space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-cyan-400">
                          {f.rule_id}
                        </span>
                        <Badge
                          variant={f.certainty === 'confirmed' ? 'emerald' : 'amber'}
                        >
                          Certainty: {f.certainty.toUpperCase()}
                        </Badge>
                      </div>

                      <div className="text-zinc-200">
                        <strong className="text-zinc-400">Root Cause:</strong> {f.root_cause}
                      </div>

                      {f.prescriptive_remediations && f.prescriptive_remediations.length > 0 && (
                        <div className="text-zinc-300">
                          <strong className="text-zinc-400">Prescriptive Remediation:</strong>
                          <ul className="list-disc list-inside mt-1 space-y-0.5 text-zinc-400">
                            {f.prescriptive_remediations.map((r, rIdx) => (
                              <li key={rIdx}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Verified Resolution & Status Updates */}
              <div className="space-y-3 pt-2 border-t border-border-subtle">
                <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                  Lifecycle Status & Verification Workflow
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] font-medium text-zinc-400 block mb-1">
                      Lifecycle Status:
                    </label>
                    <select
                      value={editStatus}
                      onChange={(e) => setEditStatus(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 font-sans focus:outline-none"
                    >
                      <option value="open">Open</option>
                      <option value="investigating">Investigating</option>
                      <option value="mitigated">Mitigated</option>
                      <option value="resolved">Resolved</option>
                      <option value="closed">Closed</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-[11px] font-medium text-zinc-400 block mb-1">
                    Verified Resolution Applied:
                  </label>
                  <textarea
                    rows={3}
                    value={editResolution}
                    onChange={(e) => setEditResolution(e.target.value)}
                    placeholder="Describe confirmed remediation applied..."
                    className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-border-active resize-none"
                  />
                </div>

                <Button
                  size="sm"
                  variant="secondary"
                  isLoading={savingIncident}
                  onClick={handleSaveUpdates}
                  leftIcon={<Save className="w-3.5 h-3.5" />}
                >
                  Save Incident Updates
                </Button>
              </div>

              {/* Supermemory v5 Cloud Knowledge Sync */}
              <div className="p-4 rounded-xl bg-indigo-500/[0.04] border border-indigo-500/20 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Send className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-semibold text-zinc-200">
                      Supermemory API v5 Knowledge Sync
                    </span>
                  </div>
                  <Badge variant="indigo" className="font-mono text-[10px]">
                    ns: {systemStatus?.supermemory_namespace || 'restorelab-incidents'}
                  </Badge>
                </div>

                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  Sync sanitized post-mortem knowledge for case-based reasoning across incidents.
                  Client-side sanitization strips all Windows/POSIX paths to <code className="text-zinc-300">[LOCAL_PATH]</code> and redacts secrets.
                </p>

                {/* Preview Sanitized Telemetry */}
                <div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handlePreviewSanitization}
                    leftIcon={<Eye className="w-3.5 h-3.5 text-zinc-400" />}
                  >
                    Preview Sanitized JSON Payload
                  </Button>

                  {showPreview && previewPayload && (
                    <div className="mt-2 p-3 rounded-lg bg-black/60 border border-border-subtle font-mono text-[10px] text-zinc-300 max-h-48 overflow-y-auto">
                      <pre>{JSON.stringify(previewPayload, null, 2)}</pre>
                    </div>
                  )}
                </div>

                {/* Explicit Consent & Sync Button */}
                <div className="pt-2 border-t border-indigo-500/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={consentGiven}
                      onChange={(e) => setConsentGiven(e.target.checked)}
                      className="rounded bg-surface-3 border-border-muted text-indigo-500 focus:ring-0"
                    />
                    <span>
                      I give explicit consent to transmit this sanitized incident summary to Supermemory
                    </span>
                  </label>

                  <Button
                    size="sm"
                    variant="primary"
                    disabled={!consentGiven}
                    isLoading={syncing}
                    onClick={handleSyncSupermemory}
                    leftIcon={<Send className="w-3.5 h-3.5" />}
                  >
                    Sync to Supermemory
                  </Button>
                </div>

                {syncResult && (
                  <div className="p-2.5 rounded bg-surface-2 text-xs font-mono text-zinc-300 border border-border-subtle">
                    {syncResult}
                  </div>
                )}
              </div>
            </Card>
          ) : (
            <Card className="py-20 text-center text-xs text-zinc-500">
              Select an incident from the left to inspect evidence and diagnostic findings.
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
