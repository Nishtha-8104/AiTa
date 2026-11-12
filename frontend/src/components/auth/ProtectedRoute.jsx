import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import LogoMark from '../ui/LogoMark'

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex min-h-[100dvh] flex-col items-center justify-center gap-4" role="status">
        <LogoMark className="h-11 w-11 motion-safe:animate-pulse" />
        <p className="text-sm text-ink-subtle">Loading PET…</p>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="flex min-h-[100dvh] flex-col items-center justify-center gap-4 px-4 text-center" role="alert">
        <LogoMark className="h-11 w-11" />
        <p className="text-sm text-ink">PET&apos;s backend is not answering.</p>
        <p className="max-w-sm text-sm text-ink-subtle">Check that it is running, then reload this page.</p>
      </div>
    )
  }

  if (user.role === 'student' && !user.onboarding_done && location.pathname !== '/onboarding') {
    return <Navigate to="/onboarding" replace />
  }

  return children
}