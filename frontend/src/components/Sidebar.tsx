import React from 'react'
import {
  LayoutDashboard,
  HardDrive,
  CheckCircle2,
  AlertTriangle,
  BookOpen,
  FlaskConical,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
  Layers,
} from 'lucide-react'
import { SystemStatus } from '@/lib/api'

interface SidebarProps {
  currentView: string
  onSelectView: (view: string) => void
  isCollapsed: boolean
  onToggleCollapse: () => void
  openIncidentsCount: number
  systemStatus: SystemStatus | null
}

interface NavItem {
  id: string
  label: string
  icon: React.ReactNode
  badge?: number
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onSelectView,
  isCollapsed,
  onToggleCollapse,
  openIncidentsCount,
  systemStatus,
}) => {
  const navItems: NavItem[] = [
    {
      id: 'overview',
      label: 'Overview',
      icon: <LayoutDashboard className="w-4 h-4" />,
    },
    {
      id: 'backup',
      label: 'Backup Lab',
      icon: <HardDrive className="w-4 h-4" />,
    },
    {
      id: 'recovery',
      label: 'Recovery Verification',
      icon: <CheckCircle2 className="w-4 h-4" />,
    },
    {
      id: 'incidents',
      label: 'Incident Explorer',
      icon: <AlertTriangle className="w-4 h-4" />,
      badge: openIncidentsCount > 0 ? openIncidentsCount : undefined,
    },
    {
      id: 'knowledge',
      label: 'Knowledge Base',
      icon: <BookOpen className="w-4 h-4" />,
    },
    {
      id: 'experiments',
      label: 'Experiments',
      icon: <FlaskConical className="w-4 h-4" />,
    },
    {
      id: 'reports',
      label: 'Reports & Audits',
      icon: <FileText className="w-4 h-4" />,
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: <Settings className="w-4 h-4" />,
    },
  ]

  return (
    <aside
      className={`h-screen sticky top-0 bg-surface-1 border-r border-border-subtle flex flex-col justify-between transition-all duration-200 select-none z-30 ${
        isCollapsed ? 'w-16' : 'w-60'
      }`}
    >
      {/* Top Header */}
      <div>
        <div className="h-14 flex items-center justify-between px-3.5 border-b border-border-subtle">
          {!isCollapsed && (
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-indigo-500/20 to-cyan-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
                <Shield className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="flex flex-col truncate">
                <span className="text-xs font-semibold tracking-tight text-zinc-100 flex items-center gap-1.5">
                  RestoreLab
                  <span className="text-[10px] px-1 py-0.2 font-mono bg-zinc-800 text-zinc-400 rounded">
                    v1.0
                  </span>
                </span>
                <span className="text-[10px] text-zinc-500 truncate">
                  Reliability Workbench
                </span>
              </div>
            </div>
          )}

          {isCollapsed && (
            <div className="w-7 h-7 mx-auto rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
              <Shield className="w-4 h-4 text-cyan-400" />
            </div>
          )}

          <button
            onClick={onToggleCollapse}
            className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-surface-2 transition-colors ml-auto"
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="p-2 space-y-0.5">
          {navItems.map((item) => {
            const isActive = currentView === item.id

            return (
              <button
                key={item.id}
                onClick={() => onSelectView(item.id)}
                title={isCollapsed ? item.label : undefined}
                className={`w-full flex items-center gap-3 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-surface-3 text-zinc-100 shadow-subtle border border-border-muted'
                    : 'text-zinc-400 hover:bg-surface-2 hover:text-zinc-200'
                }`}
              >
                <span className={isActive ? 'text-cyan-400' : 'text-zinc-400'}>
                  {item.icon}
                </span>

                {!isCollapsed && (
                  <>
                    <span className="truncate flex-1 text-left">{item.label}</span>
                    {item.badge !== undefined && (
                      <span className="px-1.5 py-0.2 text-[10px] font-mono font-semibold rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Footer System Status */}
      <div className="p-3 border-t border-border-subtle bg-surface-1/50">
        {!isCollapsed ? (
          <div className="space-y-2 text-[11px]">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="flex items-center gap-1.5">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    systemStatus?.restic_installed
                      ? 'bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.5)]'
                      : 'bg-rose-400'
                  }`}
                />
                Engine: Restic
              </span>
              <span className="font-mono text-[10px] text-zinc-500">
                {systemStatus?.restic_installed ? '0.19.1' : 'missing'}
              </span>
            </div>

            <div className="flex items-center justify-between text-zinc-400">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                SQLite ACID
              </span>
              <span className="font-mono text-[10px] text-zinc-500">WAL Mode</span>
            </div>

            <div className="flex items-center justify-between text-zinc-400">
              <span className="flex items-center gap-1.5">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    systemStatus?.supermemory_enabled ? 'bg-indigo-400' : 'bg-zinc-600'
                  }`}
                />
                Supermemory
              </span>
              <span className="font-mono text-[10px] text-zinc-500 truncate max-w-[80px]">
                {systemStatus?.supermemory_namespace || 'v5'}
              </span>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                systemStatus?.restic_installed ? 'bg-emerald-400' : 'bg-rose-400'
              }`}
              title="Restic Engine"
            />
            <span className="w-2 h-2 rounded-full bg-cyan-400" title="SQLite Database" />
            <span
              className={`w-2 h-2 rounded-full ${
                systemStatus?.supermemory_enabled ? 'bg-indigo-400' : 'bg-zinc-600'
              }`}
              title="Supermemory"
            />
          </div>
        )}
      </div>
    </aside>
  )
}
