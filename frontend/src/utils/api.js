import axios from 'axios'
import { notifyModelError } from '../components/model/notifyModelError'

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

export const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,
  withCredentials: true,   // the model-choice cookie
})

// An evaluation compiles code, runs it in the sandbox and calls an LLM, which
// routinely passes 60s. Aborting the request does not stop the backend, so the
// work completes while the UI reports "Network Error" and resets itself.
const EVAL_TIMEOUT = 300000

// PET runs locally for one student, so an expired token is replaced by a new session.
// Must go through API_BASE: a relative path posts to the frontend's own origin.
export async function openSession() {
  const { data } = await axios.post(`${API_BASE}/auth/session`)
  localStorage.setItem('access_token', data.access_token)
  return data.access_token
}

// ─── Request Interceptor: attach token ───────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error)
)

// ─── Response Interceptor: new session on 401 ────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 424 && error.response.data?.code && !originalRequest?.inlineModelError) {
      notifyModelError(error.response.data)
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const token = await openSession()
        originalRequest.headers.Authorization = `Bearer ${token}`
        return api(originalRequest)
      } catch { /* the backend is down; the caller shows the error */ }
    }
    return Promise.reject(error)
  }
)

// ─── Auth API ─────────────────────────────────────────────────────────────────
export const authAPI = {
  getMe: () => api.get('/auth/me'),
}

// ─── User Profile API ─────────────────────────────────────────────────────────
export const userAPI = {
  getProfile: () => api.get('/users/profile'),
  updateProfile: (data) => api.patch('/users/profile', data),
  updateConsent: (consent) => api.patch(`/users/consent?consent=${consent}`),
  getPeerComparison: () => api.get('/users/peer-comparison'),
}

export const problemsAPI = {
  generate: (data) => api.post('/problems/generate', data),
  solution: (id, data) => api.post(`/problems/${id}/solution`, data, { timeout: EVAL_TIMEOUT }),
};

// ─── Code Evaluation Agent API ────────────────────────────────────────────────
export const codeEvalAPI = {
  // Submit code (no eval yet)
  submit:           (data) => api.post('/code-eval/submit', data),
  // Evaluate an existing submission
  evaluate:         (id)   => api.post(`/code-eval/submit/${id}/evaluate`, null, { timeout: EVAL_TIMEOUT }),
  // Submit + evaluate in one call  ← main action
  submitAndEvaluate:(data) => api.post('/code-eval/evaluate', data, { timeout: EVAL_TIMEOUT }),
  // Run against the shown example only — not scored, not saved
  run:              (data) => api.post('/code-eval/run', data),
  // History
  getSubmissions:   ()     => api.get('/code-eval/submissions'),
  getSubmission:    (id)   => api.get(`/code-eval/submissions/${id}`),
  deleteSubmission: (id)   => api.delete(`/code-eval/submissions/${id}`),
  // Stats & progress
  getStats:         ()     => api.get('/code-eval/stats'),
  // Problem bank
  getProblems:      ()     => api.get('/code-eval/problems'),
  getProblem:       (id)   => api.get(`/code-eval/problems/${id}`),
}

// A report waits on the model; the backend falls back to a pattern-only report when it is
// slow, and that fallback can land after the default 60s.
const FEEDBACK_TIMEOUT = 120000

export const feedbackAPI = {
  autoGenerate: ()       => api.post('/feedback/auto-generate', null, { timeout: FEEDBACK_TIMEOUT }),
  generate:    (data)    => api.post('/feedback/generate', data, { timeout: FEEDBACK_TIMEOUT }),
  getAll:      ()        => api.get('/feedback/'),
  unreadCount: ()        => api.get('/feedback/unread-count'),
  getReport:   (id)      => api.get(`/feedback/${id}`),
  markRead:    (id)      => api.patch(`/feedback/${id}/read`),
  // Next rung of the hint ladder for a problem the student is failing
  hint:        (problemId) => api.post('/feedback/hint', { problem_id: problemId }, { timeout: EVAL_TIMEOUT }),
}

export const profileAPI = {
  getMastery: () => api.get('/profile/mastery'),
}

const signedOut = (res) => res.status === 401

// The reply is a Server-Sent Events stream over POST, which axios cannot read
// incrementally, so this one call uses fetch with the same token handling.
async function postStream(path, body, signal) {
  const send = () => {
    const token = localStorage.getItem('access_token')
    return fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
      credentials: 'include',
    })
  }
  const res = await send()
  if (!signedOut(res)) return res
  try {
    await openSession()
  } catch {
    return res
  }
  return send()
}

export const chatAPI = {
  listThreads:  ()                       => api.get('/chat/threads'),
  getThread:    (id)                     => api.get(`/chat/threads/${id}`),
  createThread: (mode)                   => api.post('/chat/threads', mode ? { mode } : {}),
  thumbs:       (messageId, value)       => api.patch(`/chat/messages/${messageId}/thumbs`, { value }),
  send:         (threadId, body, signal) => postStream(`/chat/threads/${threadId}/messages`, body, signal),
}

export const assessmentAPI = {
  // May generate a coding problem when the bank has none left, which calls the LLM
  next:        ()               => api.get('/assessment/next', { timeout: EVAL_TIMEOUT }),
  answerMcq:   (id, chosenIndex) => api.post(`/assessment/mcq/${id}/answer`, { chosen_index: chosenIndex }),
  submitDebug: (id, code)       => api.post(`/assessment/debug/${id}/submit`, { code }, { timeout: EVAL_TIMEOUT }),
}

export const gamificationAPI = {
  me: () => api.get('/gamification/me'),
}

export const practiceSessionAPI = {
  current:  ()          => api.get('/practice-sessions/current'),
  pending:  ()          => api.get('/practice-sessions/pending'),
  get:      (id)        => api.get(`/practice-sessions/${id}`),
  finish:   (id)        => api.post(`/practice-sessions/${id}/finish`),
  // Writes the short feedback with the LLM the first time
  feedback: (id, retry) => api.post(`/practice-sessions/${id}/feedback`, { retry }, { timeout: EVAL_TIMEOUT }),
}

// The key goes to the server only to be checked and sealed into an HttpOnly cookie.
export const modelAPI = {
  get:    ()     => api.get('/model-settings'),
  test:   (body) => api.post('/model-settings/test', body, { timeout: EVAL_TIMEOUT, inlineModelError: true }),
  save:   (body) => api.put('/model-settings', body, { timeout: EVAL_TIMEOUT, inlineModelError: true }),
  remove: ()     => api.delete('/model-settings'),
}

export const topicPracticeAPI = {
  explanation:  (topic)      => api.get(`/topic-practice/${topic}/explanation`),
  start:        (topic)      => api.post(`/topic-practice/${topic}/start`),
  // Can write a fresh coding problem when none of the saved ones fits
  next:         ()           => api.get('/topic-practice/next', { timeout: EVAL_TIMEOUT }),
  answerTheory: (id, answer) => api.post(`/topic-practice/theory/${id}/answer`, { answer }, { timeout: EVAL_TIMEOUT }),
}

export const onboardingAPI = {
  state:       ()                          => api.get('/onboarding/state'),
  saveStep:    (step, data)                => api.put(`/onboarding/steps/${step}`, data),
  next:        ()                          => api.post('/onboarding/diagnostic/next'),
  // Code answers run in the sandbox and theory answers may call the LLM
  answer:      (itemId, answer, msTaken)   => api.post('/onboarding/diagnostic/answer',
    { item_id: itemId, answer, ms_taken: msTaken }, { timeout: EVAL_TIMEOUT }),
  finish:      ()                          => api.post('/onboarding/finish', null, { timeout: EVAL_TIMEOUT }),
  editProfile: (data)                      => api.patch('/onboarding/profile', data),
  switchLanguage: (language)               => api.post('/onboarding/language', { language }),
}

// The short code-only check taken on switching to a language never used before
export const recheckAPI = {
  next:   ()                        => api.post('/onboarding/recheck/next'),
  answer: (itemId, answer, msTaken) => api.post('/onboarding/recheck/answer',
    { item_id: itemId, answer, ms_taken: msTaken }, { timeout: EVAL_TIMEOUT }),
  finish: ()                        => api.post('/onboarding/recheck/finish'),
}

export default api