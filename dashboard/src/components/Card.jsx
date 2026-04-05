const VARIANT_CLASSES = {
  default:  'bg-zinc-950/60 border-white/5',
  lavender: 'bg-indigo-950/20 border-indigo-500/10',
  blue:     'bg-blue-950/20 border-blue-500/10',
  orange:   'bg-orange-950/20 border-orange-500/10',
  green:    'bg-emerald-950/20 border-emerald-500/10',
}

export default function Card({ children, className = '', variant = 'default', onClick }) {
  return (
    <div
      onClick={onClick}
      className={`rounded-[32px] p-8 transition-all duration-300 backdrop-blur-2xl border shadow-2xl ${VARIANT_CLASSES[variant] || VARIANT_CLASSES.default} ${onClick ? 'cursor-pointer hover:shadow-[0_10px_40px_rgba(0,0,0,0.5)] hover:-translate-y-1 hover:border-white/10' : ''} ${className}`}
    >
      {children}
    </div>
  )
}