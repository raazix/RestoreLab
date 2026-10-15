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
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { api, Incident, RestoreAttempt } from '@/lib/api'

export const ReportsView: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [restoreAttempts, setRestoreAttempts] = useState<RestoreAttempt[]>([])
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>('')
  const [selectedAttemptId, setSelectedAttemptId] = useState<string>('')

  const [reportMarkdown, setReportMarkdown] = useState<string>('')
  const [reportFingerprint, setReportFingerprint] = useState<string>('')
  const [reportTitle, setReportTitle] = useState<string>('')
  const [loadingReport, setLoadingReport] = useState(false)
  const [copied, setCopied] = useState(false)

  const fetchData = async () => {
    try {
      const [incData, dashData] = await Promise.all([
        api.getIncidents(undefined, 20),
        api.getDashboard(),
      ])
      setIncidents(incData)
      setRestoreAttempts(dashData.recent_restore_attempts)

      if (incData.length > 0) {
        setSelectedIncidentId(incData[0].incident_id)
      } else if (dashData.recent_restore_attempts.length > 0) {
        setSelectedAttemptId(dashData.recent_restore_attempts[0].attempt_id)
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
    } catch (err: any) {
      alert(`Failed to generate report: ${err.message}`)
    } finally {
      setLoadingReport(false)
    }
  }

  const copyMarkdown = () => {
    navigator.clipboard.writeText(reportMarkdown)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const downloadMarkdown = () => {
    const blob = new Blob([reportMarkdown], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${reportFingerprint.slice(0, 8)}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* View Header */}
      <div>
        <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
          Hashed Audit & Post-Mortem Exports
        </h2>
        <p className="text-xs text-zinc-400 mt-1 max-w-2xl leading-relaxed">
          Generate formal Markdown post-mortems and cryptographic verification reports
          with independent SHA-256 document fingerprints for compliance and incident reviews.
        </p>
      </div>

      {/* Selectors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Incident Post-Mortem Card */}
        <Card className="space-y-3">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <CardTitle>Incident Post-Mortem Report</CardTitle>
            </div>
          </CardHeader>

          <select
            value={selectedIncidentId}
            onChange={(e) => {
              setSelectedIncidentId(e.target.value)
              handleGenerateIncidentReport(e.target.value)
            }}
            className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 focus:outline-none"
          >
            <option value="">Select an incident...</option>
            {incidents.map((i) => (
              <option key={i.incident_id} value={i.incident_id}>
                {i.incident_id}: {i.title} ({i.status.toUpperCase()})
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
            Generate Post-Mortem Markdown
          </Button>
        </Card>

        {/* Recovery Verification Report Card */}
        <Card className="space-y-3">
          <CardHeader>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <CardTitle>Cryptographic Verification Audit</CardTitle>
            </div>
          </CardHeader>

          <select
            value={selectedAttemptId}
            onChange={(e) => {
              setSelectedAttemptId(e.target.value)
              handleGenerateRestoreReport(e.target.value)
            }}
            className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-border-muted text-xs text-zinc-200 focus:outline-none"
          >
            <option value="">Select a restore verification attempt...</option>
            {restoreAttempts.map((a) => (
              <option key={a.attempt_id} value={a.attempt_id}>
                Audit {a.attempt_id.slice(0, 8)}: Snapshot {a.snapshot_id.slice(0, 8)} ({a.status})
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
            Generate Verification Report
          </Button>
        </Card>
      </div>

      {/* Generated Report Preview */}
      {reportMarkdown && (
        <Card className="space-y-4">
          <CardHeader>
            <div>
              <CardTitle className="flex items-center gap-2">
                <span>{reportTitle || 'Audit Report'}</span>
                <Badge variant="cyan" className="font-mono text-[10px]">
                  SHA-256 Fingerprint: {reportFingerprint.slice(0, 12)}...
                </Badge>
              </CardTitle>
              <CardDescription>
                Full SHA-256 Digest: <span className="font-mono text-zinc-400">{reportFingerprint}</span>
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={copyMarkdown}
                leftIcon={
                  copied ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )
                }
              >
                {copied ? 'Copied' : 'Copy'}
              </Button>
              <Button
                size="sm"
                variant="primary"
                onClick={downloadMarkdown}
                leftIcon={<Download className="w-3.5 h-3.5" />}
              >
                Download (.md)
              </Button>
            </div>
          </CardHeader>

          <div className="bg-black/60 rounded-lg p-4 font-mono text-xs text-zinc-300 max-h-96 overflow-y-auto whitespace-pre-wrap border border-border-subtle leading-relaxed">
            {reportMarkdown}
          </div>
        </Card>
      )}
    </div>
  )
}
