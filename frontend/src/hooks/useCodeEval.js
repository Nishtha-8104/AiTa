import { useState, useCallback } from 'react'
import { codeEvalAPI, getErrorMessage } from '../utils/api'
import toast from 'react-hot-toast'
import { toastAwards } from '../components/practice/shared'

function resultToast(data) {
  const score = `${(data.scores?.overall ?? 0).toFixed(1)}/100`
  if (data.verification_status === 'verified') {
    return `${data.tests_passed}/${data.tests_total} tests passed — ${score}`
  }
  if (data.compiled === false) return 'Your code did not compile — see the Tests tab'
  return `Evaluated, correctness not verified — ${score}`
}

export function useCodeEval() {
  const [submissions, setSubmissions]     = useState([])
  const [activeResult, setActiveResult]   = useState(null)   // latest EvaluationResult
  const [activeSubmission, setActiveSub]  = useState(null)   // full SubmissionDetail
  const [stats, setStats]                 = useState(null)
  const [evaluating, setEvaluating]       = useState(false)
  const [loading, setLoading]             = useState(false)
  const [error, setError]                 = useState(null)    // last failed evaluation

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

  // ── Fetch a submission's detail ───────────────────────────────────────────
  // The API no longer nests past evaluations, so this loads the code back into the
  // editor and leaves the result panel empty until the submission is re-evaluated.
  const openSubmission = useCallback(async (id) => {
    setLoading(true)
    try {
      const { data } = await codeEvalAPI.getSubmission(id)
      setActiveSub(data)
      setActiveResult(null)
    } catch {
      toast.error('Failed to load submission.')
    } finally {
      setLoading(false)
    }
  }, [])

  // ── Submit + evaluate in one shot ─────────────────────────────────────────
  const submitAndEvaluate = useCallback(async ({ language, code, title, problemContext, expectedOutput, problemId }) => {
    setEvaluating(true)
    setActiveResult(null)
    setActiveSub(null)
    setError(null)
    try {
      const { data } = await codeEvalAPI.submitAndEvaluate({
        language,
        code:            code.slice(0, 50000),
        title:           title                          || undefined,
        problem_context: problemContext?.slice(0, 5000) || undefined,
        expected_output: expectedOutput?.slice(0, 2000) || undefined,
        problem_id:      problemId                      || undefined,
      })
      setActiveResult(data)
      toast.success(resultToast(data))
      toastAwards(data)
      // Refresh submissions list
      const { data: subs } = await codeEvalAPI.getSubmissions()
      setSubmissions(subs)
      return data
    } catch (err) {
      // Kept in state as well as toasted: a toast disappears, and without this the
      // panel falls back to the empty state as though nothing had been attempted.
      const message = getErrorMessage(err, 'Evaluation failed. Is the executor running?')
      setError({ message, status: err?.response?.status ?? null })
      toast.error(message)
      return null
    } finally {
      setEvaluating(false)
    }
  }, [])

  // ── Re-evaluate an existing submission ────────────────────────────────────
  const reEvaluate = useCallback(async (submissionId) => {
    setEvaluating(true)
    setError(null)
    try {
      const { data } = await codeEvalAPI.evaluate(submissionId)
      setActiveResult(data)
      toast.success(resultToast(data))
      return data
    } catch (err) {
      const message = getErrorMessage(err, 'Re-evaluation failed.')
      setError({ message, status: err?.response?.status ?? null })
      toast.error(message)
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
    setError(null)
  }, [])

  return {
    submissions, activeResult, activeSubmission, stats,
    evaluating, loading, error,
    fetchSubmissions, openSubmission, submitAndEvaluate,
    reEvaluate, fetchStats, deleteSubmission, clearResult,
  }
}