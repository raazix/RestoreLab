import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

export interface TabItem {
  id: string
  label: string
  badge?: number | string
  icon?: React.ReactNode
}

interface TabsProps {
  tabs: TabItem[]
  activeTab: string
  onChange: (id: string) => void
  className?: string
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onChange, className }) => {
  return (
    <div className={cn('flex items-center gap-1 border-b border-border-subtle px-1', className)}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id

        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              'relative flex items-center gap-2 px-3 py-2 text-xs font-medium transition-colors select-none',
              isActive ? 'text-zinc-100' : 'text-zinc-400 hover:text-zinc-200'
            )}
          >
            {tab.icon}
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span
                className={cn(
                  'px-1.5 py-0.2 text-[10px] font-mono rounded-full',
                  isActive
                    ? 'bg-zinc-800 text-zinc-200 border border-zinc-700'
                    : 'bg-surface-2 text-zinc-500'
                )}
              >
                {tab.badge}
              </span>
            )}
            {isActive && (
              <motion.div
                layoutId="activeTabUnderline"
                className="absolute bottom-0 left-0 right-0 h-[2px] bg-linear-accent"
                transition={{ type: 'spring', stiffness: 500, damping: 35 }}
              />
            )}
          </button>
        )
      })}
    </div>
  )
}
