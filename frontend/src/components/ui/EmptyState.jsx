export default function EmptyState({ icon: Icon, title, body, action, className = '' }) {
  return (
    <div className={`flex flex-col items-start gap-4 rounded-[20px] border border-dashed border-line-strong p-6 sm:p-8 ${className}`}>
      {Icon && (
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-tile-3 text-ink-muted">
          <Icon size={20} />
        </span>
      )}
      <div>
        <p className="text-[15px] font-semibold tracking-tight text-ink">{title}</p>
        {body && <p className="mt-1 max-w-[56ch] text-sm leading-relaxed text-ink-subtle">{body}</p>}
      </div>
      {action}
    </div>
  )
}
