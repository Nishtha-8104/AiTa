import { lazy, Suspense } from 'react'

const CodeMirrorEditor = lazy(() => import('./CodeMirrorEditor'))

function Fallback({ minHeight, height }) {
  return (
    <div className="animate-pulse bg-code-bg px-4 py-4" style={{ height: height || minHeight }} aria-hidden="true">
      <div className="space-y-2.5">
        {[62, 44, 78, 30, 55].map(w => <div key={w} className="h-3 rounded bg-white/[0.05]" style={{ width: `${w}%` }} />)}
      </div>
    </div>
  )
}

export default function CodeEditor({ className = '', readOnly = false, ...props }) {
  return (
    <div className={`overflow-hidden rounded-2xl border border-line bg-code-bg transition-colors focus-within:border-brand-400/60 ${readOnly ? 'opacity-90' : ''} ${className}`}>
      <Suspense fallback={<Fallback minHeight={props.minHeight || '240px'} height={props.height} />}>
        <CodeMirrorEditor readOnly={readOnly} {...props} />
      </Suspense>
    </div>
  )
}
