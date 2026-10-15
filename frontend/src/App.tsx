import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sidebar } from './components/Sidebar'
import { Header } from './components/Header'
import { CommandPalette } from './components/CommandPalette'
import { OverviewView } from './views/OverviewView'
import { BackupLabView } from './views/BackupLabView'
import { RecoveryVerificationView } from './views/RecoveryVerificationView'
import { IncidentExplorerView } from './views/IncidentExplorerView'
import { KnowledgeBaseView } from './views/KnowledgeBaseView'
import { ExperimentsView } from './views/ExperimentsView'
import { ReportsView } from './views/ReportsView'
import { SettingsView } from './views/SettingsView'
import { api, DashboardMetrics, SystemStatus } from './lib/api'

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<string>('overview')
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false)
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false)

  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3500)
  }

  const fetchGlobalData = async () => {
    try {
      const [statusData, dashData] = await Promise.all([
        api.getSystemStatus(),
        api.getDashboard(),
      ])
      setSystemStatus(statusData)
      setMetrics(dashData)
    } catch (err: any) {
      console.error('Error fetching global telemetry', err)
    }
  }

  useEffect(() => {
    fetchGlobalData()

    // Global keyboard shortcuts
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setIsCommandPaletteOpen((prev) => !prev)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleAction = async (action: string) => {
    if (action === 'generate-sample') {
      try {
        const res = await api.generateSampleData()
        showToast(res.message)
        fetchGlobalData()
      } catch (err: any) {
        showToast(`Error: ${err.message}`)
      }
    } else if (action === 'generate-manifest') {
      try {
        const manifest = await api.generateManifest()
        showToast(`Manifest generated: ${manifest.id.slice(0, 8)}`)
        fetchGlobalData()
      } catch (err: any) {
        showToast(`Error: ${err.message}`)
      }
    } else if (action === 'run-check') {
      try {
        const res = await api.checkRepo(false)
        showToast(`Check finished (Passed: ${res.success})`)
        fetchGlobalData()
      } catch (err: any) {
        showToast(`Error: ${err.message}`)
      }
    } else if (action === 'test-supermemory') {
      try {
        const res = await api.testSupermemory()
        showToast(`Supermemory: ${res.message}`)
      } catch (err: any) {
        showToast(`Supermemory Error: ${err.message}`)
      }
    }
  }

  const viewTitles: Record<string, string> = {
    overview: 'Overview',
    backup: 'Backup Lab',
    recovery: 'Recovery Verification',
    incidents: 'Incident Explorer',
    knowledge: 'Knowledge Base',
    experiments: 'Controlled Experiments',
    reports: 'Reports & Audits',
    settings: 'Settings',
  }

  return (
    <div className="min-h-screen bg-canvas text-zinc-100 flex flex-row">
      {/* Sidebar */}
      <Sidebar
        currentView={currentView}
        onSelectView={(v) => setCurrentView(v)}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        openIncidentsCount={metrics?.open_incidents_count ?? 0}
        systemStatus={systemStatus}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          currentViewTitle={viewTitles[currentView] || 'Overview'}
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
          onQuickBackup={() => setCurrentView('backup')}
          onQuickVerify={() => setCurrentView('recovery')}
          systemStatus={systemStatus}
        />

        <main className="flex-1 p-6 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentView}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
            >
              {currentView === 'overview' && (
                <OverviewView
                  metrics={metrics}
                  systemStatus={systemStatus}
                  onNavigate={(v) => setCurrentView(v)}
                  onRefresh={fetchGlobalData}
                />
              )}
              {currentView === 'backup' && (
                <BackupLabView
                  systemStatus={systemStatus}
                  onRefreshMetrics={fetchGlobalData}
                />
              )}
              {currentView === 'recovery' && (
                <RecoveryVerificationView
                  systemStatus={systemStatus}
                  onRefreshMetrics={fetchGlobalData}
                />
              )}
              {currentView === 'incidents' && (
                <IncidentExplorerView
                  systemStatus={systemStatus}
                  onRefreshMetrics={fetchGlobalData}
                />
              )}
              {currentView === 'knowledge' && (
                <KnowledgeBaseView systemStatus={systemStatus} />
              )}
              {currentView === 'experiments' && (
                <ExperimentsView
                  systemStatus={systemStatus}
                  onRefreshMetrics={fetchGlobalData}
                />
              )}
              {currentView === 'reports' && <ReportsView />}
              {currentView === 'settings' && <SettingsView />}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Global Command Palette (Ctrl+K) */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onNavigate={(v) => setCurrentView(v)}
        onRunAction={handleAction}
      />

      {/* Toast Notification */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className="fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-lg bg-surface-3 border border-border-muted text-xs font-medium text-zinc-100 shadow-elevated flex items-center gap-2"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default App
