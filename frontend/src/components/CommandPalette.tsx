import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  LayoutDashboard,
  HardDrive,
  CheckCircle2,
  AlertTriangle,
  BookOpen,
  FlaskConical,
  FileText,
  Settings,
  Zap,
  X,
} from 'lucide-react'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  onNavigate: (view: string) => void
  onRunAction: (action: string) => void
}

interface CommandItem {
  id: string
  label: string
  category: 'Navigation' | 'Actions'
  icon: React.ReactNode
  shortcut?: string
  action: () => void
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigate,
  onRunAction,
}) => {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)

  const items: CommandItem[] = [
    // Navigation
    {
      id: 'nav-overview',
      label: 'Go to Overview',
      category: 'Navigation',
      icon: <LayoutDashboard className="w-4 h-4 text-cyan-400" />,
      shortcut: 'G O',
      action: () => onNavigate('overview'),
    },
    {
      id: 'nav-backup',
      label: 'Go to Backup Lab',
      category: 'Navigation',
      icon: <HardDrive className="w-4 h-4 text-indigo-400" />,
      shortcut: 'G B',
      action: () => onNavigate('backup'),
    },
    {
      id: 'nav-verify',
      label: 'Go to Recovery Verification',
      category: 'Navigation',
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
      shortcut: 'G V',
      action: () => onNavigate('recovery'),
    },
    {
      id: 'nav-incidents',
      label: 'Go to Incident Explorer',
      category: 'Navigation',
      icon: <AlertTriangle className="w-4 h-4 text-amber-400" />,
      shortcut: 'G I',
      action: () => onNavigate('incidents'),
    },
    {
      id: 'nav-kb',
      label: 'Go to Knowledge Base',
      category: 'Navigation',
      icon: <BookOpen className="w-4 h-4 text-blue-400" />,
      shortcut: 'G K',
      action: () => onNavigate('knowledge'),
    },
    {
      id: 'nav-exp',
      label: 'Go to Controlled Experiments',
      category: 'Navigation',
      icon: <FlaskConical className="w-4 h-4 text-purple-400" />,
      shortcut: 'G E',
      action: () => onNavigate('experiments'),
    },
    {
      id: 'nav-reports',
      label: 'Go to Audit Reports',
      category: 'Navigation',
      icon: <FileText className="w-4 h-4 text-zinc-400" />,
      shortcut: 'G R',
      action: () => onNavigate('reports'),
    },
    {
      id: 'nav-settings',
      label: 'Go to Settings',
      category: 'Navigation',
      icon: <Settings className="w-4 h-4 text-zinc-400" />,
      shortcut: 'G S',
      action: () => onNavigate('settings'),
    },

    // Actions
    {
      id: 'act-sample',
      label: 'Generate Sample Lab Dataset',
      category: 'Actions',
      icon: <Zap className="w-4 h-4 text-amber-400" />,
      action: () => onRunAction('generate-sample'),
    },
    {
      id: 'act-manifest',
      label: 'Generate Pre-Backup Manifest',
      category: 'Actions',
      icon: <Zap className="w-4 h-4 text-cyan-400" />,
      action: () => onRunAction('generate-manifest'),
    },
    {
      id: 'act-check',
      label: 'Run Fast Repository Check',
      category: 'Actions',
      icon: <Zap className="w-4 h-4 text-emerald-400" />,
      action: () => onRunAction('run-check'),
    },
    {
      id: 'act-test-supermemory',
      label: 'Test Supermemory Connection',
      category: 'Actions',
      icon: <Zap className="w-4 h-4 text-indigo-400" />,
      action: () => onRunAction('test-supermemory'),
    },
  ]

  const filteredItems = items.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase())
  )

  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (!isOpen) return

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredItems.length))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (filteredItems[selectedIndex]) {
          filteredItems[selectedIndex].action()
          onClose()
        }
      } else if (e.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, selectedIndex, filteredItems, onClose])

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/75 backdrop-blur-sm"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -10 }}
            transition={{ duration: 0.15 }}
            className="relative w-full max-w-xl bg-surface-1 border border-border-muted rounded-xl shadow-elevated overflow-hidden z-10"
          >
            {/* Search Input */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-border-subtle">
              <Search className="w-4 h-4 text-zinc-400" />
              <input
                autoFocus
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Type a command or search..."
                className="w-full bg-transparent text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none font-sans"
              />
              <button
                onClick={onClose}
                className="text-zinc-500 hover:text-zinc-300 p-0.5 rounded transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Command List */}
            <div className="max-h-80 overflow-y-auto p-2">
              {filteredItems.length === 0 ? (
                <div className="py-8 text-center text-xs text-zinc-500">
                  No matching commands found.
                </div>
              ) : (
                filteredItems.map((item, index) => {
                  const isSelected = index === selectedIndex

                  return (
                    <div
                      key={item.id}
                      onClick={() => {
                        item.action()
                        onClose()
                      }}
                      onMouseEnter={() => setSelectedIndex(index)}
                      className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-xs transition-colors ${
                        isSelected
                          ? 'bg-surface-3 text-zinc-100'
                          : 'text-zinc-400 hover:bg-surface-2 hover:text-zinc-200'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        {item.icon}
                        <span className="font-medium">{item.label}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-zinc-500 uppercase">
                          {item.category}
                        </span>
                        {item.shortcut && (
                          <span className="kbd-shortcut">{item.shortcut}</span>
                        )}
                      </div>
                    </div>
                  )
                })
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-border-subtle bg-surface-2/40 flex items-center justify-between text-[11px] text-zinc-500 font-mono">
              <div className="flex items-center gap-3">
                <span>↑↓ navigate</span>
                <span>↵ select</span>
                <span>esc close</span>
              </div>
              <span>RestoreLab v1.0</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
