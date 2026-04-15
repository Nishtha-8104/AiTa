import { useState, useCallback } from 'react'
import { codeEvalAPI } from '../utils/api'
import toast from 'react-hot-toast'

export function useCodeEval() {
  const [submissions, setSubmissions]     = useState([])
  const [activeResult, setActiveResult]   = useState(null)   // latest EvaluationResult
  const [activeSubmission, setActiveSub]  = useState(null)   // full SubmissionDetail
  const [stats, setStats]                 = useState(null)
  const [evaluating, setEvaluating]       = useState(false)
  const [loading, setLoading]             = useState(false)

  // ── Fetch submission list ─────────────────────────────────────────────────
  const fetchSubmissions = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await codeEvalAPI.getSubmissions()
      setSubmissions(data)
    } catch {
      toast.error('Failed to load submissions.')
    } finally {
      setLoading(false)
    }
  }, [])

  // ── Fetch a submission's full detail (with all evaluations) ───────────────
  const openSubmission = useCallback(async (id) => {
    setLoading(true)
    try {
      const { data } = await codeEvalAPI.getSubmission(id)
      setActiveSub(data)
      if (data.evaluations?.length > 0) setActiveResult(data.evaluations[0])
    } catch {
      toast.error('Failed to load submission.')
    } finally {
      setLoading(false)
    }
  }, [])

  // ── Submit + evaluate in one shot ─────────────────────────────────────────
  const submitAndEvaluate = useCallback(async ({ language, code, title, problemContext, expectedOutput }) => {
    setEvaluating(true)
    setActiveResult(null)
    setActiveSub(null)
    try {
      const { data } = await codeEvalAPI.submitAndEvaluate({
        language,
        code,
        title:           title           || undefined,
        problem_context: problemContext  || undefined,
        expected_output: expectedOutput  || undefined,
      })
      setActiveResult(data)
      toast.success(`✅ Evaluation complete — Score: ${data.scores.overall.toFixed(1)}/100`)
      // Refresh submissions list
      const { data: subs } = await codeEvalAPI.getSubmissions()
      setSubmissions(subs)
      return data
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Evaluation failed. Check your Groq API key.')
      return null
    } finally {
      setEvaluating(false)
    }
  }, [])

  // ── Re-evaluate an existing submission ────────────────────────────────────
  const reEvaluate = useCallback(async (submissionId) => {
    setEvaluating(true)
    try {
      const { data } = await codeEvalAPI.evaluate(submissionId)
      setActiveResult(data)
      toast.success(`Re-evaluation complete — Score: ${data.scores.overall.toFixed(1)}/100`)
      return data
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Re-evaluation failed.')
      return null
    } finally {
      setEvaluating(false)
    }
  }, [])

  // ── Fetch stats ───────────────────────────────────────────────────────────
  const fetchStats = useCallback(async () => {
    try {
      const { data } = await codeEvalAPI.getStats()
      setStats(data)
    } catch {
      // Stats optional — silent fail
    }
  }, [])

  // ── Delete a submission ───────────────────────────────────────────────────
  const deleteSubmission = useCallback(async (id) => {
    try {
      await codeEvalAPI.deleteSubmission(id)
      setSubmissions(prev => prev.filter(s => s.id !== id))
      if (activeSubmission?.id === id) { setActiveSub(null); setActiveResult(null) }
      toast.success('Submission deleted.')
    } catch {
      toast.error('Failed to delete submission.')
    }
  }, [activeSubmission])

  const clearResult = useCallback(() => {
    setActiveResult(null)
    setActiveSub(null)
  }, [])

  return {
    submissions, activeResult, activeSubmission, stats,
    evaluating, loading,
    fetchSubmissions, openSubmission, submitAndEvaluate,
    reEvaluate, fetchStats, deleteSubmission, clearResult,
  }
}