import { useEffect, useRef } from 'react'
import { Clock, FileText, MessageSquareText, Sparkles } from 'lucide-react'
import { useFeedback } from '../hooks/useFeedback'
import FeedbackCard from '../components/feedback/FeedbackCard'
import AppShell from '../components/ui/AppShell'
import PageHeader from '../components/ui/PageHeader'
import Button from '../components/ui/Button'
import BusyNote from '../components/ui/BusyNote'
import EmptyState from '../components/ui/EmptyState'
import Skeleton from '../components/ui/Skeleton'

const TYPE_DOT = { code_review: 'bg-pop-sun', learning_recap: 'bg-pop-aqua', combined: 'bg-pop-pink' }
const TYPE_LABEL = { code_review: 'Code review', learning_recap: 'Learning recap', combined: 'Full report' }

const STEPS = [
  { after: 0, text: 'Reading your latest graded code and practice…' },
  { after: 6, text: 'Looking for mistakes you repeat…' },
  { after: 15, text: 'Writing your report…' },
  { after: 45, text: 'Almost done. Longer reports take a little more time…' },
]

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const m = Math.floor((Date.now() - new Date(dateStr)) / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m} min ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} h ago`
  return `${Math.floor(h / 24)} d ago`
}

export default function FeedbackPage() {
  const { reports, activeReport, generating, loading, fetchReports, openReport, autoGenerate } = useFeedback()
  const reportRef = useRef(null)

  useEffect(() => { fetchReports() }, [])

  useEffect(() => {
    if (activeReport && window.innerWidth < 1024) reportRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [activeReport?.id])

  const unread = reports.filter(r => !r.is_read).length

  useEffect(() => { window.dispatchEvent(new Event('pet:feedback-changed')) }, [unread, reports.length])

  return (
    <AppShell title="Feedback">
      <div className="mx-auto flex max-w-[1240px] flex-col gap-5">
        <PageHeader
          eyebrow="Feedback"
          title="Reports on your work"
          description="A report reads your latest graded code and practice, points out mistakes you repeat, and tells you what to do next."
          actions={
            <Button size="lg" icon={Sparkles} onClick={autoGenerate} busy={generating}>
              {generating ? 'Writing…' : 'Get my feedback'}
            </Button>
          }
        />

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[300px_minmax(0,1fr)] lg:items-start">
          <aside className="tile p-4 lg:sticky lg:top-8">
            <div className="mb-3 flex items-center justify-between px-1">
              <p className="eyebrow">Your reports</p>
              <span className="font-mono text-xs text-ink-faint">{unread > 0 ? `${unread} new` : reports.length}</span>
            </div>
            {loading && reports.length === 0 ? (
              <div className="space-y-2">{[1, 2, 3].map(i => <Skeleton key={i} className="h-16 rounded-2xl" />)}</div>
            ) : reports.length === 0 ? (
              <p className="px-1 py-2 text-sm text-ink-subtle">No reports yet.</p>
            ) : (
              <ul className="max-h-[60vh] space-y-1.5 overflow-y-auto pr-1">
                {reports.map(r => {
                  const active = activeReport?.id === r.id
                  return (
                    <li key={r.id}>
                      <button
                        type="button"
                        onClick={() => openReport(r.id)}
                        aria-current={active ? 'true' : undefined}
                        className={`flex w-full items-start gap-3 rounded-2xl border px-3.5 py-3 text-left transition-colors ${
                          active ? 'border-ink bg-tile-3' : 'border-transparent hover:bg-white/[0.04]'
                        }`}
                      >
                        <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${TYPE_DOT[r.feedback_type] || 'bg-pop-pink'}`} aria-hidden="true" />
                        <span className="min-w-0 flex-1">
                          <span className={`block truncate text-sm ${r.is_read ? 'text-ink-muted' : 'font-semibold text-ink'}`}>{r.headline || 'Feedback report'}</span>
                          <span className="mt-1 flex items-center gap-2 text-[11px] text-ink-subtle">
                            {TYPE_LABEL[r.feedback_type] || 'Report'}
                            <span className="flex items-center gap-1"><Clock size={10} /> {timeAgo(r.created_at)}</span>
                          </span>
                        </span>
                        {!r.is_read && <span className="mt-1 rounded-full bg-pop-pink px-1.5 py-px text-[10px] font-semibold text-canvas">New</span>}
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </aside>

          <div ref={reportRef} className="min-w-0 scroll-mt-20">
            {generating ? (
              <div className="space-y-4">
                <BusyNote active steps={STEPS} note="Reports usually take 15 to 45 seconds." />
                <div className="tile space-y-3 p-6" aria-hidden="true">
                  <Skeleton className="h-6 w-2/3" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-4/5" />
                </div>
              </div>
            ) : activeReport ? (
              <div className="motion-safe:animate-rise"><FeedbackCard report={activeReport} /></div>
            ) : reports.length > 0 ? (
              <EmptyState
                className="tile"
                icon={FileText}
                title="Pick a report to read it"
                body="Choose one from the list, or press Get my feedback for a fresh one based on your latest work."
              />
            ) : (
              <EmptyState
                className="tile"
                icon={MessageSquareText}
                title="No reports yet"
                body="Solve something in Practice or the Code workspace first, then ask for a report on how it went."
                action={<Button icon={Sparkles} onClick={autoGenerate} busy={generating}>Get my feedback</Button>}
              />
            )}
          </div>
        </div>
      </div>
    </AppShell>
  )
}
