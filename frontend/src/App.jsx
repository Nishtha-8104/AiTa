import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './hooks/useAuth'
import { ThemeProvider } from './hooks/useTheme'
import ProtectedRoute from './components/auth/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import OnboardingPage from './pages/OnboardingPage'
import DashboardPage from './pages/DashboardPage'
import ProfilePage from './pages/ProfilePage'
import RecommendationPage from './pages/RecommendationPage'
import ContentPlayerPage from './pages/ContentPlayerPage'
import CodeEvalPage from './pages/CodeEvalPage'
import FeedbackPage from './pages/FeedbackPage'
import CodeHelpPage from './pages/CodeHelpPage'

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
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
            <Route path="/"                element={<Navigate to="/dashboard" replace />} />
            <Route path="/login"           element={<LoginPage />} />
            <Route path="/register"        element={<RegisterPage />} />
            <Route path="/onboarding"      element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
            <Route path="/dashboard"       element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/profile"         element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
            <Route path="/recommendations" element={<ProtectedRoute><RecommendationPage /></ProtectedRoute>} />
            <Route path="/learn"           element={<ProtectedRoute><ContentPlayerPage /></ProtectedRoute>} />
            <Route path="/code-eval"       element={<ProtectedRoute><CodeEvalPage /></ProtectedRoute>} />
            <Route path="/feedback"        element={<ProtectedRoute><FeedbackPage /></ProtectedRoute>} />
            <Route path="/code-help"       element={<ProtectedRoute><CodeHelpPage /></ProtectedRoute>} />
            <Route path="*"               element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}