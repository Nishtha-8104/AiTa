// ============================================================
// CHANGES TO: frontend/src/App.jsx
// ADD: import RecommendationPage + add its Route
// ============================================================

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './hooks/useAuth'
import ProtectedRoute from './components/auth/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import ProfilePage from './pages/ProfilePage'
import RecommendationPage from './pages/RecommendationPage'    // ← NEW

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#1a2236',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.08)',
              fontFamily: '"DM Sans", sans-serif',
              fontSize: '14px',
              borderRadius: '12px',
            },
            success: { iconTheme: { primary: '#2e9aff', secondary: '#fff' } },
            error:   { iconTheme: { primary: '#f87171', secondary: '#fff' } },
          }}
        />
        <Routes>
          <Route path="/"               element={<Navigate to="/dashboard" replace />} />
          <Route path="/login"          element={<LoginPage />} />
          <Route path="/register"       element={<RegisterPage />} />
          <Route path="/dashboard"      element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/profile"        element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
          <Route path="/recommendations" element={<ProtectedRoute><RecommendationPage /></ProtectedRoute>} />   {/* ← NEW */}
          <Route path="*"              element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}