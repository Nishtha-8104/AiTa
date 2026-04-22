import axios from 'axios'

// ─── Helper: safely extract a string from any API error ──────────────────────
export function getErrorMessage(err, fallback = 'Something went wrong.') {
  const detail = err?.response?.data?.detail
  if (!detail) return err?.message || fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map(e => (typeof e === 'object' ? (e.msg || JSON.stringify(e)) : String(e))).join(', ')
  }
  if (typeof detail === 'object') return detail.msg || JSON.stringify(detail)
  return String(detail)
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,   // 60s — gives Render free tier time to wake up
})

// ─── Request Interceptor: attach token ───────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error)
)

// ─── Response Interceptor: auto-refresh on 401 ───────────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const refreshToken = localStorage.getItem('refresh_token')

      if (refreshToken) {
        try {
          const { data } = await axios.post('/api/v1/auth/refresh', {
            refresh_token: refreshToken,
          })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`
          return api(originalRequest)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

// ─── Auth API ─────────────────────────────────────────────────────────────────
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  verifyOtp: (data) => api.post('/auth/verify-otp', data),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  resetPassword: (data) => api.post('/auth/reset-password', data),
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  refresh: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken }),
}

// ─── User Profile API ─────────────────────────────────────────────────────────
export const userAPI = {
  getProfile: () => api.get('/users/profile'),
  updateProfile: (data) => api.patch('/users/profile', data),
  changePassword: (data) => api.post('/users/change-password', data),
  updateConsent: (consent) => api.patch(`/users/consent?consent=${consent}`),
  getPeerComparison: () => api.get('/users/peer-comparison'),
}

export const recommendationAPI = {
  // Trigger the AI agent — long timeout since it fetches YouTube + calls Groq
  generate: () => api.post('/recommendations/generate', {}, { timeout: 120000 }),
  // Get current stored recommendations
  getAll: () => api.get('/recommendations/'),
  // Get last agent run log with thought steps
  getAgentLog: () => api.get('/recommendations/agent-log'),
  // Log an interaction (view, complete, like, etc.)
  logInteraction: (data) => api.post('/recommendations/interact', data),
  // Dismiss a recommendation
  dismiss: (recId) => api.patch(`/recommendations/${recId}/dismiss`),
  // Browse content catalog
  listContent: (skip = 0, limit = 50) => api.get(`/recommendations/content?skip=${skip}&limit=${limit}`),
  // Seed starter content (call once)
  seedContent: () => api.post('/recommendations/content/seed'),
}

// export const contentPlayerAPI = {
//   // Session management
//   createSession:  (data)      => api.post('/content-player/sessions', data),
//   getSessions:    ()          => api.get('/content-player/sessions'),
//   getSession:     (id)        => api.get(`/content-player/sessions/${id}`),
//   archiveSession: (id)        => api.delete(`/content-player/sessions/${id}`),

//   // Chat — the main action
//   chat:           (id, data)  => api.post(`/content-player/sessions/${id}/chat`, data),

//   // Message feedback
//   rateMessage:    (msgId, wasHelpful) =>
//     api.patch(`/content-player/messages/${msgId}/feedback`, { was_helpful: wasHelpful }),
// }

export const contentPlayerAPI = {
  createSession:  (data)             => api.post('/content-player/sessions', data),
  getSessions:    ()                 => api.get('/content-player/sessions'),
  getSession:     (id)               => api.get(`/content-player/sessions/${id}`),
  archiveSession: (id)               => api.delete(`/content-player/sessions/${id}`),
  chat:           (sessionId, data)  => api.post(`/content-player/sessions/${sessionId}/chat`, data),
  rateMessage:    (msgId, helpful)   => api.patch(`/content-player/messages/${msgId}/feedback`, { was_helpful: helpful }),
  generateProblem:(data)             => api.post('/content-player/generate-problem', data),
};

// ─── Code Evaluation Agent API ────────────────────────────────────────────────
export const codeEvalAPI = {
  // Submit code (no eval yet)
  submit:           (data) => api.post('/code-eval/submit', data),
  // Evaluate an existing submission
  evaluate:         (id)   => api.post(`/code-eval/submit/${id}/evaluate`),
  // Submit + evaluate in one call  ← main action
  submitAndEvaluate:(data) => api.post('/code-eval/evaluate', data),
  // History
  getSubmissions:   ()     => api.get('/code-eval/submissions'),
  getSubmission:    (id)   => api.get(`/code-eval/submissions/${id}`),
  deleteSubmission: (id)   => api.delete(`/code-eval/submissions/${id}`),
  // Stats & progress
  getStats:         ()     => api.get('/code-eval/stats'),
}

export const feedbackAPI = {
  autoGenerate: ()       => api.post('/feedback/auto-generate'),
  generate:    (data)    => api.post('/feedback/generate', data),
  getAll:      ()        => api.get('/feedback/'),
  unreadCount: ()        => api.get('/feedback/unread-count'),
  getReport:   (id)      => api.get(`/feedback/${id}`),
  markRead:    (id)      => api.patch(`/feedback/${id}/read`),
}

export default api