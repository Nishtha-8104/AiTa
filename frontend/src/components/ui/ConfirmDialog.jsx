import { useEffect, useRef } from 'react'
import Button from './Button'

export default function ConfirmDialog({
  open, title, body, confirmLabel = 'Confirm', cancelLabel = 'Cancel', tone = 'primary', onConfirm, onCancel, onClose,
}) {
  const cancelRef = useRef(null)
  const dismissRef = useRef(null)
  dismissRef.current = onClose || onCancel

  useEffect(() => {
    if (!open) return
    const prev = document.activeElement
    cancelRef.current?.focus()
    const onKey = e => { if (e.key === 'Escape') dismissRef.current() }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      prev?.focus?.()
    }
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center" role="presentation">
      <button type="button" aria-label="Close" onClick={() => dismissRef.current()} className="absolute inset-0 bg-canvas/75 backdrop-blur-sm motion-safe:animate-fade-in" />
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-body"
        className="tile relative w-full max-w-md bg-tile-2 p-6 motion-safe:animate-rise"
      >
        <h2 id="confirm-title" className="text-lg font-semibold tracking-tight text-ink">{title}</h2>
        <div id="confirm-body" className="mt-2 text-sm leading-relaxed text-ink-subtle">{body}</div>
        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <Button ref={cancelRef} variant="secondary" onClick={onCancel}>{cancelLabel}</Button>
          <Button variant={tone} onClick={onConfirm}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  )
}
