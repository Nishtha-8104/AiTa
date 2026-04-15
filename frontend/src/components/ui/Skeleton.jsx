/**
 * Skeleton loading components — drop-in replacements while data loads.
 */

function Skeleton({ className = '', style = {} }) {
  return (
    <div
      className={`animate-pulse rounded-xl bg-white/[0.06] ${className}`}
      style={style}
    />
  )
}

export function SkeletonCard({ lines = 3 }) {
  return (
    <div className="glass-card p-6 space-y-3">
      <Skeleton className="h-5 w-2/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className="h-3" style={{ width: `${90 - i * 15}%` }} />
      ))}
    </div>
  )
}

export function SkeletonStatCard() {
  return (
    <div className="glass-card p-5 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="w-9 h-9 rounded-xl" />
        <Skeleton className="h-3 w-24" />
      </div>
      <Skeleton className="h-7 w-16" />
      <Skeleton className="h-2 w-32" />
    </div>
  )
}

export function SkeletonMessage() {
  return (
    <div className="flex items-start gap-3">
      <Skeleton className="w-8 h-8 rounded-full shrink-0" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    </div>
  )
}

export function SkeletonRecommendationCard() {
  return (
    <div className="glass-card overflow-hidden">
      <div className="flex items-start">
        <Skeleton className="w-36 shrink-0" style={{ minHeight: 100 }} />
        <div className="flex-1 p-4 space-y-3">
          <div className="flex gap-2">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
          <div className="flex gap-2 pt-1">
            <Skeleton className="h-7 w-20 rounded-lg" />
            <Skeleton className="h-7 w-16 rounded-lg" />
          </div>
        </div>
      </div>
    </div>
  )
}

export default Skeleton
