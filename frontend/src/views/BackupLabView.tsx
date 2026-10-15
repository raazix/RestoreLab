import React, { useState } from 'react'
import {
  HardDrive,
  FileCode2,
  Check,
  Copy,
  Terminal,
  ShieldCheck,
  Zap,
  RefreshCw,
  FolderPlus,
  Hash,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { api, SystemStatus } from '@/lib/api'

interface BackupLabViewProps {
  systemStatus: SystemStatus | null
  onRefreshMetrics: () => void
}

export const BackupLabView: React.FC<BackupLabViewProps> = ({
  systemStatus,
  onRefreshMetrics,
}) => {
  // Action states
  const [loadingSample, setLoadingSample] = useState(false)
  const [loadingManifest, setLoadingManifest] = useState(false)
  const [loadingInit, setLoadingInit] = useState(false)
  const [loadingBackup, setLoadingBackup] = useState(false)
  const [loadingCheckFast, setLoadingCheckFast] = useState(false)
  const [loadingCheckDeep, setLoadingCheckDeep] = useState(false)

  // Results
  const [sampleResult, setSampleResult] = useState<any>(null)
  const [manifestData, setManifestData] = useState<any>(null)
  const [terminalOutput, setTerminalOutput] = useState<string>('')
  const [lastSnapshotId, setLastSnapshotId] = useState<string | null>(null)
  const [copiedHash, setCopiedHash] = useState<string | null>(null)

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedHash(text)
    setTimeout(() => setCopiedHash(null), 2000)
  }

  // 1. Generate Sample Data
  const handleGenerateSample = async () => {
    setLoadingSample(true)
    try {
      const res = await api.generateSampleData()
      setSampleResult(res)
      setTerminalOutput(`[${new Date().toLocaleTimeString()}] Created ${res.file_count} sample files in ${systemStatus?.lab_source} (${res.total_bytes} bytes total)`)
    } catch (err: any) {
      setTerminalOutput(`[ERROR] Failed to generate sample data: ${err.message}`)
    } finally {
      setLoadingSample(false)
    }
  }

  // 2. Generate Manifest
  const handleGenerateManifest = async () => {
    setLoadingManifest(true)
    try {
      const manifest = await api.generateManifest()
      setManifestData(manifest)
      setTerminalOutput(`[${new Date().toLocaleTimeString()}] Generated pre-backup SHA-256 manifest: ${manifest.id.slice(0, 8)} (${Object.keys(manifest.entries || {}).length} files hashed)`)
    } catch (err: any) {
      setTerminalOutput(`[ERROR] Failed to generate manifest: ${err.message}`)
    } finally {
      setLoadingManifest(false)
    }
  }

  // 3. Init Repo
  const handleInitRepo = async () => {
    setLoadingInit(true)
    try {
      const res = await api.initRepo()
      setTerminalOutput(`[${new Date().toLocaleTimeString()}] restic init finished (exit code ${res.exit_code}):\n${res.stdout || res.stderr}`)
      onRefreshMetrics()
    } catch (err: any) {
      setTerminalOutput(`[ERROR] Failed to initialize repository: ${err.message}`)
    } finally {
      setLoadingInit(false)
    }
  }

  // 4. Run Backup
  const handleRunBackup = async () => {
    setLoadingBackup(true)
    try {
      const res = await api.runBackup(['lab', 'verified'])
      if (res.snapshot_id) {
        setLastSnapshotId(res.snapshot_id)
      }
      setTerminalOutput(`[${new Date().toLocaleTimeString()}] Restic backup completed in ${res.duration_seconds.toFixed(2)}s (Snapshot: ${res.snapshot_id || 'N/A'}):\n${res.stdout || res.stderr}`)
      onRefreshMetrics()
    } catch (err: any) {
      setTerminalOutput(`[ERROR] Backup execution failed: ${err.message}`)
    } finally {
      setLoadingBackup(false)
    }
  }

  // 5. Check Repo
  const handleCheck = async (readData: boolean) => {
    if (readData) setLoadingCheckDeep(true)
    else setLoadingCheckFast(true)

    try {
      const res = await api.checkRepo(readData)
      setTerminalOutput(`[${new Date().toLocaleTimeString()}] restic check ${readData ? '--read-data ' : ''}finished (Passed: ${res.success}):\n${res.stdout || res.stderr}`)
      onRefreshMetrics()
    } catch (err: any) {
      setTerminalOutput(`[ERROR] Integrity check failed: ${err.message}`)
    } finally {
      if (readData) setLoadingCheckDeep(false)
      else setLoadingCheckFast(false)
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Description */}
      <div>
        <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
          Backup Lab & Repository Operations
        </h2>
        <p className="text-xs text-zinc-400 mt-1 max-w-2xl leading-relaxed">
          Manage local encrypted repositories, pre-compute deterministic SHA-256 digests,
          execute isolated backups, and validate repository structural indexes.
        </p>
      </div>

      {/* Grid of Steps */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Step 1: Dataset & Manifest */}
        <Card className="flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-surface-3 border border-border-muted flex items-center justify-center font-mono text-[10px] text-zinc-300">
                1
              </span>
              <CardTitle>Dataset & Manifest</CardTitle>
            </div>
            <CardDescription>
              Populate test sources (configs, binaries, Unicode) and compute cryptographic pre-ingest hashes.
            </CardDescription>
          </div>

          <div className="space-y-2">
            <Button
              className="w-full justify-start"
              variant="secondary"
              isLoading={loadingSample}
              onClick={handleGenerateSample}
              leftIcon={<FolderPlus className="w-3.5 h-3.5 text-amber-400" />}
            >
              Generate Sample Dataset
            </Button>

            <Button
              className="w-full justify-start"
              variant="outline"
              isLoading={loadingManifest}
              onClick={handleGenerateManifest}
              leftIcon={<Hash className="w-3.5 h-3.5 text-cyan-400" />}
            >
              Generate SHA-256 Manifest
            </Button>
          </div>
        </Card>

        {/* Step 2: Encrypted Repository */}
        <Card className="flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-surface-3 border border-border-muted flex items-center justify-center font-mono text-[10px] text-zinc-300">
                2
              </span>
              <CardTitle>Restic Repository</CardTitle>
            </div>
            <CardDescription>
              Local repository encrypted with AES-256-CTR and HMAC-SHA256. Password read strictly from .env.
            </CardDescription>
          </div>

          <div className="space-y-2">
            <div className="p-2 rounded bg-surface-2 border border-border-subtle font-mono text-[11px] text-zinc-400 truncate">
              {systemStatus?.repository_path}
            </div>

            <Button
              className="w-full justify-start"
              variant="secondary"
              isLoading={loadingInit}
              onClick={handleInitRepo}
              leftIcon={<HardDrive className="w-3.5 h-3.5 text-indigo-400" />}
            >
              Initialize Repository (`restic init`)
            </Button>
          </div>
        </Card>

        {/* Step 3: Execute Genuine Backup */}
        <Card className="flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-surface-3 border border-border-muted flex items-center justify-center font-mono text-[10px] text-zinc-300">
                3
              </span>
              <CardTitle>Execute Backup</CardTitle>
            </div>
            <CardDescription>
              Dispatches hardened subprocess wrapper without shell injection or argument secret leakage.
            </CardDescription>
          </div>

          <div className="space-y-2">
            {lastSnapshotId && (
              <div className="flex items-center justify-between p-2 rounded bg-emerald-500/10 border border-emerald-500/20 text-xs">
                <span className="text-emerald-400 font-medium">Last Snapshot:</span>
                <span className="font-mono text-zinc-200">{lastSnapshotId.slice(0, 8)}</span>
              </div>
            )}

            <Button
              className="w-full justify-start"
              variant="primary"
              isLoading={loadingBackup}
              onClick={handleRunBackup}
              leftIcon={<Zap className="w-3.5 h-3.5 text-white" />}
            >
              Execute Real Backup (Restic)
            </Button>
          </div>
        </Card>
      </div>

      {/* Manifest Preview Table (If generated) */}
      {manifestData && manifestData.entries && (
        <Card>
          <CardHeader>
            <div>
              <CardTitle className="flex items-center gap-2">
                <span>Pre-Backup Baseline Manifest</span>
                <Badge variant="cyan" className="font-mono text-[10px]">
                  {manifestData.id.slice(0, 8)}
                </Badge>
              </CardTitle>
              <CardDescription>
                Canonical tree hash: <span className="font-mono">{manifestData.canonical_hash}</span>
              </CardDescription>
            </div>
            <div className="text-xs text-zinc-400 font-mono">
              {Object.keys(manifestData.entries).length} files tracked
            </div>
          </CardHeader>

          <div className="overflow-x-auto max-h-64">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-2/60 text-zinc-400 font-mono text-[11px] sticky top-0">
                <tr>
                  <th className="py-2 px-3">File Path</th>
                  <th className="py-2 px-3">Size (bytes)</th>
                  <th className="py-2 px-3">SHA-256 Cryptographic Hash</th>
                  <th className="py-2 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle font-mono text-[11px]">
                {Object.entries(manifestData.entries).map(([path, entry]: [string, any]) => (
                  <tr key={path} className="hover:bg-surface-2/40 transition-colors">
                    <td className="py-2 px-3 text-zinc-200">{path}</td>
                    <td className="py-2 px-3 text-zinc-400">{entry.size}</td>
                    <td className="py-2 px-3 text-zinc-400 truncate max-w-xs">{entry.sha256}</td>
                    <td className="py-2 px-3 text-right">
                      <button
                        onClick={() => copyToClipboard(entry.sha256)}
                        className="text-zinc-500 hover:text-zinc-200 p-1 rounded"
                        title="Copy SHA-256"
                      >
                        {copiedHash === entry.sha256 ? (
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
        </Card>
      )}

      {/* Terminal Telemetry Stream & Integrity Validation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Terminal Output */}
        <div className="lg:col-span-2">
          <Card className="h-full flex flex-col justify-between">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-cyan-400" />
                <CardTitle>Execution Console Stream</CardTitle>
              </div>
              <span className="text-[10px] font-mono text-zinc-500">Live Telemetry</span>
            </CardHeader>

            <div className="bg-black/60 rounded-lg p-3 font-mono text-xs text-zinc-300 h-64 overflow-y-auto whitespace-pre-wrap border border-border-subtle">
              {terminalOutput || (
                <span className="text-zinc-600">// Ready. Awaiting operator dispatch.</span>
              )}
            </div>
          </Card>
        </div>

        {/* Integrity Check Actions */}
        <div>
          <Card className="h-full flex flex-col justify-between space-y-4">
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <CardTitle>Repository Health Audits</CardTitle>
              </div>
              <CardDescription>
                Fast checks inspect pack index structure; deep checks verify entire data blobs.
              </CardDescription>
            </div>

            <div className="space-y-2">
              <Button
                className="w-full justify-start"
                variant="secondary"
                isLoading={loadingCheckFast}
                onClick={() => handleCheck(false)}
                leftIcon={<RefreshCw className="w-3.5 h-3.5 text-emerald-400" />}
              >
                Fast Index Check (`restic check`)
              </Button>

              <Button
                className="w-full justify-start"
                variant="outline"
                isLoading={loadingCheckDeep}
                onClick={() => handleCheck(true)}
                leftIcon={<ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />}
              >
                Deep Data Check (`--read-data`)
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
