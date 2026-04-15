import { useState, useCallback } from 'react'
import { recommendationAPI } from '../utils/api'
import toast from 'react-hot-toast'

export function useRecommendations() {
  const [recommendations, setRecommendations] = useState([])
  const [agentLog,        setAgentLog]        = useState(null)
  const [thoughtSteps,    setThoughtSteps]    = useState([])
  const [loading,         setLoading]         = useState(false)
  const [generating,      setGenerating]      = useState(false)

  // ─── Fetch stored recommendations ──────────────────────────────────────────
  const fetchRecommendations = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await recommendationAPI.getAll()
      setRecommendations(data)
    } catch (err) {
      if (err.response?.status !== 404) {
        // silent on 404 (no recommendations yet)
        toast.error('Failed to load recommendations.')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  // ─── Fetch agent run log ────────────────────────────────────────────────────
  const fetchAgentLog = useCallback(async () => {
    try {
      const { data } = await recommendationAPI.getAgentLog()
      setAgentLog(data)
      setThoughtSteps(data.step_log || [])
    } catch {
      // No log yet — that's fine on first load
    }
  }, [])

  // ─── Run the AI Agent ───────────────────────────────────────────────────────
  // Auto-seed is now handled by the backend agent itself.
  // The frontend just shows animated progress steps while waiting.
  const runAgent = useCallback(async () => {
    setGenerating(true)
    setThoughtSteps([])
    setRecommendations([])

    const progressSteps = [
      '📦 Checking content catalog (auto-seeding if empty)...',
      '🔍 Extracting your learning profile & history...',
      '🤝 Running Collaborative Filtering across all learners...',
      '📚 Matching content topics to your interests & weak areas...',
      '⚙️  Merging scores + applying RL exploration bonus...',
      '🎬 Fetching real YouTube videos for content items...',
      '🤖 Sending top candidates to Groq AI for reasoning...',
      '🧠 Groq re-ranking and writing personalised explanations...',
      '💾 Persisting your personalised recommendations...',
    ]

    let stepIdx = 0
    const interval = setInterval(() => {
      if (stepIdx < progressSteps.length) {
        setThoughtSteps(prev => [...prev, progressSteps[stepIdx]])
        stepIdx++
      }
    }, 900)

    try {
      const { data } = await recommendationAPI.generate()
      clearInterval(interval)

      // Replace animated steps with real backend thought log
      setThoughtSteps(data.agent_thought_steps || progressSteps)

      // Fetch final recommendations (now with real YouTube URLs)
      const { data: recs } = await recommendationAPI.getAll()
      setRecommendations(recs)

      await fetchAgentLog()
      toast.success(`✅ ${data.total} personalised recommendations ready!`)
    } catch (err) {
      clearInterval(interval)
      setThoughtSteps(prev => [
        ...prev,
        `❌ Error: ${
          Array.isArray(err.response?.data?.detail)
            ? err.response.data.detail.map(e => e.msg || JSON.stringify(e)).join(', ')
            : err.response?.data?.detail || err.message
        }`,
      ])
      toast.error('Agent run failed. Check GROQ_API_KEY in your .env')
    } finally {
      setGenerating(false)
    }
  }, [fetchAgentLog])

  // ─── Log interaction ────────────────────────────────────────────────────────
  const logInteraction = useCallback(async (contentId, interaction, extra = {}) => {
    try {
      await recommendationAPI.logInteraction({ content_id: contentId, interaction, ...extra })
    } catch {
      // silent — interaction logging should never block UI
    }
  }, [])

  // ─── Dismiss ────────────────────────────────────────────────────────────────
  const dismiss = useCallback(async (recId) => {
    try {
      await recommendationAPI.dismiss(recId)
      setRecommendations(prev => prev.filter(r => r.id !== recId))
      toast.success('Recommendation dismissed.')
    } catch {
      toast.error('Failed to dismiss.')
    }
  }, [])

  return {
    recommendations, agentLog, thoughtSteps,
    loading, generating,
    fetchRecommendations, fetchAgentLog, runAgent,
    logInteraction, dismiss,
  }
}