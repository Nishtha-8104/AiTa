import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Award, Building, Lightbulb, Lock, MapPin, Save, Shield, Target, User } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '../hooks/useAuth'
import { userAPI, onboardingAPI, getErrorMessage } from '../utils/api'
import BandSummary, { conceptLine } from '../components/onboarding/BandSummary'
import {
  AboutFields, LearningFields, aboutForm, aboutPayload, aboutComplete, learningForm, learningComplete,
} from '../components/onboarding/BackgroundFields'
import { YEARS } from '../components/onboarding/options'
import { LANGUAGES } from '../components/code/templates'
import { languageLabel } from '../components/learning/labels'
import { LanguagePicker } from '../components/practice/Workbench'
import AppShell from '../components/ui/AppShell'
import Button from '../components/ui/Button'
import Chip from '../components/ui/Chip'
import Tabs from '../components/ui/Tabs'
import Skeleton from '../components/ui/Skeleton'
import { TextArea, TextField } from '../components/ui/Field'

const TABS = [
  { value: 'profile', label: 'Profile info', icon: User },
  { value: 'learning', label: 'Learning', icon: Target },
  { value: 'privacy', label: 'Privacy', icon: Shield },
]

const PRIVATE = ['Your name', 'Your code', 'Your chat messages']

function Panel({ title, description, children }) {
  return (
    <section className="tile p-5 sm:p-7">
      {title && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold tracking-tight text-ink">{title}</h2>
          {description && <p className="mt-1 text-sm leading-relaxed text-ink-subtle">{description}</p>}
        </div>
      )}
      {children}
    </section>
  )
}

export default function ProfilePage() {
  const { user, updateUser, refreshUser } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    full_name: user?.full_name || '',
    bio: user?.bio || '',
    institution: user?.institution || '',
    year_of_study: user?.year_of_study || '',
    city: user?.city || '',
    state: user?.state || '',
    years_of_experience: user?.years_of_experience || 0,
  })
  const language = user?.preferred_language || 'c'

  const [saving, setSaving] = useState(false)
  const [savingConsent, setSavingConsent] = useState(false)
  const [consent, setConsent] = useState(user?.data_sharing_consent ?? false)
  const [activeTab, setActiveTab] = useState('profile')
  const [card, setCard] = useState(null)
  const [cardLoading, setCardLoading] = useState(true)
  const [aboutPrefs, setAboutPrefs] = useState(null)
  const [learningPrefs, setLearningPrefs] = useState(null)
  const [aboutDirty, setAboutDirty] = useState(false)
  const [savingPrefs, setSavingPrefs] = useState(false)
  const [switchTo, setSwitchTo] = useState(null)
  const [switching, setSwitching] = useState(false)

  const set = field => e => setForm(f => ({ ...f, [field]: e.target.value }))

  useEffect(() => {
    onboardingAPI.state()
      .then(({ data }) => {
        if (data.current_step !== 'done' || !data.card) return
        setCard(data.card)
        setAboutPrefs(aboutForm(data.answers?.about, user))
        setLearningPrefs(learningForm(data.answers?.learning))
      })
      .catch(() => {})
      .finally(() => setCardLoading(false))
  }, [])

  const handleSwitchLanguage = async () => {
    setSwitching(true)
    try {
      const { data } = await onboardingAPI.switchLanguage(switchTo)
      updateUser({ preferred_language: data.language })
      setSwitchTo(null)
      if (data.needs_check) {
        navigate('/language-check')
        return
      }
      toast.success(`Switched to ${languageLabel(data.language)}.`)
      const { data: state } = await onboardingAPI.state()
      if (state.card) setCard(state.card)
    } catch (err) {
      toast.error(getErrorMessage(err, 'Could not switch language.'))
    } finally {
      setSwitching(false)
    }
  }

  const handleSavePrefs = async () => {
    setSavingPrefs(true)
    try {
      const body = { learning: learningPrefs }
      if (aboutDirty) {
        const about = aboutPayload(aboutPrefs)
        body.about = { ...about, year_of_study: YEARS.some(y => y.value === about.year_of_study) ? about.year_of_study : null }
      }
      const { data } = await onboardingAPI.editProfile(body)
      setCard(data)
      setAboutPrefs(aboutForm(data.preferences?.about, user))
      setLearningPrefs(learningForm(data.preferences?.learning))
      setAboutDirty(false)
      toast.success('Preferences saved.')
      try {
        const me = await refreshUser()
        setForm(f => ({
          ...f,
          years_of_experience: me.years_of_experience || 0,
          year_of_study: me.year_of_study || '',
          institution: me.institution || '',
        }))
      } catch { /* ignore */ }
    } catch (err) {
      toast.error(getErrorMessage(err, 'Could not save your preferences.'))
    } finally {
      setSavingPrefs(false)
    }
  }

  const handleSaveProfile = async () => {
    setSaving(true)
    try {
      const payload = {
        ...form,
        year_of_study: form.year_of_study === '' || form.year_of_study === null ? null : parseInt(form.year_of_study, 10) || null,
        years_of_experience: parseFloat(form.years_of_experience) || 0,
      }
      const { data } = await userAPI.updateProfile(payload)
      updateUser(data)
      setAboutPrefs(a => a && { ...a, year_of_study: data.year_of_study ?? null, institution: data.institution ?? '' })
      toast.success('Profile saved.')
    } catch (err) {
      toast.error(getErrorMessage(err, "Couldn't save your profile."))
    } finally {
      setSaving(false)
    }
  }

  const handleConsentToggle = async (value) => {
    setSavingConsent(true)
    try {
      await userAPI.updateConsent(value)
      setConsent(value)
      updateUser({ data_sharing_consent: value })
      toast.success(value ? 'Research sharing turned on.' : 'Research sharing turned off.')
    } catch {
      toast.error("Couldn't update this setting. Try again.")
    } finally {
      setSavingConsent(false)
    }
  }

  const name = user?.full_name || user?.username || 'You'
  const initials = name.split(/\s+/).map(p => p[0]).join('').slice(0, 2).toUpperCase()

  return (
    <AppShell title="Profile">
      <div className="mx-auto flex max-w-3xl flex-col gap-5">
        <header className="tile flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:p-7">
          <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-ink font-mono text-xl font-semibold text-canvas shadow-[0_5px_0_theme(colors.key.ink)]" aria-hidden="true">
            {initials}
          </span>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-2xl font-semibold tracking-tight text-ink">{name}</h1>
            <p className="mt-1 truncate text-sm text-ink-subtle">@{user?.username}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Chip tone="aqua">Coding in {languageLabel(language)}</Chip>
            <Chip className="capitalize">{user?.role}</Chip>
          </div>
        </header>

        <Tabs tabs={TABS} value={activeTab} onChange={setActiveTab} label="Profile sections" className="self-start" />

        {activeTab === 'profile' && (
          <Panel title="Profile info" description="Shown only to you. Your institution and year also help pitch explanations.">
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              <TextField label="Full name" icon={User} value={form.full_name} onChange={set('full_name')} placeholder="Your full name" />
              <TextField label="Institution" icon={Building} value={form.institution} onChange={set('institution')} placeholder="College or university" />
              <TextField label="City" icon={MapPin} value={form.city} onChange={set('city')} placeholder="Your city" />
              <TextField label="State" value={form.state} onChange={set('state')} placeholder="Your state" />
              <TextField label="Year of study" type="number" min="1" max="6" value={form.year_of_study} onChange={set('year_of_study')} placeholder="e.g. 2" />
              <TextField label="Years of coding experience" type="number" min="0" max="50" step="0.5" value={form.years_of_experience}
                onChange={e => setForm(f => ({ ...f, years_of_experience: parseFloat(e.target.value) || 0 }))} />
            </div>
            <TextArea className="mt-5" label="Bio" optional value={form.bio} onChange={set('bio')} placeholder="A line or two about you" rows={3} />
            <div className="mt-6 flex justify-end border-t border-line pt-5">
              <Button icon={Save} onClick={handleSaveProfile} busy={saving}>{saving ? 'Saving…' : 'Save changes'}</Button>
            </div>
          </Panel>
        )}

        {activeTab === 'learning' && (
          <>
            <Panel title="Your language" description="Practice questions, debug challenges and your topic levels follow this language.">
              {cardLoading ? (
                <Skeleton className="h-10 w-56 rounded-full" />
              ) : (
                <>
                  <LanguagePicker
                    languages={LANGUAGES}
                    value={switchTo || language}
                    onChange={v => setSwitchTo(v === language ? null : v)}
                    disabled={!card || switching}
                  />
                  {!card && <p className="mt-2 text-xs text-ink-subtle">You can switch once your starting check is done.</p>}
                </>
              )}
              {switchTo && (
                <div className="mt-5 space-y-3 rounded-[20px] border border-line-strong bg-tile-3 p-5 motion-safe:animate-rise" role="alert">
                  <p className="text-sm text-ink">
                    Switch to {languageLabel(switchTo)}? Your {languageLabel(language)} progress is kept and comes back when you switch back.
                  </p>
                  <p className="text-xs text-ink-subtle">
                    If you haven't studied {languageLabel(switchTo)} here before, you'll take a short code check in it first (about 4 minutes).
                  </p>
                  <div className="flex flex-wrap gap-2 pt-1">
                    <Button onClick={handleSwitchLanguage} busy={switching}>{switching ? 'Switching…' : `Switch to ${languageLabel(switchTo)}`}</Button>
                    <Button variant="secondary" onClick={() => setSwitchTo(null)} disabled={switching}>Cancel</Button>
                  </div>
                </div>
              )}
              <div className="mt-6 flex items-center justify-between gap-3 border-t border-line pt-5">
                <span className="text-sm text-ink-muted">Skill level</span>
                <span className="text-right text-sm">
                  <span className="font-medium capitalize text-ink">{user?.skill_level || 'beginner'}</span>
                  <span className="block text-xs text-ink-subtle">From your starting check</span>
                </span>
              </div>
            </Panel>

            {learningPrefs && (
              <Panel title="Background and preferences" description="Hints, feedback and chat follow these.">
                <div className="space-y-8">
                  <LearningFields form={learningPrefs} onChange={setLearningPrefs} />
                  <AboutFields form={aboutPrefs} withSchool={false} onChange={f => { setAboutPrefs(f); setAboutDirty(true) }} />
                </div>
                <div className="mt-6 flex justify-end border-t border-line pt-5">
                  <Button
                    icon={Save}
                    onClick={handleSavePrefs}
                    busy={savingPrefs}
                    disabled={!learningComplete(learningPrefs) || (aboutDirty && !aboutComplete(aboutPrefs))}
                  >
                    {savingPrefs ? 'Saving…' : 'Save preferences'}
                  </Button>
                </div>
              </Panel>
            )}

            {card && (
              <Panel title="Starting check" description="Your result from onboarding. It can't be edited. Practice updates your topic levels from here on.">
                <p className="mb-5 flex items-center gap-2 text-lg font-semibold text-ink">
                  <Award size={18} className="text-pop-mint" aria-hidden="true" /> {card.title}
                </p>
                <BandSummary card={card} headingLevel={4} />
                <p className="mt-5 flex items-center gap-2 text-sm text-ink-muted">
                  <Lightbulb size={16} className="shrink-0 text-pop-sun" aria-hidden="true" /> {conceptLine(card)}
                </p>
              </Panel>
            )}
          </>
        )}

        {activeTab === 'privacy' && (
          <Panel title="Privacy" description="You decide whether your activity helps research.">
            <div className="flex items-start justify-between gap-4 rounded-[20px] border border-line bg-tile-2 p-5">
              <div className="flex-1">
                <p id="consent-label" className="text-[15px] font-medium text-ink">Allow your anonymised activity to be used for research and to improve PET</p>
                <p id="consent-desc" className="mt-1.5 text-xs leading-relaxed text-ink-subtle">
                  This covers things like your scores, how many hints you used and how your topic levels changed, with your name removed. You can turn it off at any time.
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={consent}
                aria-labelledby="consent-label"
                aria-describedby="consent-desc"
                onClick={() => handleConsentToggle(!consent)}
                disabled={savingConsent}
                className={`relative h-7 w-12 shrink-0 rounded-full transition-colors duration-300 disabled:opacity-50 ${consent ? 'bg-pop-mint' : 'bg-tile-3'}`}
              >
                <span className={`absolute top-1 h-5 w-5 rounded-full bg-ink shadow transition-transform duration-300 ${consent ? 'translate-x-6' : 'translate-x-1'}`} />
                <span className="sr-only">{consent ? 'On' : 'Off'}</span>
              </button>
            </div>
            <div className="mt-5">
              <p className="eyebrow">Never shared</p>
              <ul className="mt-3 divide-y divide-line">
                {PRIVATE.map(item => (
                  <li key={item} className="flex items-center justify-between py-3 text-sm text-ink-muted">
                    {item}
                    <Chip tone="mint" icon={Lock}>Private</Chip>
                  </li>
                ))}
              </ul>
            </div>
          </Panel>
        )}
      </div>
    </AppShell>
  )
}
