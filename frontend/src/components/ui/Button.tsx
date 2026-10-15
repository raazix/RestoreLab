import React from 'react'
import { cn } from '@/lib/utils'

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  isLoading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  kbd?: string
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'secondary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      kbd,
      className,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium transition-all duration-150 select-none disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]'

    const variantStyles: Record<ButtonVariant, string> = {
      primary:
        'bg-linear-accent hover:bg-[#6c78e0] text-white shadow-subtle border border-indigo-400/30',
      secondary:
        'bg-surface-3 hover:bg-surface-4 text-zinc-200 border border-border-muted hover:border-border-active',
      outline:
        'bg-transparent hover:bg-surface-2 text-zinc-300 border border-border-muted hover:border-border-active',
      ghost:
        'bg-transparent hover:bg-surface-2 text-zinc-400 hover:text-zinc-200',
      danger:
        'bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30',
    }

    const sizeStyles: Record<ButtonSize, string> = {
      sm: 'text-xs h-7 px-2.5 gap-1.5 rounded-md',
      md: 'text-xs h-8 px-3 gap-2 rounded-md',
      lg: 'text-sm h-9 px-4 gap-2.5 rounded-lg',
    }

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
        {...props}
      >
        {isLoading ? (
          <svg
            className="animate-spin h-3.5 w-3.5 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        ) : (
          leftIcon
        )}
        <span>{children}</span>
        {rightIcon && !isLoading && rightIcon}
        {kbd && <span className="kbd-shortcut ml-1">{kbd}</span>}
      </button>
    )
  }
)

Button.displayName = 'Button'
