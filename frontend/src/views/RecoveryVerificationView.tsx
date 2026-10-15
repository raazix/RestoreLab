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
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { api, Snapshot, VerificationReport, SystemStatus } from '@/lib/api'

interface RecoveryVerificationViewProps {
  systemStatus: SystemStatus | null
  onRefreshMetrics: () => void
}

export const RecoveryVerificationView: React.FC<RecoveryVerificationViewProps> = ({
  systemStatus,
  onRefreshMetrics,
}) => {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [loadingSnapshots, setLoadingSnapshots] = useState(false)
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string>('')
  const [subfolder, setSubfolder] = useState<string>('')

  const [verifying, setVerifying] = useState(false)
  const [verificationReport, setVerificationReport] = useState<VerificationReport | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [copiedText, setCopiedText] = useState<string | null>(null)

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
      if (data.length > 0 && !selectedSnapshotId) {
        setSelectedSnapshotId(data[0].id)
      }
    } catch (err: any) {
      setErrorMsg(`Failed to load snapshots: ${err.message}`)
    } finally {
      setLoadingSnapshots(false)
    }
  }

  useEffect(() => {
    fetchSnapshots()
  }, [])

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

  const selectedSnapshot = snapshots.find((s) => s.id === selectedSnapshotId)

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* View Header */}
      <div>
        <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
          Recovery Verification & Cryptographic Auditing
        </h2>
        <p className="text-xs text-zinc-400 mt-1 max-w-2xl leading-relaxed">
          Restore snapshots into isolated sandboxes and compute post-restore SHA-256 manifests.
          Guarantees clean room isolation and catches silent corruption before production deployment.
        </p>
      </div>

      {/* Snapshot Selection & Controls */}
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
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
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

              {/* Subfolder override input */}
              <div className="pt-2">
                <label className="text-[11px] font-medium text-zinc-400 block mb-1">
                  Optional Subfolder Scope (Restore subfolder directly):
                </label>
                <input
                  type="text"
                  placeholder="e.g. data or subfolder (leave blank for complete snapshot)"
                  value={subfolder}
                  onChange={(e) => setSubfolder(e.target.value)}
                  className="w-full px-3 py-1.5 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 placeholder-zinc-500 font-mono focus:outline-none focus:border-border-active"
                />
              </div>
            </div>
          )}
        </Card>

        {/* Right: Destination Safety & Verification Dispatch */}
        <Card className="flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <CardTitle>Destination Safety Guards</CardTitle>
            </div>
            <CardDescription>
              Enforces strict destination containment. Restores are isolated inside timestamped
              sandboxes within <code className="text-zinc-300">./data/lab_restore/</code>.
            </CardDescription>

            <div className="p-3 rounded-lg bg-surface-2 border border-border-subtle space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Target Isolation:</span>
                <Badge variant="emerald" dot>
                  Sandbox Enforced
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">In-Place Overwrites:</span>
                <Badge variant="zinc">Blocked</Badge>
              </div>
            </div>
          </div>

          <Button
            className="w-full"
            variant="primary"
            isLoading={verifying}
            disabled={!selectedSnapshotId}
            onClick={handleVerify}
            leftIcon={<CheckCircle2 className="w-4 h-4" />}
          >
            Execute Restore & Verify
          </Button>
        </Card>
      </div>

      {/* Error Notice */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Verification Report Display */}
      {verificationReport && (
        <Card className="space-y-6">
          {/* Status Banner */}
          <div
            className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
              verificationReport.status === 'PASSED'
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
            }`}
          >
            <div className="flex items-center gap-3">
              {verificationReport.status === 'PASSED' ? (
                <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
              ) : (
                <ShieldAlert className="w-6 h-6 text-rose-400 shrink-0" />
              )}
              <div>
                <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                  <span>
                    {verificationReport.status === 'PASSED'
                      ? 'PASSED: 100% Byte-Level Recovery Verified'
                      : `VERIFICATION FAILED: ${verificationReport.status}`}
                  </span>
                  <Badge
                    variant={verificationReport.status === 'PASSED' ? 'emerald' : 'rose'}
                    dot
                  >
                    {verificationReport.status}
                  </Badge>
                </h3>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Snapshot: <span className="font-mono">{verificationReport.snapshot_id.slice(0, 8)}</span> |
                  Restore Duration: <span className="font-mono">{verificationReport.restore_duration_seconds.toFixed(2)}s</span> |
                  Audit Duration: <span className="font-mono">{verificationReport.verification_duration_seconds.toFixed(2)}s</span>
                </p>
              </div>
            </div>

            {/* Metrics Chips */}
            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="px-2.5 py-1 rounded-md bg-surface-3 text-emerald-400 border border-border-subtle">
                {verificationReport.comparison_result?.matched_count ?? 0} Matched
              </span>
              {(verificationReport.comparison_result?.corrupted_count ?? 0) > 0 && (
                <span className="px-2.5 py-1 rounded-md bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold">
                  {verificationReport.comparison_result?.corrupted_count} Corrupted
                </span>
              )}
              {(verificationReport.comparison_result?.missing_count ?? 0) > 0 && (
                <span className="px-2.5 py-1 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  {verificationReport.comparison_result?.missing_count} Missing
                </span>
              )}
            </div>
          </div>

          {/* File-by-File Comparison Table */}
          {verificationReport.comparison_result?.file_diffs && (
            <div>
              <CardHeader>
                <div>
                  <CardTitle>File-by-File Cryptographic Audit Details</CardTitle>
                  <CardDescription>
                    Direct comparison of expected pre-backup SHA-256 vs. restored actual SHA-256
                  </CardDescription>
                </div>
              </CardHeader>

              <div className="overflow-x-auto max-h-80">
                <table className="w-full text-left text-xs">
                  <thead className="bg-surface-2 text-zinc-400 font-mono text-[11px] sticky top-0">
                    <tr>
                      <th className="py-2.5 px-3">File Path</th>
                      <th className="py-2.5 px-3">Integrity Status</th>
                      <th className="py-2.5 px-3">Expected SHA-256</th>
                      <th className="py-2.5 px-3">Restored Actual SHA-256</th>
                      <th className="py-2.5 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-subtle font-mono text-[11px]">
                    {verificationReport.comparison_result.file_diffs.map((diff) => (
                      <tr key={diff.path} className="hover:bg-surface-2/40 transition-colors">
                        <td className="py-2 px-3 text-zinc-200 font-medium">{diff.path}</td>
                        <td className="py-2 px-3">
                          <Badge
                            variant={
                              diff.status === 'MATCHED'
                                ? 'emerald'
                                : diff.status === 'CORRUPTED'
                                ? 'rose'
                                : 'amber'
                            }
                            dot={diff.status !== 'MATCHED'}
                          >
                            {diff.status}
                          </Badge>
                        </td>
                        <td className="py-2 px-3 text-zinc-400 truncate max-w-xs">
                          {diff.expected_hash || '-'}
                        </td>
                        <td className="py-2 px-3 text-zinc-400 truncate max-w-xs">
                          {diff.actual_hash || '-'}
                        </td>
                        <td className="py-2 px-3 text-right">
                          <button
                            onClick={() => copyToClipboard(diff.actual_hash || diff.expected_hash || '')}
                            className="text-zinc-500 hover:text-zinc-200 p-1 rounded"
                            title="Copy Hash"
                          >
                            {copiedText === (diff.actual_hash || diff.expected_hash) ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
