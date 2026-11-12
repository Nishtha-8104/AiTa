import { useCallback, useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { chatAPI, getErrorMessage } from '../utils/api'
import { createSSEParser } from '../utils/sse'
import { notifyModelError } from '../components/model/notifyModelError'

const FIRST_CHECK_MS = 800
const RECOVER_EVERY_MS = 2500
const RECOVER_TRIES = 24
const RECENT_MS = 3 * 60 * 1000

const BUSY_NOTICE = 'PET is still answering your previous message in this chat. Your new message was not sent — try again once the reply arrives.'
const LOST_NOTICE = 'The reply is taking longer than usual. Reopen this chat in a minute to see it.'
const OFFLINE_NOTICE = "Couldn't reach PET. Check your connection and try again."
const FAILED_REPLY = 'Sorry — something went wrong. Please try again.'
const RETRYABLE = new Set(['busy', 'error'])

let seq = 0
const localId = (kind) => `local-${kind}-${++seq}`
const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms))
const lastOf = (list) => list[list.length - 1]

const liveReply = (status = 'thinking') =>
  ({ id: localId('a'), role: 'assistant', content: '', live: true, status, tools: [] })

const stored = (final) => ({
  id: final.message_id,
  role: 'assistant',
  content: final.content || '',
  citations: final.citations || [],
  tool_calls: final.tool_calls || [],
  moderation_flag: final.moderation_flag || null,
  thumbs: null,
})

function settle(tools, trace) {
  const i = tools.findIndex(t => t.running && t.name === trace.name)
  if (i === -1) return [...tools, trace]
  return tools.map((t, j) => (j === i ? trace : t))
}

async function describeFailure(res) {
  if (res.status === 404) return 'This chat could not be found. Start a new chat.'
  try {
    const body = await res.json()
    return getErrorMessage({ response: { data: body } }, `PET couldn't take that message (error ${res.status}).`)
  } catch {
    return `PET couldn't take that message (error ${res.status}). Try again.`
  }
}

export default function useChatStream({ startFresh = false } = {}) {
  const [threads, setThreads]     = useState([])
  const [threadId, setThreadId]   = useState(null)
  const [messages, setMessages]   = useState([])
  const [streaming, setStreaming] = useState(false)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)

  const controllerRef = useRef(null)
  // Bumped whenever the conversation on screen changes; late results of older work are dropped.
  const genRef        = useRef(0)
  const busyRef       = useRef(false)
  const touchedRef    = useRef(false)
  const startFreshRef = useRef(startFresh)

  const patchLive = useCallback((fn) => {
    setMessages(list => list.map(m => (m.live ? fn(m) : m)))
  }, [])

  const dropLive = useCallback(() => {
    setMessages(list => list.filter(m => !m.live))
  }, [])

  const refreshThreads = useCallback(() =>
    chatAPI.listThreads().then(({ data }) => setThreads(data)).catch(() => {}), [])

  const release = useCallback(() => {
    genRef.current += 1
    controllerRef.current?.abort()
    controllerRef.current = null
    busyRef.current = false
    setStreaming(false)
  }, [])

  // The server finishes and saves a turn even when nobody is listening, so a lost
  // or refused stream is followed by re-reading the thread until the reply is there.
  const recover = useCallback(async (id, gen, { hold = false, tries = RECOVER_TRIES, giveUp } = {}) => {
    const current = () => gen === genRef.current
    if (hold) {
      busyRef.current = true
      setStreaming(true)
    }
    const finish = () => {
      if (!hold) return
      busyRef.current = false
      setStreaming(false)
    }
    for (let i = 0; i < tries; i++) {
      await wait(i === 0 ? FIRST_CHECK_MS : RECOVER_EVERY_MS)
      if (!current()) return
      try {
        const { data } = await chatAPI.getThread(id)
        if (!current()) return
        if (lastOf(data.messages)?.role === 'assistant') {
          setMessages(data.messages)
          setError(null)
          finish()
          refreshThreads()
          return
        }
      } catch {
        /* keep trying */
      }
    }
    if (!current()) return
    giveUp?.()
    finish()
  }, [refreshThreads])

  const openThread = useCallback(async (id) => {
    touchedRef.current = true
    release()
    const gen = genRef.current
    setThreadId(id)
    setMessages([])
    setError(null)
    setLoading(true)
    try {
      const { data } = await chatAPI.getThread(id)
      if (gen !== genRef.current) return
      const last = lastOf(data.messages)
      const pending = last?.role === 'user'
        && Date.now() - new Date(last.created_at).getTime() < RECENT_MS
      setMessages(pending ? [...data.messages, liveReply('waiting')] : data.messages)
      if (pending) recover(id, gen, { hold: true, giveUp: dropLive })
    } catch (err) {
      if (gen === genRef.current) setError(getErrorMessage(err, 'Could not open this chat.'))
    } finally {
      if (gen === genRef.current) setLoading(false)
    }
  }, [dropLive, recover, release])

  const newChat = useCallback(() => {
    touchedRef.current = true
    release()
    setThreadId(null)
    setMessages([])
    setError(null)
    setLoading(false)
  }, [release])

  const send = useCallback(async (content, language) => {
    const text = (content || '').trim()
    if (!text) return { ok: false }
    if (busyRef.current) return { ok: false, restore: true }
    touchedRef.current = true
    busyRef.current = true
    const gen = ++genRef.current
    const current = () => gen === genRef.current
    const done = () => {
      if (!current()) return
      busyRef.current = false
      setStreaming(false)
    }

    const userMsg = { id: localId('u'), role: 'user', content: text }
    setError(null)
    setStreaming(true)
    setMessages(list => {
      const kept = list.filter(m => !m.live)
      const [asked, failed] = kept.slice(-2)
      // Same rule as the server: retrying a failed reply replaces that exchange.
      const retry = failed?.role === 'assistant' && RETRYABLE.has(failed.moderation_flag)
        && asked?.role === 'user' && asked.content === text
      return [...(retry ? kept.slice(0, -2) : kept), userMsg, liveReply()]
    })

    const withdraw = (notice) => {
      if (!current()) return { ok: false }
      setMessages(list => list.filter(m => m !== userMsg && !m.live))
      setError(notice)
      done()
      return { ok: false, restore: true }
    }

    const controller = new AbortController()
    controllerRef.current = controller
    let id = threadId
    let res
    try {
      if (!id) {
        const { data } = await chatAPI.createThread()
        if (!current()) return { ok: false }
        id = data.id
        setThreadId(id)
        setThreads(list => [data, ...list])
      }
      res = await chatAPI.send(id, { content: text, language }, controller.signal)
    } catch (err) {
      if (err?.name === 'AbortError' || !current()) return { ok: false }
      return withdraw(err?.response ? getErrorMessage(err) : OFFLINE_NOTICE)
    }
    if (!current()) return { ok: false }

    if (res.status === 409) {
      setMessages(list => [...list.filter(m => m !== userMsg && !m.live), liveReply('waiting')])
      setError(BUSY_NOTICE)
      recover(id, gen, { hold: true, giveUp: dropLive })
      return { ok: false, restore: true }
    }
    if (!res.ok) return withdraw(await describeFailure(res))

    let ended = null
    let modelFailed = false
    const push = createSSEParser((event, data) => {
      if (!current()) return
      if (event === 'tool_start') {
        patchLive(m => ({ ...m, tools: [...m.tools, { name: data.name, args: data.args, running: true }] }))
      } else if (event === 'tool_end' && data.trace) {
        patchLive(m => ({ ...m, tools: settle(m.tools, data.trace) }))
      } else if (event === 'token') {
        patchLive(m => ({ ...m, content: m.content + (data.text || '') }))
      } else if (event === 'final') {
        ended = 'final'
        setMessages(list => list.map(m => (m.live ? stored(data) : m)))
      } else if (event === 'error') {
        ended = 'error'
        modelFailed = Boolean(data.code)
        if (modelFailed) notifyModelError({ detail: data.message })
        setMessages(list => list.map(m => (m.live ? {
          ...m, live: false, content: data.message || FAILED_REPLY, moderation_flag: 'error',
          tool_calls: m.tools.filter(t => !t.running),
        } : m)))
      }
    })

    try {
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      for (;;) {
        const { value, done: finished } = await reader.read()
        if (finished) break
        push(decoder.decode(value, { stream: true }))
      }
      push(decoder.decode())
    } catch (err) {
      if (err?.name === 'AbortError' || !current()) return { ok: false }
    }
    if (!current()) return { ok: false }

    if (ended === 'final') {
      done()
      refreshThreads()
      return { ok: true }
    }
    if (ended === 'error') {
      done()
      // Retrying a rejected key only repeats the error.
      if (!modelFailed) recover(id, gen, { tries: 3 })
      return { ok: false }
    }
    patchLive(m => ({ ...m, status: 'reconnecting' }))
    recover(id, gen, {
      hold: true,
      giveUp: () => { dropLive(); setError(LOST_NOTICE) },
    })
    return { ok: false }
  }, [dropLive, patchLive, recover, refreshThreads, threadId])

  const setThumbs = useCallback(async (message, value) => {
    const previous = message.thumbs ?? null
    const apply = (thumbs) =>
      setMessages(list => list.map(m => (m.id === message.id ? { ...m, thumbs } : m)))
    apply(value)
    try {
      await chatAPI.thumbs(message.id, value)
    } catch {
      apply(previous)
      toast.error('Could not save your feedback')
    }
  }, [])

  useEffect(() => {
    let alive = true
    chatAPI.listThreads()
      .then(({ data }) => {
        if (!alive) return
        setThreads(data)
        if (!startFreshRef.current && !touchedRef.current && data.length) openThread(data[0].id)
      })
      .catch(() => {})
    return () => {
      alive = false
      release()
    }
  }, [openThread, release])

  return {
    threads, threadId, messages, streaming, loading, error,
    send, openThread, newChat, setThumbs,
    abort: release,
    clearError: () => setError(null),
  }
}
