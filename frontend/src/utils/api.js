import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
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
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  refresh: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken }),
}

// ─── User Profile API ─────────────────────────────────────────────────────────
export const userAPI = {
  getProfile: () => api.get('/users/profile'),
  updateProfile: (data) => api.patch('/users/profile', data),
  changePassword: (data) => api.post('/users/change-password', data),
}

export const recommendationAPI = {
  // Trigger the AI agent (CF + CBF + Claude reasoning)
  generate: () => api.post('/recommendations/generate'),
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

export default api