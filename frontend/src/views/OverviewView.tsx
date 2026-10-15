import React from 'react'
import {
  HardDrive,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  ArrowUpRight,
  Clock,
  FileCheck2,
  Layers,
  ChevronRight,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { DashboardMetrics, ReadinessAssessment, SystemStatus, api } from '@/lib/api'
import { Download, Sparkles, Activity } from 'lucide-react'

interface OverviewViewProps {
  metrics: DashboardMetrics | null
  systemStatus: SystemStatus | null
  onNavigate: (view: string) => void
  onRefresh: () => void
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  metrics,
  systemStatus,
  onNavigate,
  onRefresh,
}) => {
  const [readiness, setReadiness] = React.useState<ReadinessAssessment | null>(null)
  const [showLimitations, setShowLimitations] = React.useState(false)

  const fetchReadiness = async () => {
    try {
      const data = await api.getReadiness()
      setReadiness(data)
    } catch (err) {
      console.error('Failed to load readiness', err)
    }
  }

  React.useEffect(() => {
    fetchReadiness()
  }, [])

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Banner: Reliability Ground Truth */}
      <div className="linear-panel rounded-xl p-5 border border-border-subtle relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-96 bg-gradient-to-l from-indigo-500/10 to-transparent pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
                Reliability Engineering Dashboard
              </h2>
              <Badge variant="cyan" className="font-mono text-[10px]">
                Deterministic Rules v1.0
              </Badge>
            </div>
            <p className="text-xs text-zinc-400 max-w-2xl leading-relaxed">
              Evidence before conclusions. Cryptographic SHA-256 manifest auditing, isolated
              sandbox recovery, and case-based incident investigation for production backups.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={onRefresh}
              leftIcon={<Clock className="w-3.5 h-3.5 text-zinc-400" />}
            >
              Refresh Stats
            </Button>
            <Button
              size="sm"
              variant="primary"
              onClick={() => onNavigate('backup')}
              rightIcon={<ArrowUpRight className="w-3.5 h-3.5" />}
            >
              New Backup
            </Button>
          </div>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <Card className="flex flex-col justify-between">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-medium">
            <span>Total Backup Runs</span>
            <HardDrive className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-4">
            <span className="text-2xl font-bold font-mono text-zinc-100">
              {metrics?.total_backups ?? 0}
            </span>
            <div className="mt-1 flex items-center gap-1.5 text-[11px] text-zinc-500">
              <span>ACID Logged in SQLite</span>
            </div>
          </div>
        </Card>

        {/* Metric 2 */}
        <Card className="flex flex-col justify-between">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-medium">
            <span>Verified Restores</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-4">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono text-zinc-100">
                {metrics?.passed_restores ?? 0}
              </span>
              <span className="text-xs text-zinc-500 font-mono">
                / {metrics?.total_restores ?? 0} total
              </span>
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-[11px] text-emerald-400/90 font-medium">
              <span>{metrics?.verification_ratio ?? 0}% byte-verified</span>
            </div>
          </div>
        </Card>

        {/* Metric 3 */}
        <Card className="flex flex-col justify-between">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-medium">
            <span>Open Incidents</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="mt-4">
            <span className="text-2xl font-bold font-mono text-zinc-100">
              {metrics?.open_incidents_count ?? 0}
            </span>
            <div className="mt-1 flex items-center gap-1.5 text-[11px] text-zinc-500">
              <span>Awaiting root-cause triage</span>
            </div>
          </div>
        </Card>

        {/* Metric 4 */}
        <Card className="flex flex-col justify-between">
          <div className="flex items-center justify-between text-zinc-400 text-xs font-medium">
            <span>Repository Health</span>
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="mt-4">
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold text-zinc-100">
                {metrics?.last_integrity_check_passed !== false ? 'Valid & Clean' : 'Issues Detected'}
              </span>
              <Badge
                variant={metrics?.last_integrity_check_passed !== false ? 'emerald' : 'rose'}
                dot
              >
                {metrics?.last_integrity_check_passed !== false ? 'Passed' : 'Attention'}
              </Badge>
            </div>
            <div className="mt-1 text-[11px] text-zinc-500 truncate">
              {systemStatus?.repository_path || 'Encrypted Local Restic'}
            </div>
          </div>
        </Card>
      </div>

      {/* Disaster Recovery Readiness Analytics Panel */}
      {readiness && (
        <Card className="border-indigo-500/30 bg-gradient-to-r from-surface-1 via-surface-2 to-surface-1">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            {/* Score & Tier */}
            <div className="flex items-center gap-4">
              <div className="relative flex items-center justify-center w-20 h-20 rounded-2xl bg-surface-3 border border-indigo-500/40 shadow-subtle">
                <div className="text-center">
                  <div className="text-2xl font-bold font-mono text-zinc-100">
                    {readiness.score}
                  </div>
                  <div className="text-[10px] text-zinc-400 font-mono -mt-0.5">/ 100</div>
                </div>
              </div>

              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-zinc-100">
                    Disaster Recovery Readiness Score
                  </span>
                  <Badge
                    variant={
                      readiness.readiness_tier === 'OPTIMAL'
                        ? 'emerald'
                        : readiness.readiness_tier === 'ACCEPTABLE'
                        ? 'cyan'
                        : readiness.readiness_tier === 'DEGRADED'
                        ? 'amber'
                        : 'rose'
                    }
                    dot
                  >
                    Tier: {readiness.readiness_tier}
                  </Badge>
                </div>
                <p className="text-xs text-zinc-400 max-w-xl">
                  Multi-factor composite readiness derived from recovery drill verification pass rates, RTO SLA compliance, and snapshot age.
                </p>
              </div>
            </div>

            {/* Sub-Metrics & Actions */}
            <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
              <div className="p-2.5 rounded-lg bg-surface-3/80 border border-border-subtle">
                <div className="text-[10px] text-zinc-500 uppercase">Snapshot Coverage</div>
                <div className="text-sm font-bold text-zinc-200 mt-0.5">
                  {readiness.coverage_ratio}% ({readiness.tested_snapshots_count}/{readiness.total_eligible_snapshots})
                </div>
              </div>

              <div className="p-2.5 rounded-lg bg-surface-3/80 border border-border-subtle">
                <div className="text-[10px] text-zinc-500 uppercase">RTO SLA Compliance</div>
                <div className="text-sm font-bold text-emerald-400 mt-0.5">
                  {readiness.rto_compliance_rate}%
                </div>
              </div>

              <div className="p-2.5 rounded-lg bg-surface-3/80 border border-border-subtle">
                <div className="text-[10px] text-zinc-500 uppercase">Avg Restore Duration</div>
                <div className="text-sm font-bold text-zinc-200 mt-0.5">
                  {readiness.average_restore_seconds.toFixed(2)}s
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => onNavigate('recovery')}
                  leftIcon={<Activity className="w-3.5 h-3.5" />}
                >
                  Run Recovery Drill
                </Button>
                <a
                  href="/api/reports/download/readiness.html"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center justify-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 font-sans"
                >
                  <Download className="w-3 h-3" />
                  Download Signed HTML Audit
                </a>
              </div>
            </div>
          </div>

          {/* Transparent Metric Limitations Toggle */}
          <div className="mt-4 pt-3 border-t border-border-subtle flex flex-col gap-1.5">
            <button
              onClick={() => setShowLimitations(!showLimitations)}
              className="text-[11px] text-zinc-500 hover:text-zinc-300 flex items-center gap-1 font-mono text-left"
            >
              <span>{showLimitations ? '▼ Hide' : '▶ Show'} Documented Metric Limitations & Assumptions</span>
            </button>
            {showLimitations && (
              <ul className="text-[11px] text-zinc-400 font-mono space-y-1 list-disc pl-5 mt-1 bg-surface-3/50 p-2.5 rounded border border-border-subtle">
                {readiness.metric_limitations.map((lim, i) => (
                  <li key={i}>{lim}</li>
                ))}
              </ul>
            )}
          </div>
        </Card>
      )}

      {/* Main Grid: Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Recent Backups */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Recent Backup Runs</CardTitle>
              <CardDescription>Subprocess execution audits and snapshot registrations</CardDescription>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onNavigate('backup')}
              rightIcon={<ChevronRight className="w-3.5 h-3.5" />}
            >
              View all
            </Button>
          </CardHeader>

          <div className="divide-y divide-border-subtle">
            {metrics?.recent_backup_runs && metrics.recent_backup_runs.length > 0 ? (
              metrics.recent_backup_runs.map((run) => (
                <div
                  key={run.run_id}
                  className="py-3 flex items-center justify-between text-xs hover:bg-surface-2/40 px-2 -mx-2 rounded transition-colors"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-zinc-200">
                        {run.snapshot_id ? run.snapshot_id.slice(0, 8) : 'Pending'}
                      </span>
                      <Badge
                        variant={run.status === 'success' ? 'emerald' : 'rose'}
                      >
                        {run.status.toUpperCase()}
                      </Badge>
                    </div>
                    <div className="text-[11px] text-zinc-500 font-mono">
                      {new Date(run.timestamp).toLocaleString()}
                    </div>
                  </div>

                  <div className="text-right space-y-0.5 font-mono text-[11px]">
                    <div className="text-zinc-300">
                      {run.total_files} files ({(run.total_bytes / 1024).toFixed(1)} KB)
                    </div>
                    <div className="text-zinc-500">
                      {run.duration_seconds.toFixed(2)}s
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-zinc-500">
                No backup runs recorded yet. Generate sample data and run your first backup.
              </div>
            )}
          </div>
        </Card>

        {/* Recent Recovery Verifications */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Recent Restores & Verification Audits</CardTitle>
              <CardDescription>Cryptographic SHA-256 byte-by-byte comparisons</CardDescription>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onNavigate('recovery')}
              rightIcon={<ChevronRight className="w-3.5 h-3.5" />}
            >
              View all
            </Button>
          </CardHeader>

          <div className="divide-y divide-border-subtle">
            {metrics?.recent_restore_attempts && metrics.recent_restore_attempts.length > 0 ? (
              metrics.recent_restore_attempts.map((att) => (
                <div
                  key={att.attempt_id}
                  className="py-3 flex items-center justify-between text-xs hover:bg-surface-2/40 px-2 -mx-2 rounded transition-colors"
                >
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-zinc-200">
                        Snapshot {att.snapshot_id ? att.snapshot_id.slice(0, 8) : 'Manual'}
                      </span>
                      <Badge
                        variant={
                          att.status === 'PASSED'
                            ? 'emerald'
                            : att.status === 'FAILED'
                            ? 'rose'
                            : 'amber'
                        }
                        dot
                      >
                        {att.status}
                      </Badge>
                    </div>
                    <div className="text-[11px] text-zinc-500 font-mono">
                      {new Date(att.timestamp).toLocaleString()}
                    </div>
                  </div>

                  <div className="text-right space-y-0.5 font-mono text-[11px]">
                    <div className="text-emerald-400">
                      {att.matched_files} matched
                    </div>
                    {att.corrupted_files > 0 && (
                      <div className="text-rose-400 font-semibold">
                        {att.corrupted_files} corrupted
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-zinc-500">
                No restore verifications recorded yet.
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Open Incidents Ticker */}
      {metrics?.open_incidents && metrics.open_incidents.length > 0 && (
        <Card className="border-amber-500/20 bg-amber-500/[0.02]">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <CardTitle className="text-amber-200">Active Incident Triage</CardTitle>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onNavigate('incidents')}
              rightIcon={<ChevronRight className="w-3.5 h-3.5" />}
            >
              Open Explorer
            </Button>
          </CardHeader>

          <div className="space-y-2">
            {metrics.open_incidents.map((inc) => (
              <div
                key={inc.incident_id}
                onClick={() => onNavigate('incidents')}
                className="p-3 rounded-lg bg-surface-2 border border-border-subtle hover:border-border-muted cursor-pointer flex items-center justify-between text-xs transition-all"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] text-zinc-400">
                      {inc.incident_id}
                    </span>
                    <span className="font-medium text-zinc-200">{inc.title}</span>
                    <Badge variant={inc.severity === 'critical' ? 'rose' : 'amber'}>
                      {inc.severity.toUpperCase()}
                    </Badge>
                  </div>
                  {inc.findings.length > 0 && (
                    <p className="text-[11px] text-zinc-400">
                      Root Cause: {inc.findings[0].root_cause}
                    </p>
                  )}
                </div>

                <div className="font-mono text-[10px] text-zinc-500">
                  {new Date(inc.created_at).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
