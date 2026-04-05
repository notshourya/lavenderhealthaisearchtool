import { useEffect } from 'react'
import { createPortal } from 'react-dom'

const SIZE_CLASS = {
  sm: 'max-w-md',
  md: 'max-w-xl',
  lg: 'max-w-3xl',
  xl: 'max-w-6xl',
}

export default function Modal({ isOpen, onClose, title, children, size = 'sm' }) {
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  if (!isOpen || typeof document === 'undefined') return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-md" onClick={onClose} />
      <div className={`relative w-full ${SIZE_CLASS[size] || SIZE_CLASS.sm} rounded-[40px] border border-white/5 bg-zinc-950/80 backdrop-blur-3xl p-10 shadow-2xl z-10 max-h-[calc(100vh-2rem)] overflow-y-auto`}>
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-medium text-zinc-100">{title}</h2>
          <button onClick={onClose} className="h-10 w-10 rounded-full bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-zinc-100 transition-colors text-2xl flex items-center justify-center">&times;</button>
        </div>
        {children}
      </div>
    </div>,
    document.body
  )
}