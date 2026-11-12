function Skeleton({ className = '', style = {} }) {
  return (
    <div
      className={`animate-pulse rounded-xl bg-white/[0.06] ${className}`}
      style={style}
    />
  )
}

export function SkeletonTile({ className = '', lines = 3 }) {
  return (
    <div className={`tile space-y-4 p-6 ${className}`} aria-hidden="true">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-6 w-2/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className="h-3" style={{ width: `${88 - i * 14}%` }} />
      ))}
    </div>
  )
}

export default Skeleton
