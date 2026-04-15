import { useState, useCallback, useRef } from 'react'
import { contentPlayerAPI } from '../utils/api'
import toast from 'react-hot-toast'

export function useContentPlayer() {
  const [sessions, setSessions]           = useState([])
  const [activeSession, setActiveSession] = useState(null)
  const [messages, setMessages]           = useState([])
  const [sending, setSending]             = useState(false)
  const [loading, setLoading]             = useState(false)
  const [creating, setCreating]           = useState(false)
  const abortRef                          = useRef(null)

  // ─── Load all sessions ────────────────────────────────────────────────────
  const fetchSessions = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await contentPlayerAPI.getSessions()
      setSessions(data)
    } catch {
      toast.error('Failed to load sessions.')
    } finally {
      setLoading(false)
    }
  }, [])

  // ─── Open/load a session ──────────────────────────────────────────────────
  const openSession = useCallback(async (sessionId) => {
    setLoading(true)
    try {
      const { data } = await contentPlayerAPI.getSession(sessionId)
      const sessionData = data.session || data
      const msgs = data.messages || []
      setActiveSession(sessionData)
      setMessages(msgs)
    } catch {
      toast.error('Failed to load session.')
    } finally {
      setLoading(false)
    }
  }, [])

  // ─── Create a new session ─────────────────────────────────────────────────
  const createSession = useCallback(async ({ mode, language, topic }) => {
    setCreating(true)
    try {
      const { data } = await contentPlayerAPI.createSession({ mode, language, topic })
      setActiveSession(data)
      setMessages([])
      setSessions(prev => [data, ...prev])
      return data
    } catch {
      toast.error('Failed to create session.')
      return null
    } finally {
      setCreating(false)
    }
  }, [])

  // ─── Send a message ───────────────────────────────────────────────────────
  const sendMessage = useCallback(async ({
    sessionId,
    message,
    codeSnippet,
    codeLanguage,
    errorMessage,
  }) => {
    if (!message.trim()) return null
    setSending(true)

    // Optimistically add user message to UI immediately
    const tempUserMsg = {
      id:           `temp-${Date.now()}`,
      role:         'user',
      content:      message,
      has_code:     !!codeSnippet,
      code_snippet: codeSnippet || null,
      code_language:codeLanguage || null,
      error_message:errorMessage || null,
      created_at:   new Date().toISOString(),
      _pending:     true,
    }
    setMessages(prev => [...prev, tempUserMsg])

    // Add a typing indicator
    const typingMsg = { id: 'typing', role: 'assistant', content: '', _typing: true }
    setMessages(prev => [...prev, typingMsg])

    try {
      const { data } = await contentPlayerAPI.chat(sessionId, {
        message,
        code_snippet:  codeSnippet  || undefined,
        code_language: codeLanguage || undefined,
        error_message: errorMessage || undefined,
      })

      // Replace typing indicator with real response
      const assistantMsg = {
        id:             data.message_id,
        role:           'assistant',
        content:        data.response,
        tokens_used:    data.tokens_used,
        latency_ms:     data.latency_ms,
        was_helpful:    null,
        created_at:     new Date().toISOString(),
        _concepts:      data.concepts || data.detected_concepts || [],
        _suggestions:   data.follow_up_suggestions || [],
        _confusion:     data.comfort_signal === 'struggling' || data.confusion_detected,
      }

      setMessages(prev =>
        prev
          .filter(m => m.id !== 'typing' && m.id !== tempUserMsg.id)
          .concat([{ ...tempUserMsg, id: tempUserMsg.id, _pending: false }, assistantMsg])
      )

      // Update active session metadata
      setActiveSession(prev => prev ? {
        ...prev,
        title:            data.session_title || prev.title,
        difficulty:       data.difficulty || prev.difficulty,
        total_messages:   (prev.total_messages || 0) + 2,
        last_message_at:  new Date().toISOString(),
      } : prev)

      // Notify user of mastery milestones
      if (data.question_solved) {
        toast.success('✅ Question marked as solved! Great work.')
      }
      if (data.difficulty_increased) {
        toast.success(`🚀 Difficulty increased to ${data.difficulty}! You're on a roll.`)
      }

      // Update session in the sidebar list
      setSessions(prev => prev.map(s =>
        s.id === sessionId
          ? { ...s, title: data.session_title || s.title, last_message_at: new Date().toISOString() }
          : s
      ))

      return data
    } catch (err) {
      setMessages(prev => prev.filter(m => m.id !== 'typing' && m.id !== tempUserMsg.id))
      const errMsg = err.response?.data?.detail || 'Failed to get response. Check your Groq API key.'
      toast.error(errMsg)
      return null
    } finally {
      setSending(false)
    }
  }, [])

  // ─── Rate a message ───────────────────────────────────────────────────────
  const rateMessage = useCallback(async (messageId, wasHelpful) => {
    try {
      await contentPlayerAPI.rateMessage(messageId, wasHelpful)
      setMessages(prev =>
        prev.map(m => m.id === messageId ? { ...m, was_helpful: wasHelpful } : m)
      )
    } catch {
      // silent
    }
  }, [])
  const archiveSession = useCallback(async (sessionId) => {
    try {
      await contentPlayerAPI.archiveSession(sessionId)
      setSessions(prev => prev.filter(s => s.id !== sessionId))
      if (activeSession?.id === sessionId) {
        setActiveSession(null)
        setMessages([])
      }
      toast.success('Session archived.')
    } catch {
      toast.error('Failed to archive session.')
    }
  }, [activeSession])

  // ─── Clear active session (go to home) ───────────────────────────────────
  const clearActive = useCallback(() => {
    setActiveSession(null)
    setMessages([])
  }, [])

  return {
    sessions, activeSession, messages,
    sending, loading, creating,
    fetchSessions, openSession, createSession,
    sendMessage, rateMessage, archiveSession, clearActive,
  }
}