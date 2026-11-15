import { useState, useEffect } from 'react'

export interface ToastMessage {
  id: string
  type: 'success' | 'warning' | 'error' | 'info'
  title: string
  message: string
  duration?: number
}

// 全局 Toast 事件发布订阅
type ToastListener = (toast: ToastMessage) => void
const listeners = new Set<ToastListener>()

export function showToast(toast: Omit<ToastMessage, 'id'>) {
  const item: ToastMessage = {
    ...toast,
    id: `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
  }
  listeners.forEach((fn) => fn(item))
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  useEffect(() => {
    const handler: ToastListener = (toast) => {
      setToasts((prev) => [...prev, toast])
      const duration = toast.duration ?? 4000
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== toast.id))
      }, duration)
    }

    listeners.add(handler)
    return () => {
      listeners.delete(handler)
    }
  }, [])

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-md w-full pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`pointer-events-auto rounded-lg p-3.5 border backdrop-blur-md flex items-start gap-3 transition-all transform translate-y-0 ${
            t.type === 'success'
              ? 'bg-[#102a1e]/90 border-[#176249] text-[#e8f8f0]'
              : t.type === 'error'
              ? 'bg-[#331114]/90 border-rose-500 text-[#fce8e8]'
              : t.type === 'warning'
              ? 'bg-[#2d2208]/90 border-amber-500 text-[#fdf6e6]'
              : 'bg-[#141d30]/90 border-slate-600 text-[#e8eef8]'
          }`}
        >
          <div className="text-lg leading-none mt-0.5">
            {t.type === 'success' && '✓'}
            {t.type === 'error' && '✕'}
            {t.type === 'warning' && '⚠'}
            {t.type === 'info' && 'ℹ'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-sm">{t.title}</div>
            <div className="text-xs opacity-90 mt-0.5 leading-relaxed break-words">{t.message}</div>
          </div>
          <button
            onClick={() => setToasts((prev) => prev.filter((item) => item.id !== t.id))}
            className="text-xs opacity-60 hover:opacity-100 p-1"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
