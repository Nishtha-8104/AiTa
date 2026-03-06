import { useState, useCallback } from 'react'
import { recommendationAPI } from '../utils/api'
import toast from 'react-hot-toast'

export function useRecommendations() {
  const [recommendations, setRecommendations] = useState([])
  const [agentLog, setAgentLog]               = useState(null)
  const [thoughtSteps, setThoughtSteps]       = useState([])
  const [loading, setLoading]                 = useState(false)
  const [generating, setGenerating]           = useState(false)
  const [seeding, setSeeding]                 = useState(false)

  // ─── Fetch stored recommendations ──────────────────────────────────────
  const fetchRecommendations = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await recommendationAPI.getAll()
      setRecommendations(data)
    } catch (err) {
      if (err.response?.status !== 404) {
        toast.error('Failed to load recommendations.')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  // ─── Fetch agent run log ────────────────────────────────────────────────
  const fetchAgentLog = useCallback(async () => {
    try {
      const { data } = await recommendationAPI.getAgentLog()
      setAgentLog(data)
      setThoughtSteps(data.step_log || [])
    } catch {
      // No log yet — that's fine
    }
  }, [])

  // ─── Seed content catalog ───────────────────────────────────────────────
  const seedContent = useCallback(async () => {
    setSeeding(true)
    try {
      const { data } = await recommendationAPI.seedContent()
      toast.success(`${data.message}`)
    } catch {
      toast.error('Failed to seed content.')
    } finally {
      setSeeding(false)
    }
  }, [])

  // ─── Run the AI Agent ───────────────────────────────────────────────────
  const runAgent = useCallback(async () => {
    setGenerating(true)
    setThoughtSteps([])
    setRecommendations([])

    // Simulate progressive thought step display while waiting
    const progressSteps = [
      '🔍 Connecting to Content Recommendation Agent...',
      '👤 Extracting your learning profile...',
      '🤝 Running Collaborative Filtering across all learners...',
      '📚 Analyzing content topics vs your interests...',
      '⚙️  Merging scores + applying RL exploration bonus...',
      '🤖 Sending top candidates to Claude AI for reasoning...',
      '🧠 Claude is analyzing and re-ranking for you...',
      '💾 Persisting personalized recommendations...',
    ]

    let stepIdx = 0
    const interval = setInterval(() => {
      if (stepIdx < progressSteps.length) {
        setThoughtSteps(prev => [...prev, progressSteps[stepIdx]])
        stepIdx++
      }
    }, 800)

    try {
      const { data } = await recommendationAPI.generate()
      clearInterval(interval)

      // Replace progress steps with real agent steps
      setThoughtSteps(data.agent_thought_steps || progressSteps)

      // Fetch the actual recommendations
      const { data: recs } = await recommendationAPI.getAll()
      setRecommendations(recs)

      // Fetch log
      await fetchAgentLog()

      toast.success(`✅ Agent generated ${data.total} personalized recommendations!`)
    } catch (err) {
      clearInterval(interval)
      setThoughtSteps(prev => [...prev, `❌ Error: ${err.response?.data?.detail || err.message}`])
      toast.error('Agent run failed. Check your API key in .env')
    } finally {
      setGenerating(false)
    }
  }, [fetchAgentLog])

  // ─── Log interaction ────────────────────────────────────────────────────
  const logInteraction = useCallback(async (contentId, interaction, extra = {}) => {
    try {
      await recommendationAPI.logInteraction({ content_id: contentId, interaction, ...extra })
    } catch {
      // silent
    }
  }, [])

  // ─── Dismiss ────────────────────────────────────────────────────────────
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
    loading, generating, seeding,
    fetchRecommendations, fetchAgentLog, runAgent,
    logInteraction, dismiss, seedContent,
  }
}