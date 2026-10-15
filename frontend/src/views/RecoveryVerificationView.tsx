import React, { useEffect, useState } from 'react'
import {
  CheckCircle2,
  AlertTriangle,
  HardDrive,
  ShieldCheck,
  Copy,
  Check,
  RefreshCw,
  Clock,
  ArrowRight,
  ShieldAlert,
  Play,
  Activity,
  Layers,
  GitCompare,
  Download,
  Flame,
  FileCheck2,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import {
  api,
  Snapshot,
  VerificationReport,
  SystemStatus,
  RecoveryDrill,
  SnapshotDriftReport,
} from '@/lib/api'

interface RecoveryVerificationViewProps {
  systemStatus: SystemStatus | null
  onRefreshMetrics: () => void
}

export const RecoveryVerificationView: React.FC<RecoveryVerificationViewProps> = ({
  systemStatus,
  onRefreshMetrics,
}) => {
  // Navigation tabs within view
  const [activeTab, setActiveTab] = useState<'verification' | 'drills' | 'drift'>('verification')

  // Common snapshots state
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [loadingSnapshots, setLoadingSnapshots] = useState(false)
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string>('')
  const [subfolder, setSubfolder] = useState<string>('')
  const [copiedText, setCopiedText] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // 1. Verification State
  const [verifying, setVerifying] = useState(false)
  const [verificationReport, setVerificationReport] = useState<VerificationReport | null>(null)

  // 2. Recovery Drills State
  const [drills, setDrills] = useState<RecoveryDrill[]>([])
  const [loadingDrills, setLoadingDrills] = useState(false)
  const [runningDrill, setRunningDrill] = useState(false)
  const [rtoTarget, setRtoTarget] = useState<number>(60)
  const [cleanupSandbox, setCleanupSandbox] = useState<boolean>(true)
  const [lastDrillRecord, setLastDrillRecord] = useState<RecoveryDrill | null>(null)

  // 3. Snapshot Drift State
  const [baseSnapshotId, setBaseSnapshotId] = useState<string>('')
  const [targetSnapshotId, setTargetSnapshotId] = useState<string>('current')
  const [analyzingDrift, setAnalyzingDrift] = useState(false)
  const [driftReport, setDriftReport] = useState<SnapshotDriftReport | null>(null)

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedText(text)
    setTimeout(() => setCopiedText(null), 2000)
  }

  const fetchSnapshots = async () => {
    setLoadingSnapshots(true)
    setErrorMsg(null)
    try {
      const data = await api.getSnapshots()
      setSnapshots(data)
      if (data.length > 0) {
        if (!selectedSnapshotId) setSelectedSnapshotId(data[0].id)
        if (!baseSnapshotId) setBaseSnapshotId(data[0].id)
      }
    } catch (err: any) {
      setErrorMsg(`Failed to load snapshots: ${err.message}`)
    } finally {
      setLoadingSnapshots(false)
    }
  }

  const fetchDrills = async () => {
    setLoadingDrills(true)
    try {
      const data = await api.getDrills(30)
      setDrills(data)
    } catch (err: any) {
      console.error('Failed to load recovery drills', err)
    } finally {
      setLoadingDrills(false)
    }
  }

  useEffect(() => {
    fetchSnapshots()
    fetchDrills()
  }, [])

  // Execute single snapshot verification
  const handleVerify = async () => {
    if (!selectedSnapshotId) return
    setVerifying(true)
    setErrorMsg(null)
    setVerificationReport(null)

    try {
      const report = await api.verifyRestore(selectedSnapshotId, subfolder.trim() || undefined)
      setVerificationReport(report)
      onRefreshMetrics()
    } catch (err: any) {
      setErrorMsg(`Verification failed: ${err.message}`)
    } finally {
      setVerifying(false)
    }
  }

  // Execute recovery drill
  const handleRunDrill = async () => {
    setRunningDrill(true)
    setErrorMsg(null)
    try {
      const result = await api.runDrill({
        snapshot_id: selectedSnapshotId || undefined,
        subfolder: subfolder.trim() || undefined,
        rto_target_seconds: rtoTarget,
        drill_type: 'manual',
        cleanup_after: cleanupSandbox,
      })
      setLastDrillRecord(result)
      await fetchDrills()
      onRefreshMetrics()
    } catch (err: any) {
      setErrorMsg(`Drill failed: ${err.message}`)
    } finally {
      setRunningDrill(false)
    }
  }

  // Execute drift analysis
  const handleAnalyzeDrift = async () => {
    if (!baseSnapshotId) return
    setAnalyzingDrift(true)
    setErrorMsg(null)
    try {
      const rep = await api.compareDrift(baseSnapshotId, targetSnapshotId)
      setDriftReport(rep)
    } catch (err: any) {
      setErrorMsg(`Drift analysis failed: ${err.message}`)
    } finally {
      setAnalyzingDrift(false)
    }
  }

  const selectedSnapshot = snapshots.find((s) => s.id === selectedSnapshotId)

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* View Header with Sub-tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-subtle pb-4">
        <div>
          <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
            Recovery Verification & Reliability Auditing
          </h2>
          <p className="text-xs text-zinc-400 mt-0.5 max-w-2xl leading-relaxed">
            Cryptographic SHA-256 verification, automated recovery drills with RTO compliance, and snapshot drift anomaly detection.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 bg-surface-2 p-1 rounded-lg border border-border-subtle">
          <button
            onClick={() => setActiveTab('verification')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'verification'
                ? 'bg-surface-3 text-zinc-100 shadow-sm border border-border-muted'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Sandbox Verification
          </button>
          <button
            onClick={() => setActiveTab('drills')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'drills'
                ? 'bg-surface-3 text-zinc-100 shadow-sm border border-border-muted'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Recovery Drills & RTO
          </button>
          <button
            onClick={() => setActiveTab('drift')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'drift'
                ? 'bg-surface-3 text-zinc-100 shadow-sm border border-border-muted'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Snapshot Drift
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="text-rose-300 hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 1: SANDBOX RESTORE VERIFICATION */}
      {/* ========================================================================= */}
      {activeTab === 'verification' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Left: Snapshot Selector */}
            <Card className="md:col-span-2 space-y-4">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <HardDrive className="w-4 h-4 text-cyan-400" />
                  <CardTitle>Select Snapshot to Verify</CardTitle>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={fetchSnapshots}
                  isLoading={loadingSnapshots}
                  leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                >
                  Refresh
                </Button>
              </CardHeader>

              {snapshots.length === 0 ? (
                <div className="py-6 text-center text-xs text-zinc-500 font-mono">
                  No snapshots found in repository. Execute a backup first.
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-56 overflow-y-auto pr-1">
                    {snapshots.map((s) => {
                      const isSelected = s.id === selectedSnapshotId
                      return (
                        <div
                          key={s.id}
                          onClick={() => setSelectedSnapshotId(s.id)}
                          className={`p-3 rounded-lg border cursor-pointer transition-all ${
                            isSelected
                              ? 'bg-surface-3 border-indigo-500/40 shadow-subtle'
                              : 'bg-surface-2 border-border-subtle hover:border-border-muted'
                          }`}
                        >
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-mono font-bold text-zinc-100">
                              {s.short_id || s.id.slice(0, 8)}
                            </span>
                            <span className="font-mono text-[10px] text-zinc-500">
                              {new Date(s.time).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="mt-1 text-[11px] text-zinc-400 truncate">
                            {s.paths?.join(', ') || 'Source Tree'}
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  <div className="pt-2">
                    <label className="text-[11px] font-medium text-zinc-400 block mb-1">
                      Optional Subfolder Scope (Restore specific subdirectory):
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. data or subfolder (leave blank for entire snapshot)"
                      value={subfolder}
                      onChange={(e) => setSubfolder(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 placeholder-zinc-500 font-mono focus:outline-none focus:border-border-active"
                    />
                  </div>
                </div>
              )}
            </Card>

            {/* Right: Safety Guards */}
            <Card className="flex flex-col justify-between space-y-4">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <CardTitle>Destination Isolation</CardTitle>
                </div>
                <CardDescription>
                  Restores execute strictly inside disposable, isolated sandboxes under{' '}
                  <code className="text-zinc-300">./data/lab_restore/</code>. In-place overwrites are impossible by design.
                </CardDescription>

                <div className="p-3 rounded-lg bg-surface-2 border border-border-subtle space-y-1.5 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-400">Target Isolation:</span>
                    <Badge variant="emerald" dot>
                      Sandbox Enforced
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-400">Cryptographic Verification:</span>
                    <Badge variant="cyan">SHA-256 Byte Match</Badge>
                  </div>
                </div>
              </div>

              <Button
                className="w-full"
                variant="primary"
                isLoading={verifying}
                disabled={!selectedSnapshotId}
                onClick={handleVerify}
                leftIcon={<Play className="w-3.5 h-3.5 fill-current" />}
              >
                Execute Restore & Verification
              </Button>
            </Card>
          </div>

          {/* Verification Results Card */}
          {verificationReport && (
            <Card className="space-y-5 border-indigo-500/30">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-subtle pb-4">
                <div className="flex items-center gap-3">
                  {verificationReport.status === 'PASSED' ? (
                    <div className="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center border border-emerald-500/30">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    </div>
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-rose-500/10 flex items-center justify-center border border-rose-500/30">
                      <ShieldAlert className="w-4 h-4 text-rose-400" />
                    </div>
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-zinc-100">
                        Verification Audit: {verificationReport.snapshot_id.slice(0, 8)}
                      </h3>
                      <Badge
                        variant={verificationReport.status === 'PASSED' ? 'emerald' : 'rose'}
                        dot
                      >
                        {verificationReport.status}
                      </Badge>
                    </div>
                    <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                      {verificationReport.diagnostics_summary}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs font-mono text-zinc-400">
                  <span>Restore: {verificationReport.restore_duration_seconds.toFixed(2)}s</span>
                  <span>•</span>
                  <span>Verify: {verificationReport.verification_duration_seconds.toFixed(2)}s</span>
                  <a
                    href={`/api/reports/download/restore/${verificationReport.id}.html`}
                    target="_blank"
                    rel="noreferrer"
                    className="ml-2 inline-flex items-center gap-1 px-2.5 py-1 rounded bg-surface-2 border border-border-muted text-xs text-zinc-200 hover:text-white"
                  >
                    <Download className="w-3 h-3" />
                    HTML Certificate
                  </a>
                </div>
              </div>

              {/* Statistics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-surface-2 border border-border-subtle">
                  <div className="text-[10px] text-zinc-500 uppercase font-mono">Matched Files</div>
                  <div className="text-xl font-mono font-bold text-emerald-400 mt-1">
                    {verificationReport.comparison_result?.matched_count ?? 0}
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-surface-2 border border-border-subtle">
                  <div className="text-[10px] text-zinc-500 uppercase font-mono">Corruptions</div>
                  <div className="text-xl font-mono font-bold text-rose-400 mt-1">
                    {verificationReport.comparison_result?.corrupted_count ?? 0}
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-surface-2 border border-border-subtle">
                  <div className="text-[10px] text-zinc-500 uppercase font-mono">Missing Files</div>
                  <div className="text-xl font-mono font-bold text-amber-400 mt-1">
                    {verificationReport.comparison_result?.missing_count ?? 0}
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-surface-2 border border-border-subtle">
                  <div className="text-[10px] text-zinc-500 uppercase font-mono">Extra Files</div>
                  <div className="text-xl font-mono font-bold text-zinc-400 mt-1">
                    {verificationReport.comparison_result?.extra_count ?? 0}
                  </div>
                </div>
              </div>

              {/* Diff Table */}
              {verificationReport.comparison_result?.file_diffs &&
                verificationReport.comparison_result.file_diffs.length > 0 && (
                  <div className="border border-border-subtle rounded-lg overflow-hidden">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-surface-2 border-b border-border-subtle text-[10px] text-zinc-400 uppercase font-mono">
                        <tr>
                          <th className="py-2 px-3">Path</th>
                          <th className="py-2 px-3">Status</th>
                          <th className="py-2 px-3">Expected Hash</th>
                          <th className="py-2 px-3">Restored Hash</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-subtle font-mono text-[11px]">
                        {verificationReport.comparison_result.file_diffs.map((diff) => (
                          <tr key={diff.path} className="hover:bg-surface-2/40">
                            <td className="py-2 px-3 text-zinc-200">{diff.path}</td>
                            <td className="py-2 px-3">
                              <Badge
                                variant={diff.status === 'MATCHED' ? 'emerald' : 'rose'}
                                dot={diff.status !== 'MATCHED'}
                              >
                                {diff.status}
                              </Badge>
                            </td>
                            <td className="py-2 px-3 text-zinc-400 truncate max-w-xs">
                              {diff.expected_hash ? diff.expected_hash.slice(0, 16) + '...' : '-'}
                            </td>
                            <td className="py-2 px-3 text-zinc-400 truncate max-w-xs">
                              {diff.actual_hash ? diff.actual_hash.slice(0, 16) + '...' : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
            </Card>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: AUTOMATED RECOVERY DRILLS & RTO SLA */}
      {/* ========================================================================= */}
      {activeTab === 'drills' && (
        <div className="space-y-6">
          {/* Drill Dispatch Panel */}
          <Card className="space-y-4">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-400" />
                <CardTitle>Trigger Automated Disaster Recovery Drill</CardTitle>
              </div>
              <CardDescription>
                Simulates real disaster scenarios by restoring a snapshot into a bounded temporary sandbox, measuring elapsed recovery duration against target RTO, and verifying byte-for-byte SHA-256 accuracy.
              </CardDescription>
            </CardHeader>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  Target Snapshot:
                </label>
                <select
                  value={selectedSnapshotId}
                  onChange={(e) => setSelectedSnapshotId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 font-mono focus:outline-none focus:border-border-active"
                >
                  <option value="">(Auto: Select Latest Available Snapshot)</option>
                  {snapshots.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.short_id || s.id.slice(0, 8)} — {new Date(s.time).toLocaleDateString()}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  RTO SLA Target (Seconds):
                </label>
                <input
                  type="number"
                  min="5"
                  max="600"
                  value={rtoTarget}
                  onChange={(e) => setRtoTarget(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 font-mono focus:outline-none focus:border-border-active"
                />
              </div>

              <div className="flex flex-col justify-end">
                <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer mb-2">
                  <input
                    type="checkbox"
                    checked={cleanupSandbox}
                    onChange={(e) => setCleanupSandbox(e.target.checked)}
                    className="rounded border-zinc-700 bg-surface-2 text-indigo-500 focus:ring-0"
                  />
                  <span>Auto-purge sandbox after drill verification</span>
                </label>
                <Button
                  variant="primary"
                  isLoading={runningDrill}
                  onClick={handleRunDrill}
                  leftIcon={<Play className="w-3.5 h-3.5 fill-current" />}
                >
                  Launch Recovery Drill
                </Button>
              </div>
            </div>
          </Card>

          {/* Drill Audit History Table */}
          <Card className="space-y-4">
            <CardHeader>
              <div>
                <CardTitle>Recovery Drill Audit Log</CardTitle>
                <CardDescription>
                  Historical disaster recovery drills tracked in local SQLite with persisted RTO benchmarks.
                </CardDescription>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={fetchDrills}
                isLoading={loadingDrills}
                leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              >
                Refresh Log
              </Button>
            </CardHeader>

            {drills.length === 0 ? (
              <div className="py-8 text-center text-xs text-zinc-500 font-mono">
                No recovery drills recorded yet. Click "Launch Recovery Drill" above to run the first test.
              </div>
            ) : (
              <div className="border border-border-subtle rounded-lg overflow-hidden">
                <table className="w-full text-xs text-left">
                  <thead className="bg-surface-2 border-b border-border-subtle text-[10px] text-zinc-400 uppercase font-mono">
                    <tr>
                      <th className="py-2.5 px-3">Drill ID</th>
                      <th className="py-2.5 px-3">Snapshot</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Duration / RTO</th>
                      <th className="py-2.5 px-3">Cryptographic Matches</th>
                      <th className="py-2.5 px-3 text-right">Certificate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle font-mono text-[11px]">
                    {drills.map((d) => (
                      <tr key={d.drill_id} className="hover:bg-surface-2/40">
                        <td className="py-2.5 px-3 font-semibold text-zinc-200">
                          {d.drill_id}
                        </td>
                        <td className="py-2.5 px-3 text-zinc-400">
                          {d.snapshot_id ? d.snapshot_id.slice(0, 8) : 'Auto'}
                        </td>
                        <td className="py-2.5 px-3 capitalize text-zinc-400">
                          {d.drill_type}
                        </td>
                        <td className="py-2.5 px-3">
                          <Badge
                            variant={
                              d.status === 'SUCCESS'
                                ? 'emerald'
                                : d.status === 'FAILED'
                                ? 'rose'
                                : 'amber'
                            }
                            dot
                          >
                            {d.status}
                          </Badge>
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-1.5">
                            <span className="text-zinc-200">{d.duration_seconds.toFixed(2)}s</span>
                            <span className="text-zinc-500">/ {d.rto_target_seconds}s</span>
                            <Badge variant={d.rto_compliant ? 'emerald' : 'rose'}>
                              {d.rto_compliant ? 'SLA Met' : 'Breached'}
                            </Badge>
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-zinc-300">
                          <span className="text-emerald-400 font-bold">{d.matched_files}</span> matched
                          {d.corrupted_files > 0 && (
                            <span className="text-rose-400 ml-1.5 font-bold">
                              • {d.corrupted_files} corrupted
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <a
                            href={`/api/reports/download/drill/${d.drill_id}.html`}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 underline"
                          >
                            <Download className="w-3 h-3" />
                            HTML
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: SNAPSHOT INTEGRITY & DRIFT ANALYSIS */}
      {/* ========================================================================= */}
      {activeTab === 'drift' && (
        <div className="space-y-6">
          <Card className="space-y-4">
            <CardHeader>
              <div className="flex items-center gap-2">
                <GitCompare className="w-4 h-4 text-cyan-400" />
                <CardTitle>Snapshot Manifest Drift & Volumetric Anomaly Analysis</CardTitle>
              </div>
              <CardDescription>
                Compare snapshots or evaluate current live directory against a baseline to detect file-level churn, volumetric surges, and explainable forensic anomalies.
              </CardDescription>
            </CardHeader>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  Base Snapshot (Baseline):
                </label>
                <select
                  value={baseSnapshotId}
                  onChange={(e) => setBaseSnapshotId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 font-mono focus:outline-none focus:border-border-active"
                >
                  {snapshots.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.short_id || s.id.slice(0, 8)} — {new Date(s.time).toLocaleDateString()}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  Target Snapshot or State:
                </label>
                <select
                  value={targetSnapshotId}
                  onChange={(e) => setTargetSnapshotId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 font-mono focus:outline-none focus:border-border-active"
                >
                  <option value="current">Current Live Source Tree (data/lab_source)</option>
                  {snapshots.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.short_id || s.id.slice(0, 8)} — {new Date(s.time).toLocaleDateString()}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-end">
                <Button
                  className="w-full"
                  variant="primary"
                  isLoading={analyzingDrift}
                  disabled={!baseSnapshotId}
                  onClick={handleAnalyzeDrift}
                  leftIcon={<GitCompare className="w-3.5 h-3.5" />}
                >
                  Analyze Content Drift
                </Button>
              </div>
            </div>
          </Card>

          {/* Drift Analysis Findings */}
          {driftReport && (
            <Card className="space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-subtle pb-4">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-100">
                    Drift Assessment: {driftReport.base_snapshot_id.slice(0, 8)} vs{' '}
                    {driftReport.target_snapshot_id === 'current'
                      ? 'Live Source'
                      : driftReport.target_snapshot_id.slice(0, 8)}
                  </h3>
                  <p className="text-[11px] text-zinc-400 font-mono mt-0.5">
                    Evaluated at {new Date(driftReport.timestamp).toLocaleString()}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {driftReport.anomaly_flags.length === 0 ? (
                    <Badge variant="emerald" dot>
                      Normal Operational Drift
                    </Badge>
                  ) : (
                    <Badge variant="amber" dot>
                      {driftReport.anomaly_flags.length} Anomaly Flag(s) Raised
                    </Badge>
                  )}
                </div>
              </div>

              {/* Anomaly Explanations Banner */}
              {driftReport.anomaly_explanations.length > 0 && (
                <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-semibold text-amber-300">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span>Explainable Forensic Anomalies Detected</span>
                  </div>
                  <ul className="text-xs text-amber-200/90 space-y-1 list-disc pl-5">
                    {driftReport.anomaly_explanations.map((exp, idx) => (
                      <li key={idx}>{exp}</li>
                    ))}
                  </ul>
                  <p className="text-[11px] text-zinc-400 pt-1 italic">
                    Note: Anomaly flags indicate statistical deviations from baseline. They do not represent definitive claims of malware or ransomware.
                  </p>
                </div>
              )}

              {/* 4 Stat Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-surface-2 border border-border-subtle">
                  <div className="text-[10px] text-zinc-500 uppercase font-mono">Added Files</div>
                  <div className="text-xl font-mono font-bold text-emerald-400 mt-1">
                    +{driftReport.added_files.length}
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-surface-2 border border-border-subtle">
                  <div className="text-[10px] text-zinc-500 uppercase font-mono">Modified Files</div>
                  <div className="text-xl font-mono font-bold text-cyan-400 mt-1">
                    {driftReport.modified_files.length}
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-surface-2 border border-border-subtle">
                  <div className="text-[10px] text-zinc-500 uppercase font-mono">Removed Files</div>
                  <div className="text-xl font-mono font-bold text-rose-400 mt-1">
                    -{driftReport.removed_files.length}
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-surface-2 border border-border-subtle">
                  <div className="text-[10px] text-zinc-500 uppercase font-mono">Volumetric Swing</div>
                  <div className="text-xl font-mono font-bold text-zinc-200 mt-1">
                    {driftReport.percent_size_change > 0 ? `+${driftReport.percent_size_change}%` : `${driftReport.percent_size_change}%`}
                  </div>
                  <div className="text-[10px] text-zinc-500 mt-0.5">
                    {(driftReport.size_change_bytes / 1024).toFixed(1)} KB delta
                  </div>
                </div>
              </div>

              {/* Sample Files Lists */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                {driftReport.modified_files.length > 0 && (
                  <div className="p-3 rounded-lg bg-surface-2 border border-border-subtle">
                    <span className="text-zinc-400 font-semibold block mb-2">Modified Files Sample:</span>
                    <ul className="text-zinc-300 space-y-1 max-h-36 overflow-y-auto">
                      {driftReport.modified_files.slice(0, 10).map((f) => (
                        <li key={f} className="truncate">• {f}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {driftReport.removed_files.length > 0 && (
                  <div className="p-3 rounded-lg bg-surface-2 border border-border-subtle">
                    <span className="text-zinc-400 font-semibold block mb-2">Removed Files Sample:</span>
                    <ul className="text-rose-300 space-y-1 max-h-36 overflow-y-auto">
                      {driftReport.removed_files.slice(0, 10).map((f) => (
                        <li key={f} className="truncate">• {f}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
