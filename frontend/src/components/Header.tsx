import React from 'react'
import { Search, Terminal, HardDrive, CheckCircle2, ShieldCheck } from 'lucide-react'
import { Button } from './ui/Button'
import { Badge } from './ui/Badge'
import { SystemStatus } from '@/lib/api'

interface HeaderProps {
  currentViewTitle: string
  onOpenCommandPalette: () => void
  onQuickBackup: () => void
  onQuickVerify: () => void
  systemStatus: SystemStatus | null
}

export const Header: React.FC<HeaderProps> = ({
  currentViewTitle,
  onOpenCommandPalette,
  onQuickBackup,
  onQuickVerify,
  systemStatus,
}) => {
  return (
    <header className="h-14 border-b border-border-subtle bg-surface-1/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Left Title & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold tracking-tight text-zinc-100">
          {currentViewTitle}
        </h1>

        <div className="h-3.5 w-[1px] bg-border-muted" />

        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <Badge variant="cyan" className="font-mono text-[10px]">
            Restic 0.19.1
          </Badge>
          <span className="hidden md:inline font-mono text-[11px] text-zinc-500">
            {systemStatus?.repository_path ? systemStatus.repository_path.split(/[\\/]/).pop() : 'lab_repo'}
          </span>
        </div>
      </div>

      {/* Right Actions & Command Palette Trigger */}
      <div className="flex items-center gap-2.5">
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-2 hover:bg-surface-3 border border-border-muted text-xs text-zinc-400 hover:text-zinc-200 transition-all shadow-subtle group"
        >
          <Search className="w-3.5 h-3.5 text-zinc-400 group-hover:text-zinc-200" />
          <span className="hidden sm:inline">Search commands...</span>
          <span className="kbd-shortcut">Ctrl K</span>
        </button>

        <div className="h-3.5 w-[1px] bg-border-muted hidden sm:block" />

        <Button
          size="sm"
          variant="outline"
          leftIcon={<HardDrive className="w-3.5 h-3.5 text-indigo-400" />}
          onClick={onQuickBackup}
        >
          Backup
        </Button>

        <Button
          size="sm"
          variant="primary"
          leftIcon={<CheckCircle2 className="w-3.5 h-3.5" />}
          onClick={onQuickVerify}
        >
          Verify
        </Button>
      </div>
    </header>
  )
}
