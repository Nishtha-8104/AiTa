import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { MessageSquareText, RefreshCw } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { feedbackAPI, gamificationAPI, practiceSessionAPI, profileAPI } from '../utils/api'
import AppShell from '../components/ui/AppShell'
import Button from '../components/ui/Button'
import { SkeletonTile } from '../components/ui/Skeleton'
import HeroTile from '../components/dashboard/HeroTile'
import TopicLevelsTile from '../components/dashboard/TopicLevelsTile'
import TopicRing from '../components/dashboard/TopicRing'
import ProgressTile from '../components/dashboard/ProgressTile'
import ActivityTile from '../components/dashboard/ActivityTile'
import Shortcuts from '../components/dashboard/Shortcuts'
import LastSessionCard from '../components/dashboard/LastSessionCard'
import ChatPanel from '../components/chat/ChatPanel'

function LoadError({ onRetry }) {
  return (
    <section className="tile flex flex-col items-start gap-4 p-6 md:col-span-6">
      <div>
        <p className="eyebrow">Topic levels</p>
        <p className="mt-2 text-sm text-ink-muted">Couldn't load your topic levels. Check your connection, then try again.</p>
      </div>
      <Button size="sm" variant="secondary" icon={RefreshCw} onClick={onRetry}>Try again</Button>
    </section>
  )
}

function rise(i) {
  return `motion-safe:animate-rise ${['', '[animation-delay:70ms]', '[animation-delay:140ms]', '[animation-delay:210ms]', '[animation-delay:280ms]'][i]}`
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [ask] = useState(() => searchParams.get('ask') || '')
  const [chatOpen, setChatOpen] = useState(Boolean(ask))

  useEffect(() => {
    if (searchParams.has('ask')) setSearchParams({}, { replace: true })
  }, [searchParams, setSearchParams])

  const [mastery, setMastery] = useState({ data: null, error: false })
  const [progress, setProgress] = useState(null)
  const [unread, setUnread] = useState(0)
  const [lastSession, setLastSession] = useState(null)

  const loadMastery = useCallback(() => {
    setMastery({ data: null, error: false })
    profileAPI.getMastery()
      .then(({ data }) => setMastery({ data, error: false }))
      .catch(() => setMastery({ data: null, error: true }))
  }, [])

  useEffect(() => {
    loadMastery()
    gamificationAPI.me().then(({ data }) => setProgress(data)).catch(() => setProgress(null))
    feedbackAPI.unreadCount().then(({ data }) => setUnread(data.unread ?? 0)).catch(() => {})
    practiceSessionAPI.pending().then(({ data }) => setLastSession(data)).catch(() => {})
  }, [loadMastery])

  useEffect(() => {
    if (!chatOpen) return
    const onKey = e => { if (e.key === 'Escape') setChatOpen(false) }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [chatOpen])

  const topics = mastery.data?.topics
  const loading = !mastery.data && !mastery.error
  const [revealed, setRevealed] = useState(false)
  const showProgress = progress && progress.mode !== 'off'
  const progressOpen = showProgress && (progress.mode === 'live' || revealed)

  return (
    <AppShell title="Home">
      <div className="mx-auto max-w-[1480px] pb-20 xl:grid xl:pb-0 xl:grid-cols-[minmax(0,1fr)_360px] 2xl:grid-cols-[minmax(0,1fr)_400px] xl:items-start xl:gap-6">
        <div className="grid min-w-0 grid-cols-1 gap-4 md:grid-cols-6 md:gap-5">
          <div className={`md:col-span-6 ${rise(0)}`}>
            <HeroTile user={user} topics={topics} loading={loading} />
          </div>

          {lastSession && (
            <div className={`md:col-span-6 ${rise(1)}`}>
              <LastSessionCard session={lastSession} />
            </div>
          )}

          {mastery.error ? (
            <LoadError onRetry={loadMastery} />
          ) : loading ? (
            <>
              <SkeletonTile className="h-[420px] md:col-span-4" lines={6} />
              <SkeletonTile className="h-[420px] md:col-span-2" lines={2} />
              <SkeletonTile className="h-[320px] md:col-span-6" lines={4} />
            </>
          ) : (
            <>
              <div className={`md:col-span-4 ${rise(1)}`}>
                <TopicLevelsTile topics={topics} />
              </div>
              <div className={`md:col-span-2 ${rise(2)}`}>
                <TopicRing topics={topics} />
              </div>
              {showProgress && (
                <div className={`${progressOpen ? 'md:col-span-3' : 'md:col-span-6'} ${rise(3)}`}>
                  <ProgressTile data={progress} revealed={revealed} onReveal={() => setRevealed(true)} />
                </div>
              )}
              <div className={`${progressOpen ? 'md:col-span-3' : 'md:col-span-6'} ${rise(3)}`}>
                <ActivityTile mastery={mastery.data} wide={!progressOpen} />
              </div>
            </>
          )}

          <div className={`md:col-span-6 ${rise(4)}`}>
            <Shortcuts unread={unread} />
          </div>
        </div>

        <aside
          className={`${chatOpen ? 'fixed inset-0 z-40 flex bg-canvas p-2 sm:p-4' : 'hidden'} xl:sticky xl:inset-auto xl:top-8 xl:z-auto xl:flex xl:h-[calc(100dvh-4rem)] xl:bg-transparent xl:p-0`}
          aria-label="Ask PET"
        >
          <ChatPanel initialPrompt={ask} className="h-full w-full" onClose={() => setChatOpen(false)} />
        </aside>
      </div>

      {!chatOpen && (
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          className="fixed bottom-5 right-5 z-30 flex h-12 items-center gap-2 rounded-full bg-ink px-5 text-sm font-semibold text-canvas shadow-[0_12px_30px_-8px_rgba(0,0,0,0.7)] transition-transform active:scale-[0.97] xl:hidden"
        >
          <MessageSquareText size={18} /> Ask PET
        </button>
      )}
    </AppShell>
  )
}
