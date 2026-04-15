import { Sun, Moon } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'

export default function ThemeToggle({ className = '' }) {
  const { isDark, toggle } = useTheme()

  return (
    <button
      onClick={toggle}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className={`
        relative w-14 h-7 rounded-full border transition-all duration-300 flex items-center px-1
        ${isDark
          ? 'bg-surface-700 border-white/10'
          : 'bg-amber-100 border-amber-300'
        }
        ${className}
      `}
    >
      <span className={`
        absolute w-5 h-5 rounded-full flex items-center justify-center transition-all duration-300 shadow-md
        ${isDark
          ? 'translate-x-0 bg-surface-500'
          : 'translate-x-7 bg-amber-400'
        }
      `}>
        {isDark
          ? <Moon size={11} className="text-white/70" />
          : <Sun size={11} className="text-white" />
        }
      </span>
    </button>
  )
}
