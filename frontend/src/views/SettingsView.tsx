import React, { useEffect, useState } from 'react'
import {
  Settings,
  HardDrive,
  ShieldCheck,
  Send,
  Database,
  Lock,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { api, SettingsView as SettingsData } from '@/lib/api'

export const SettingsView: React.FC = () => {
  const [settings, setSettings] = useState<SettingsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [testingSupermemory, setTestingSupermemory] = useState(false)
  const [testResult, setTestResult] = useState<{
    success: boolean
    message: string
    namespace: string
  } | null>(null)

  const fetchSettings = async () => {
    setLoading(true)
    try {
      const data = await api.getSettings()
      setSettings(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSettings()
  }, [])

  const handleTestSupermemory = async () => {
    setTestingSupermemory(true)
    setTestResult(null)
    try {
      const res = await api.testSupermemory()
      setTestResult(res)
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message,
        namespace: settings?.supermemory_namespace || 'restorelab-incidents',
      })
    } finally {
      setTestingSupermemory(false)
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* View Header */}
      <div>
        <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
          System Governance & Configuration
        </h2>
        <p className="text-xs text-zinc-400 mt-1 max-w-2xl leading-relaxed">
          Inspect verified runtime boundaries, cryptographic engines, operational thresholds,
          and manage Supermemory API v5 scoped namespace telemetry.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Environment & Paths */}
        <Card className="space-y-4">
          <CardHeader>
            <div className="flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-cyan-400" />
              <CardTitle>Verified Filesystem Paths</CardTitle>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={fetchSettings}
              isLoading={loading}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Refresh
            </Button>
          </CardHeader>

          <div className="space-y-2 text-xs font-mono">
            <div>
              <span className="text-zinc-500 block text-[11px] font-sans">Restic Binary:</span>
              <div className="p-2 rounded bg-surface-2 text-zinc-200 border border-border-subtle truncate">
                {settings?.restic_binary_path || 'Checking...'}
              </div>
            </div>

            <div>
              <span className="text-zinc-500 block text-[11px] font-sans">Active Encrypted Repo:</span>
              <div className="p-2 rounded bg-surface-2 text-zinc-200 border border-border-subtle truncate">
                {settings?.repository_path || 'Checking...'}
              </div>
            </div>

            <div>
              <span className="text-zinc-500 block text-[11px] font-sans">Lab Source Directory:</span>
              <div className="p-2 rounded bg-surface-2 text-zinc-200 border border-border-subtle truncate">
                {settings?.lab_source || 'Checking...'}
              </div>
            </div>

            <div>
              <span className="text-zinc-500 block text-[11px] font-sans">Isolated Restore Sandbox:</span>
              <div className="p-2 rounded bg-surface-2 text-zinc-200 border border-border-subtle truncate">
                {settings?.lab_restore || 'Checking...'}
              </div>
            </div>

            <div>
              <span className="text-zinc-500 block text-[11px] font-sans">SQLite Database:</span>
              <div className="p-2 rounded bg-surface-2 text-zinc-200 border border-border-subtle truncate">
                {settings?.database_path || 'Checking...'}
              </div>
            </div>
          </div>
        </Card>

        {/* Operational Limits & Security */}
        <div className="space-y-6">
          <Card className="space-y-4">
            <CardHeader>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <CardTitle>Operational Limits & Safety Bounds</CardTitle>
              </div>
            </CardHeader>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-2.5 rounded bg-surface-2 border border-border-subtle">
                <span className="text-zinc-400">Subprocess Timeout:</span>
                <span className="font-mono text-zinc-100 font-semibold">
                  {settings?.command_timeout_seconds}s
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded bg-surface-2 border border-border-subtle">
                <span className="text-zinc-400">Max Source Scan Size:</span>
                <span className="font-mono text-zinc-100 font-semibold">
                  {settings?.max_source_scan_mb} MB
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded bg-surface-2 border border-border-subtle">
                <span className="text-zinc-400">Max Manifest Files:</span>
                <span className="font-mono text-zinc-100 font-semibold">
                  {settings?.max_manifest_files} files
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded bg-surface-2 border border-border-subtle">
                <span className="text-zinc-400">Credentials Protection:</span>
                <Badge variant="emerald" dot>
                  Zero-Leak Argument Scrubbing
                </Badge>
              </div>
            </div>
          </Card>

          {/* Supermemory v5 Integration Card */}
          <Card className="space-y-4 border-indigo-500/20 bg-indigo-500/[0.02]">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Send className="w-4 h-4 text-indigo-400" />
                <CardTitle>Supermemory API v5 Extension</CardTitle>
              </div>
              <Badge variant={settings?.supermemory_enabled ? 'indigo' : 'zinc'}>
                {settings?.supermemory_enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </CardHeader>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between p-2.5 rounded bg-surface-2 border border-border-subtle">
                <span className="text-zinc-400">API Endpoint:</span>
                <span className="font-mono text-zinc-300">
                  {settings?.supermemory_api_url}
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded bg-surface-2 border border-border-subtle">
                <span className="text-zinc-400">Isolated Namespace:</span>
                <span className="font-mono text-indigo-400 font-bold">
                  {settings?.supermemory_namespace}
                </span>
              </div>

              <div className="flex items-center justify-between p-2.5 rounded bg-surface-2 border border-border-subtle">
                <span className="text-zinc-400">API Key Configured:</span>
                <span className="font-mono text-zinc-300">
                  {settings?.supermemory_key_configured ? 'Yes (Loaded from .env)' : 'No'}
                </span>
              </div>
            </div>

            <Button
              className="w-full"
              variant="secondary"
              isLoading={testingSupermemory}
              onClick={handleTestSupermemory}
              leftIcon={<Send className="w-3.5 h-3.5 text-indigo-400" />}
            >
              Test Supermemory API Connection
            </Button>

            {testResult && (
              <div
                className={`p-3 rounded-lg border text-xs font-mono ${
                  testResult.success
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                    : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
                }`}
              >
                <div className="flex items-center gap-2 font-bold mb-1">
                  {testResult.success ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-rose-400" />
                  )}
                  <span>{testResult.success ? 'Connection Successful' : 'Connection Failed'}</span>
                </div>
                <div className="text-[11px] text-zinc-400">{testResult.message}</div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
