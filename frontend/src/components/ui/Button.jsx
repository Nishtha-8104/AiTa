import { forwardRef } from 'react'
import { Loader2 } from 'lucide-react'

const VARIANTS = {
  primary:   'bg-ink text-canvas hover:bg-white disabled:bg-tile-3 disabled:text-ink-faint',
  accent:    'bg-brand-500 text-canvas hover:bg-brand-400 disabled:bg-tile-3 disabled:text-ink-faint',
  secondary: 'border border-line-strong bg-tile-2 text-ink hover:bg-tile-3 disabled:text-ink-faint',
  ghost:     'text-ink-muted hover:bg-white/[0.06] hover:text-ink disabled:text-ink-faint',
  danger:    'bg-pop-coral text-canvas hover:brightness-110 disabled:bg-tile-3 disabled:text-ink-faint',
  hint:      'bg-pop-sun text-canvas hover:brightness-105 disabled:bg-tile-3 disabled:text-ink-faint',
}

const SIZES = {
  sm: 'h-9 px-3.5 text-[13px] gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-6 text-[15px] gap-2.5',
}

const Button = forwardRef(function Button(
  { variant = 'primary', size = 'md', busy = false, icon: Icon, iconRight: IconRight, className = '', children, disabled, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={`inline-flex shrink-0 items-center justify-center rounded-md font-medium transition-[transform,background-color,color,filter] duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] active:scale-[0.97] disabled:cursor-not-allowed disabled:active:scale-100 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {busy ? <Loader2 size={16} className="animate-spin" /> : Icon && <Icon size={16} strokeWidth={2} />}
      {children}
      {IconRight && !busy && <IconRight size={16} strokeWidth={2} />}
    </button>
  )
})

export default Button
