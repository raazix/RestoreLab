import React, { useEffect, useState } from 'react'
import {
  FileText,
  Copy,
  Check,
  Download,
  ShieldCheck,
  Hash,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Layers,
  Code2,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { api, Incident, RestoreAttempt, RecoveryDrill } from '@/lib/api'

export const ReportsView: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [restoreAttempts, setRestoreAttempts] = useState<RestoreAttempt[]>([])
  const [drills, setDrills] = useState<RecoveryDrill[]>([])

  const [selectedIncidentId, setSelectedIncidentId] = useState<string>('')
  const [selectedAttemptId, setSelectedAttemptId] = useState<string>('')
  const [selectedDrillId, setSelectedDrillId] = useState<string>('')

  const [reportMarkdown, setReportMarkdown] = useState<string>('')
  const [reportHtml, setReportHtml] = useState<string>('')
  const [reportJson, setReportJson] = useState<string>('')
  const [reportFingerprint, setReportFingerprint] = useState<string>('')
  const [reportTitle, setReportTitle] = useState<string>('')
  const [downloadHtmlUrl, setDownloadHtmlUrl] = useState<string | null>(null)
  const [loadingReport, setLoadingReport] = useState(false)
  const [copied, setCopied] = useState(false)

  const fetchData = async () => {
    try {
      const [incData, dashData, drillData] = await Promise.all([
        api.getIncidents(undefined, 20),
        api.getDashboard(),
        api.getDrills(20),
      ])
      setIncidents(incData)
      setRestoreAttempts(dashData.recent_restore_attempts)
      setDrills(drillData)

      if (incData.length > 0) {
        setSelectedIncidentId(incData[0].incident_id)
      }
      if (dashData.recent_restore_attempts.length > 0) {
        setSelectedAttemptId(dashData.recent_restore_attempts[0].attempt_id)
      }
      if (drillData.length > 0) {
        setSelectedDrillId(drillData[0].drill_id)
      }
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleGenerateIncidentReport = async (incId: string) => {
    if (!incId) return
    setLoadingReport(true)
    setDownloadHtmlUrl(null)
    setReportHtml('')
    setReportJson('')
    try {
      const data = await api.getIncidentReport(incId)
      setReportMarkdown(data.markdown)
      setReportFingerprint(data.sha256_fingerprint)
      setReportTitle(data.title)
    } catch (err: any) {
      alert(`Failed to generate report: ${err.message}`)
    } finally {
      setLoadingReport(false)
    }
  }

  const handleGenerateRestoreReport = async (attId: string) => {
    if (!attId) return
    setLoadingReport(true)
    try {
      const data = await api.getRestoreReport(attId)
      setReportMarkdown(data.markdown)
      setReportFingerprint(data.sha256_fingerprint)
      setReportTitle(`Restore Audit — Snapshot ${data.snapshot_id.slice(0, 8)}`)
      setDownloadHtmlUrl(`/api/reports/download/restore/${attId}.html`)
    } catch (err: any) {
      alert(`Failed to generate report: ${err.message}`)
    } finally {
      setLoadingReport(false)
    }
  }

  const handleGenerateDrillReport = async (dId: string) => {
    if (!dId) return
    setLoadingReport(true)
    try {
      const data = await api.getDrillReport(dId)
      setReportHtml(data.html)
      setReportJson(data.json)
      setReportFingerprint(data.sha256_fingerprint)
      setReportTitle(`Recovery Drill Audit — ${data.drill_id}`)
      setDownloadHtmlUrl(`/api/reports/download/drill/${dId}.html`)
      setReportMarkdown(`/* Standalone HTML and JSON audit artifacts ready for drill ${data.drill_id}. Click buttons below to download or view. */`)
    } catch (err: any) {
      alert(`Failed to generate drill report: ${err.message}`)
    } finally {
      setLoadingReport(false)
    }
  }

  const handleGenerateReadinessReport = async () => {
    setLoadingReport(true)
    try {
      const data = await api.getReadinessReport()
      setReportHtml(data.html)
      setReportJson(data.json)
      setReportFingerprint(data.sha256_fingerprint)
      setReportTitle(`DR Readiness Assessment — Score: ${data.score}/100 (${data.tier})`)
      setDownloadHtmlUrl('/api/reports/download/readiness.html')
      setReportMarkdown(`/* Full Disaster Recovery Readiness HTML audit report generated. Click "Download Standalone HTML" to inspect with browser formatting. */`)
    } catch (err: any) {
      alert(`Failed to generate readiness report: ${err.message}`)
    } finally {
      setLoadingReport(false)
    }
  }

  const copyContent = () => {
    navigator.clipboard.writeText(reportMarkdown || reportJson || reportHtml)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const downloadText = (content: string, filename: string, mime: string) => {
    const blob = new Blob([content], { type: mime })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* View Header */}
      <div>
        <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
          Hashed Evidence & Certified Audit Exports
        </h2>
        <p className="text-xs text-zinc-400 mt-1 max-w-2xl leading-relaxed">
          Export formal compliance certificates, recovery drill audits, and post-mortems in HTML, JSON, and Markdown formats with cryptographic SHA-256 integrity signatures.
        </p>
      </div>

      {/* Selectors Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Incident Post-Mortem Card */}
        <Card className="flex flex-col justify-between space-y-3">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <CardTitle>Incident Post-Mortems</CardTitle>
            </div>
          </CardHeader>

          <select
            value={selectedIncidentId}
            onChange={(e) => {
              setSelectedIncidentId(e.target.value)
              handleGenerateIncidentReport(e.target.value)
            }}
            className="w-full px-3 py-1.5 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 focus:outline-none"
          >
            <option value="">Select an incident...</option>
            {incidents.map((i) => (
              <option key={i.incident_id} value={i.incident_id}>
                {i.incident_id}: {i.title.slice(0, 24)}...
              </option>
            ))}
          </select>

          <Button
            size="sm"
            variant="secondary"
            disabled={!selectedIncidentId}
            onClick={() => handleGenerateIncidentReport(selectedIncidentId)}
            leftIcon={<FileText className="w-3.5 h-3.5" />}
          >
            Generate Post-Mortem
          </Button>
        </Card>

        {/* Recovery Verification Report Card */}
        <Card className="flex flex-col justify-between space-y-3">
          <CardHeader>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <CardTitle>Restore Verifications</CardTitle>
            </div>
          </CardHeader>

          <select
            value={selectedAttemptId}
            onChange={(e) => {
              setSelectedAttemptId(e.target.value)
              handleGenerateRestoreReport(e.target.value)
            }}
            className="w-full px-3 py-1.5 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 focus:outline-none"
          >
            <option value="">Select verification attempt...</option>
            {restoreAttempts.map((a) => (
              <option key={a.attempt_id} value={a.attempt_id}>
                Snap {a.snapshot_id.slice(0, 8)} ({a.status})
              </option>
            ))}
          </select>

          <Button
            size="sm"
            variant="secondary"
            disabled={!selectedAttemptId}
            onClick={() => handleGenerateRestoreReport(selectedAttemptId)}
            leftIcon={<FileText className="w-3.5 h-3.5" />}
          >
            Generate Verification Audit
          </Button>
        </Card>

        {/* Recovery Drill Audit Card */}
        <Card className="flex flex-col justify-between space-y-3">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <CardTitle>Recovery Drill Audits</CardTitle>
            </div>
          </CardHeader>

          <select
            value={selectedDrillId}
            onChange={(e) => {
              setSelectedDrillId(e.target.value)
              handleGenerateDrillReport(e.target.value)
            }}
            className="w-full px-3 py-1.5 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 focus:outline-none"
          >
            <option value="">Select recovery drill...</option>
            {drills.map((d) => (
              <option key={d.drill_id} value={d.drill_id}>
                {d.drill_id} ({d.status} • {d.duration_seconds.toFixed(1)}s)
              </option>
            ))}
          </select>

          <Button
            size="sm"
            variant="secondary"
            disabled={!selectedDrillId}
            onClick={() => handleGenerateDrillReport(selectedDrillId)}
            leftIcon={<Activity className="w-3.5 h-3.5" />}
          >
            Generate Drill Certificate
          </Button>
        </Card>

        {/* Global DR Readiness Audit Card */}
        <Card className="flex flex-col justify-between space-y-3">
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-indigo-400" />
              <CardTitle>DR Readiness Audit</CardTitle>
            </div>
          </CardHeader>

          <p className="text-[11px] text-zinc-400">
            Generate executive certificate containing composite readiness scoring, RTO SLA metrics, and limitations.
          </p>

          <Button
            size="sm"
            variant="primary"
            onClick={handleGenerateReadinessReport}
            leftIcon={<ShieldCheck className="w-3.5 h-3.5" />}
          >
            Export DR Readiness Audit
          </Button>
        </Card>
      </div>

      {/* Generated Report Preview Panel */}
      {(reportMarkdown || reportHtml || reportJson) && (
        <Card className="space-y-4">
          <CardHeader>
            <div>
              <CardTitle className="flex items-center gap-2">
                <span>{reportTitle || 'Audit Certificate'}</span>
                <Badge variant="cyan" className="font-mono text-[10px]">
                  SHA-256 Fingerprint: {reportFingerprint.slice(0, 12)}...
                </Badge>
              </CardTitle>
              <CardDescription>
                Cryptographic Signature: <span className="font-mono text-zinc-400">{reportFingerprint}</span>
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={copyContent}
                leftIcon={copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              >
                {copied ? 'Copied' : 'Copy'}
              </Button>

              {downloadHtmlUrl && (
                <a
                  href={downloadHtmlUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white shadow-sm"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download HTML Certificate
                </a>
              )}

              {reportJson && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => downloadText(reportJson, `audit_${reportFingerprint.slice(0, 8)}.json`, 'application/json')}
                  leftIcon={<Code2 className="w-3.5 h-3.5" />}
                >
                  Download JSON
                </Button>
              )}

              {reportMarkdown && !reportHtml && (
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => downloadText(reportMarkdown, `report_${reportFingerprint.slice(0, 8)}.md`, 'text/markdown')}
                  leftIcon={<Download className="w-3.5 h-3.5" />}
                >
                  Download (.md)
                </Button>
              )}
            </div>
          </CardHeader>

          <div className="bg-black/60 rounded-lg p-4 font-mono text-xs text-zinc-300 max-h-96 overflow-y-auto whitespace-pre-wrap border border-border-subtle leading-relaxed">
            {reportJson ? reportJson : reportMarkdown}
          </div>
        </Card>
      )}
    </div>
  )
}
