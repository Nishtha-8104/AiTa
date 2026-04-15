import { useState } from 'react'
import { X, Star, Send, CheckCircle2 } from 'lucide-react'

/**
 * Non-intrusive slide-up feedback modal.
 * Usage:
 *   <FeedbackModal
 *     open={showFeedback}
 *     onClose={() => setShowFeedback(false)}
 *     onSubmit={({ rating, comment }) => { ... }}
 *     context="Code Evaluation"   // optional label
 *   />
 */
export default function FeedbackModal({ open, onClose, onSubmit, context = 'Session' }) {
  const [rating, setRating]   = useState(0)
  const [hovered, setHovered] = useState(0)
  const [comment, setComment] = useState('')
  const [done, setDone]       = useState(false)
  const [saving, setSaving]   = useState(false)

  if (!open) return null

  const handleSubmit = async () => {
    if (rating === 0) return
    setSaving(true)
    try {
      await onSubmit?.({ rating, comment: comment.trim() })
      setDone(true)
      setTimeout(() => {
        onClose()
        setDone(false)
        setRating(0)
        setComment('')
      }, 1800)
    } finally {
      setSaving(false)
    }
  }

  const LABELS = ['', 'Poor', 'Fair', 'Good', 'Great', 'Excellent']

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
          backdropFilter: 'blur(4px)', zIndex: 100,
          animation: 'fadeIn 0.2s ease',
        }}
      />

      {/* Slide-up panel */}
      <div style={{
        position: 'fixed', bottom: 0, left: '50%', transform: 'translateX(-50%)',
        width: '100%', maxWidth: 480, zIndex: 101,
        background: '#111827', borderRadius: '20px 20px 0 0',
        border: '1px solid rgba(255,255,255,0.1)', borderBottom: 'none',
        padding: '28px 28px 36px',
        animation: 'slideUp 0.3s cubic-bezier(0.34,1.56,0.64,1)',
        fontFamily: "'DM Sans','Segoe UI',sans-serif",
      }}>
        {/* Handle */}
        <div style={{
          width: 40, height: 4, borderRadius: 2,
          background: 'rgba(255,255,255,0.15)',
          margin: '-12px auto 20px',
        }} />

        {done ? (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <CheckCircle2 size={40} color="#10b981" style={{ margin: '0 auto 12px' }} />
            <p style={{ color: '#fff', fontSize: 16, fontWeight: 700, margin: '0 0 6px' }}>
              Thanks for your feedback!
            </p>
            <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13 }}>
              It helps us improve your learning experience.
            </p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <div>
                <p style={{ color: '#fff', fontSize: 16, fontWeight: 700, margin: 0 }}>
                  How was this {context}?
                </p>
                <p style={{ color: 'rgba(255,255,255,0.35)', fontSize: 12, margin: '3px 0 0' }}>
                  Optional — takes 10 seconds
                </p>
              </div>
              <button
                onClick={onClose}
                style={{
                  background: 'rgba(255,255,255,0.06)', border: 'none',
                  borderRadius: 8, padding: 8, cursor: 'pointer', color: 'rgba(255,255,255,0.4)',
                  display: 'flex', alignItems: 'center',
                }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Stars */}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 8 }}>
              {[1, 2, 3, 4, 5].map(n => (
                <button
                  key={n}
                  onMouseEnter={() => setHovered(n)}
                  onMouseLeave={() => setHovered(0)}
                  onClick={() => setRating(n)}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer', padding: 4,
                    transition: 'transform 0.15s',
                    transform: hovered >= n || rating >= n ? 'scale(1.2)' : 'scale(1)',
                  }}
                >
                  <Star
                    size={32}
                    fill={hovered >= n || rating >= n ? '#f59e0b' : 'transparent'}
                    color={hovered >= n || rating >= n ? '#f59e0b' : 'rgba(255,255,255,0.2)'}
                  />
                </button>
              ))}
            </div>

            {/* Rating label */}
            <p style={{
              textAlign: 'center', fontSize: 13, fontWeight: 600, marginBottom: 20,
              color: rating > 0 ? '#f59e0b' : 'rgba(255,255,255,0.2)',
              minHeight: 20,
            }}>
              {LABELS[hovered || rating]}
            </p>

            {/* Comment */}
            <textarea
              placeholder="Any comments? (optional)"
              value={comment}
              onChange={e => setComment(e.target.value)}
              rows={3}
              style={{
                width: '100%', background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12,
                padding: '12px 14px', color: '#fff', fontSize: 13,
                resize: 'none', outline: 'none', boxSizing: 'border-box',
                fontFamily: 'inherit', lineHeight: 1.5,
                marginBottom: 16,
              }}
            />

            {/* Actions */}
            <div style={{ display: 'flex', gap: 10 }}>
              <button
                onClick={onClose}
                style={{
                  flex: 1, background: 'transparent',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 10, padding: '11px', color: 'rgba(255,255,255,0.4)',
                  fontSize: 13, cursor: 'pointer',
                }}
              >
                Skip
              </button>
              <button
                onClick={handleSubmit}
                disabled={rating === 0 || saving}
                style={{
                  flex: 2, background: rating > 0 ? 'linear-gradient(135deg,#14b8a6,#0891b2)' : 'rgba(255,255,255,0.06)',
                  border: 'none', borderRadius: 10, padding: '11px',
                  color: rating > 0 ? '#000' : 'rgba(255,255,255,0.2)',
                  fontSize: 13, fontWeight: 700, cursor: rating > 0 ? 'pointer' : 'not-allowed',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  transition: 'all 0.2s',
                }}
              >
                <Send size={14} />
                {saving ? 'Submitting...' : 'Submit Feedback'}
              </button>
            </div>
          </>
        )}
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity: 0 } to { opacity: 1 } }
        @keyframes slideUp { from { transform: translateX(-50%) translateY(100%) } to { transform: translateX(-50%) translateY(0) } }
      `}</style>
    </>
  )
}
