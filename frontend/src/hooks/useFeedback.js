import { useState, useCallback } from 'react'
import { feedbackAPI } from '../utils/api'
import toast from 'react-hot-toast'

export function useFeedback() {
  const [reports,      setReports]      = useState([])
  const [activeReport, setActiveReport] = useState(null)
  const [generating,   setGenerating]   = useState(false)
  const [loading,      setLoading]      = useState(false)

  const fetchReports = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await feedbackAPI.getAll()
      setReports(data)
    } catch { /* no reports yet is valid */ }
    finally { setLoading(false) }
  }, [])

  const openReport = useCallback(async (id) => {
    try {
      const { data } = await feedbackAPI.getReport(id)
      setActiveReport(data)
      if (!data.is_read) {
        await feedbackAPI.markRead(id)
        setReports(prev => prev.map(r => r.id === id ? { ...r, is_read: true } : r))
      }
    } catch { toast.error('Failed to load report.') }
  }, [])

  // Auto-generate — no input needed
  const autoGenerate = useCallback(async () => {
    setGenerating(true)
    setActiveReport(null)
    try {
      const { data } = await feedbackAPI.autoGenerate()
      setActiveReport(data)
      setReports(prev => [data, ...prev])
      toast.success('Feedback report ready!')
      return data
    } catch (err) {
      const msg = err.response?.data?.detail || 'Generation failed.'
      toast.error(msg)
      return null
    } finally {
      setGenerating(false)
    }
  }, [])

  const clearActive = useCallback(() => setActiveReport(null), [])

  return {
    reports, activeReport, generating, loading,
    fetchReports, openReport, autoGenerate, clearActive,
  }
}
