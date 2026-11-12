import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutGrid, Target, Shapes, Code2, SquareTerminal, MessageSquareText, UserRound, Menu, X,
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { feedbackAPI } from '../../utils/api'
import { languageLabel } from '../learning/labels'
import LogoMark, { Wordmark } from './LogoMark'
import ModelCard, { useModelSettings } from '../model/ModelCard'
import ModelWindow from '../model/ModelWindow'

const NAV = [
  { to: '/dashboard', label: 'Home', icon: LayoutGrid },
  { to: '/practice', label: 'Practice', icon: Target, primary: true },
  { to: '/topics', label: 'Topic practice', icon: Shapes },
  { to: '/code-help', label: 'Coding problems', icon: Code2 },
  { to: '/code-eval', label: 'Code workspace', icon: SquareTerminal },
  { to: '/feedback', label: 'Feedback', icon: MessageSquareText, badge: 'feedback' },
  { to: '/profile', label: 'Profile', icon: UserRound },
]

function Logo() {
  return (
    <div className="flex items-center gap-2.5 px-2">
      <LogoMark />
      <Wordmark tagline />
    </div>
  )
}

function NavItems({ unread }) {
  return (
    <ul className="flex flex-col gap-1">
      {NAV.map(({ to, label, icon: Icon, primary, badge }) => (
        <li key={to}>
          <NavLink
            to={to}
            className={({ isActive }) =>
              `group flex h-11 items-center gap-3 rounded-md px-3.5 text-sm font-medium transition-colors duration-200 ${
                isActive ? 'bg-ink text-canvas' : 'text-ink-muted hover:bg-white/[0.06] hover:text-ink'
              }`}
          >
            {({ isActive }) => (
              <>
                <Icon size={18} strokeWidth={2} className={!isActive && primary ? 'text-pop-mint' : ''} />
                <span className="flex-1">{label}</span>
                {primary && !isActive && (
                  <span className="h-2 w-2 rounded-full bg-pop-mint motion-safe:animate-breathe" aria-hidden="true" />
                )}
                {badge === 'feedback' && unread > 0 && (
                  <span className={`min-w-[22px] rounded-full px-1.5 py-0.5 text-center font-mono text-[11px] font-semibold ${isActive ? 'bg-canvas text-pop-pink' : 'bg-pop-pink text-canvas'}`}>
                    {unread}
                    <span className="sr-only"> unread</span>
                  </span>
                )}
              </>
            )}
          </NavLink>
        </li>
      ))}
    </ul>
  )
}

function UserBlock({ user }) {
  const name = user?.full_name || user?.username || 'You'
  const initials = name.split(/\s+/).map(p => p[0]).join('').slice(0, 2).toUpperCase()
  return (
    <div className="rounded-[18px] border border-line bg-tile p-3">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-ink font-mono text-sm font-semibold text-canvas" aria-hidden="true">
          {initials}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-ink">{name}</p>
          <p className="mt-0.5 flex items-center gap-1.5 text-xs text-ink-subtle">
            Coding in
            <span className="rounded-md bg-tile-3 px-1.5 py-px font-mono text-[11px] font-semibold text-ink">
              {languageLabel(user?.preferred_language)}
            </span>
          </p>
        </div>
      </div>
    </div>
  )
}

function SidebarBody({ user, unread, model, onOpenModel }) {
  return (
    <div className="flex h-full flex-col gap-8">
      <Logo />
      <nav aria-label="Main" className="flex-1">
        <NavItems unread={unread} />
      </nav>
      <div className="flex flex-col gap-3">
        <ModelCard settings={model} onOpen={onOpenModel} />
        <UserBlock user={user} />
      </div>
    </div>
  )
}

// topBar: a strip above the page (study step + timer). navLocked: hides navigation during a timed block.
export default function AppShell({ title, topBar, navLocked = false, children }) {
  const { user } = useAuth()
  const location = useLocation()
  const [unread, setUnread] = useState(0)
  const [drawer, setDrawer] = useState(false)
  const model = useModelSettings()
  const openModel = () => { setDrawer(false); model.setOpen(true) }

  useEffect(() => {
    const load = () => feedbackAPI.unreadCount()
      .then(({ data }) => setUnread(data.unread ?? 0))
      .catch(() => {})
    load()
    window.addEventListener('pet:feedback-changed', load)
    return () => window.removeEventListener('pet:feedback-changed', load)
  }, [location.pathname])

  useEffect(() => { setDrawer(false) }, [location.pathname])

  useEffect(() => {
    if (!drawer) return
    const onKey = e => { if (e.key === 'Escape') setDrawer(false) }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [drawer])

  return (
    <div className={`min-h-[100dvh] ${navLocked ? '' : 'lg:grid lg:grid-cols-[232px_minmax(0,1fr)]'}`}>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-ink focus:px-4 focus:py-2 focus:text-canvas">
        Skip to content
      </a>

      {!navLocked && (
        <aside className="sticky top-0 hidden h-[100dvh] border-r border-line px-4 py-6 lg:block">
          <SidebarBody user={user} unread={unread} model={model.settings} onOpenModel={openModel} />
        </aside>
      )}

      <header className={`sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-canvas/90 px-4 backdrop-blur-md ${navLocked ? '' : 'lg:hidden'}`}>
        <LogoMark className="h-7 w-7" />
        <span className="min-w-0 flex-1 truncate text-[15px] font-semibold tracking-tight text-ink">{title || 'PET'}</span>
        {!navLocked && (
          <button
            type="button"
            onClick={() => setDrawer(true)}
            aria-label="Open menu"
            aria-expanded={drawer}
            className="relative flex h-10 w-10 items-center justify-center rounded-full text-ink-muted hover:bg-white/[0.06] hover:text-ink"
          >
            <Menu size={20} />
            {unread > 0 && <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-pop-pink" aria-hidden="true" />}
          </button>
        )}
      </header>

      {drawer && !navLocked && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <button type="button" aria-label="Close menu" onClick={() => setDrawer(false)} className="absolute inset-0 bg-canvas/70 backdrop-blur-sm motion-safe:animate-fade-in" />
          <div className="absolute inset-y-0 left-0 w-[min(300px,86vw)] border-r border-line bg-canvas px-4 py-5 motion-safe:animate-drawer-in">
            <button
              type="button"
              autoFocus
              onClick={() => setDrawer(false)}
              aria-label="Close menu"
              className="absolute right-3 top-4 flex h-10 w-10 items-center justify-center rounded-full text-ink-muted hover:bg-white/[0.06] hover:text-ink"
            >
              <X size={18} />
            </button>
            <SidebarBody user={user} unread={unread} model={model.settings} onOpenModel={openModel} />
          </div>
        </div>
      )}

      <main id="main" className="min-w-0 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        {topBar && <div className="sticky top-16 z-20 mb-5 lg:top-4">{topBar}</div>}
        {children}
      </main>

      {model.open && model.settings && (
        <ModelWindow settings={model.settings} onClose={() => model.setOpen(false)} onChange={model.setSettings} />
      )}
    </div>
  )
}
