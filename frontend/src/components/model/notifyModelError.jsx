import toast from 'react-hot-toast'

export const OPEN_MODEL_EVENT = 'pet:open-model'

export function openModelWindow() {
  window.dispatchEvent(new CustomEvent(OPEN_MODEL_EVENT))
}

// One toast at a time: a failing key tends to fail several calls at once.
export function notifyModelError({ detail, provider_message: said }) {
  toast.error(t => (
    <div className="flex flex-col gap-2">
      <p>{detail}</p>
      {said && <p className="font-mono text-[11px] opacity-70">{said}</p>}
      <button
        type="button"
        onClick={() => { toast.dismiss(t.id); openModelWindow() }}
        className="self-start rounded-md bg-ink px-3 py-1.5 text-xs font-semibold text-canvas"
      >
        Open Model window
      </button>
    </div>
  ), { id: 'model-error', duration: 12000 })
}
