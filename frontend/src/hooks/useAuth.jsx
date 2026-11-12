import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authAPI, openSession } from '../utils/api'

const AuthContext = createContext(null)

// PET runs on the student's own computer: no sign-in, the session opens by itself.
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const start = localStorage.getItem('access_token') ? Promise.resolve() : openSession()
    start
      .then(() => authAPI.getMe())
      .then(({ data }) => setUser(data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const updateUser = useCallback((updatedUser) => {
    setUser((prev) => ({ ...prev, ...updatedUser }))
  }, [])

  const refreshUser = useCallback(async () => {
    const { data } = await authAPI.getMe()
    setUser(data)
    return data
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, updateUser, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
