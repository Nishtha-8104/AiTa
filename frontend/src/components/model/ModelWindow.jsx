import { useEffect, useId, useState } from 'react'
import { CheckCircle2, KeyRound, PlugZap, X, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { getErrorMessage, modelAPI } from '../../utils/api'
import Button from '../ui/Button'
import { ChoiceChips, SelectField, TextField } from '../ui/Field'

const MODES = [
  { value: 'own', label: 'My key' },
  { value: 'local', label: 'Local model' },
]

function providersFor(settings, mode) {
  return settings.providers.filter(p => (mode === 'local' ? p.local : !p.local))
}

function startingProvider(settings, mode) {
  return settings.source === mode ? settings.provider : providersFor(settings, mode)[0]?.id || ''
}

export default function ModelWindow({ settings, onClose, onChange }) {
  const firstMode = settings.source === 'local' ? 'local' : 'own'
  const [mode, setMode] = useState(firstMode)
  const [provider, setProvider] = useState(() => startingProvider(settings, firstMode))
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState(settings.source === 'own' || settings.source === 'local' ? settings.model : '')
  const [models, setModels] = useState([])
  const [checks, setChecks] = useState([])
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState('')
  const listId = useId()

  const info = settings.providers.find(p => p.id === provider)
  const savedKey = settings.source !== 'default' && settings.provider === provider && settings.key_hint

  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  useEffect(() => { setBaseUrl(info?.base_url || '') }, [info])

  const switchMode = next => {
    setMode(next)
    setProvider(startingProvider(settings, next))
    setModel(settings.source === next ? settings.model : '')
    setModels([])
    setChecks([])
    setError(null)
  }

  const switchProvider = next => {
    setProvider(next)
    setModel('')
    setModels([])
    setChecks([])
    setError(null)
  }

  const changeModel = next => {
    setModel(next)
    setChecks([])
  }

  const body = () => ({ provider, model: model.trim(), api_key: apiKey.trim(), base_url: info?.local ? baseUrl.trim() : '' })

  const run = async (kind, request) => {
    setBusy(kind)
    setError(null)
    try {
      return await request()
    } catch (err) {
      setError({ detail: getErrorMessage(err), said: err?.response?.data?.provider_message })
      return null
    } finally {
      setBusy('')
    }
  }

  const test = () => run('test', async () => {
    const { data } = await modelAPI.test(body())
    setModels(data.models)
    setChecks(data.checks)
    if (!model.trim()) {
      if (data.models.length) setModel(data.models[0])
      toast.success(`Connected. ${data.models.length} models found. Pick one and test it.`)
    } else if (data.ok) {
      toast.success('All checks passed.')
    }
  })

  const save = () => run('save', async () => {
    const { data } = await modelAPI.save(body())
    onChange(data)
    toast.success(`Now using ${data.model}`)
    onClose()
  })

  const remove = () => run('remove', async () => {
    const { data } = await modelAPI.remove()
    onChange(data)
    toast.success('Model removed')
    onClose()
  })

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center" role="dialog" aria-modal="true" aria-labelledby="model-window-title">
      <button type="button" aria-label="Close" onClick={onClose} className="absolute inset-0 bg-canvas/75 backdrop-blur-sm motion-safe:animate-fade-in" />
      <div className="tile relative max-h-[calc(100dvh-2rem)] w-full max-w-lg overflow-y-auto p-6 motion-safe:animate-rise">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="model-window-title" className="text-xl font-semibold tracking-tight text-ink">Model</h2>
            <p className="mt-1 text-[13px] text-ink-subtle">
              In use: <span className="font-mono text-ink-muted">{settings.model || 'none yet'}</span>
            </p>
          </div>
          <button type="button" autoFocus onClick={onClose} aria-label="Close" className="flex h-9 w-9 items-center justify-center rounded-full text-ink-muted hover:bg-white/[0.06] hover:text-ink">
            <X size={18} />
          </button>
        </div>

        <div className="mt-5">
          <ChoiceChips label="Model source" options={MODES} value={mode} onChange={switchMode} />
          <p className="mt-2 text-xs text-ink-subtle">
            Local models (Ollama, LM Studio) run on this computer, next to PET.
          </p>
        </div>

        <form className="mt-5 flex flex-col gap-4" onSubmit={e => { e.preventDefault(); save() }}>
            <SelectField label="Provider" value={provider} onChange={e => switchProvider(e.target.value)}>
              {providersFor(settings, mode).map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
            </SelectField>

            {info?.local && (
              <TextField label="Server address" value={baseUrl} onChange={e => setBaseUrl(e.target.value)} inputClassName="font-mono text-sm" spellCheck={false} />
            )}

            {(info?.needs_key || info?.local) && (
              <TextField
                label="API key"
                optional={!info?.needs_key}
                type="password"
                autoComplete="off"
                icon={KeyRound}
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder={savedKey ? `Saved key ··${settings.key_hint}` : 'Paste your key'}
                helper="Your key stays in this browser, encrypted. PET never stores it."
              />
            )}

            <TextField
              label="Model"
              value={model}
              onChange={e => changeModel(e.target.value)}
              list={listId}
              placeholder={models.length ? 'Pick or type a model' : 'Test the connection to list models'}
              inputClassName="font-mono text-sm"
              spellCheck={false}
            />
            <datalist id={listId}>
              {models.map(m => <option key={m} value={m} />)}
            </datalist>

            {checks.length === 0 && (
              <p className="text-xs text-ink-subtle">
                Test checks the connection, tool calling, structured output and context window. A model must pass all of them to be saved.
              </p>
            )}

            {checks.length > 0 && (
              <ul className="flex flex-col gap-2 rounded-md border border-line bg-tile-2 p-3" aria-label="Model checks">
                {checks.map(c => (
                  <li key={c.name} className="flex items-start gap-2 text-[13px]">
                    {c.ok
                      ? <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-pop-mint" aria-label="Passed" />
                      : <XCircle size={15} className="mt-0.5 shrink-0 text-pop-coral" aria-label="Failed" />}
                    <span><span className="font-medium text-ink">{c.name}</span> <span className="text-ink-subtle">{c.detail}</span></span>
                  </li>
                ))}
              </ul>
            )}

            {error && (
              <div role="alert" className="rounded-md border border-pop-coral/40 bg-pop-coral/10 p-3 text-[13px] text-ink">
                <p>{error.detail}</p>
                {error.said && <p className="mt-1.5 font-mono text-[11px] text-ink-subtle">{error.said}</p>}
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" icon={PlugZap} busy={busy === 'test'} disabled={Boolean(busy)} onClick={test}>{model.trim() ? 'Test model' : 'Test connection'}</Button>
              <Button type="submit" busy={busy === 'save'} disabled={Boolean(busy) || !model.trim()}>Save</Button>
              {settings.source === mode && (
                <Button variant="ghost" busy={busy === 'remove'} disabled={Boolean(busy)} onClick={remove} className="sm:ml-auto">Remove key</Button>
              )}
            </div>
          </form>
      </div>
    </div>
  )
}
