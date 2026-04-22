import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="glass-card p-4 border-red-500/20 text-center">
          <p className="text-red-400 text-sm font-display font-600 mb-1">Something went wrong rendering this section.</p>
          <p className="text-white/30 text-xs font-mono">{String(this.state.error?.message || '')}</p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="mt-3 px-3 py-1.5 bg-surface-700 hover:bg-surface-600 text-white/60 text-xs rounded-lg transition-colors"
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
