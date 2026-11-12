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
        <div className="flex min-h-[60dvh] items-center justify-center p-4">
          <div className="tile w-full max-w-md p-6">
            <p className="text-[15px] font-semibold text-ink">Something went wrong on this page.</p>
            <p className="mt-1 text-sm text-ink-subtle">Try again. If it keeps happening, reload the page.</p>
            <p className="mt-3 break-words font-mono text-xs text-ink-faint">{String(this.state.error?.message || '')}</p>
            <button
              type="button"
              onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-5 h-10 rounded-full bg-ink px-4 text-sm font-medium text-canvas hover:bg-white"
            >
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
