import React from 'react'
import { cn } from '@/lib/utils'

export type BadgeVariant = 'emerald' | 'amber' | 'rose' | 'cyan' | 'indigo' | 'zinc' | 'default'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
  dot?: boolean
  children: React.ReactNode
}

const variantStyles: Record<BadgeVariant, { bg: string; text: string; border: string; dot: string }> = {
  emerald: {
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    border: 'border-emerald-500/20',
    dot: 'bg-emerald-400',
  },
  amber: {
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    border: 'border-amber-500/20',
    dot: 'bg-amber-400',
  },
  rose: {
    bg: 'bg-rose-500/10',
    text: 'text-rose-400',
    border: 'border-rose-500/20',
    dot: 'bg-rose-400',
  },
  cyan: {
    bg: 'bg-cyan-500/10',
    text: 'text-cyan-400',
    border: 'border-cyan-500/20',
    dot: 'bg-cyan-400',
  },
  indigo: {
    bg: 'bg-indigo-500/10',
    text: 'text-indigo-400',
    border: 'border-indigo-500/20',
    dot: 'bg-indigo-400',
  },
  zinc: {
    bg: 'bg-zinc-800/60',
    text: 'text-zinc-400',
    border: 'border-zinc-700/40',
    dot: 'bg-zinc-400',
  },
  default: {
    bg: 'bg-surface-3',
    text: 'text-zinc-300',
    border: 'border-border-muted',
    dot: 'bg-zinc-400',
  },
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'default',
  dot = false,
  className,
  children,
  ...props
}) => {
  const styles = variantStyles[variant]

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-full border',
        styles.bg,
        styles.text,
        styles.border,
        className
      )}
      {...props}
    >
      {dot && (
        <span className={cn('w-1.5 h-1.5 rounded-full animate-pulse', styles.dot)} />
      )}
      {children}
    </span>
  )
}
