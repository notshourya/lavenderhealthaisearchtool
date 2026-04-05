export default function Button({ children, onClick, variant = 'primary', disabled = false, size = 'md', type = 'button', className = '' }) {
  const base = 'inline-flex items-center justify-center gap-3 font-semibold rounded-full transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-white/20 disabled:opacity-50 disabled:cursor-not-allowed transform active:scale-[0.98] tracking-wide'

  const sizes = {
    sm: 'px-5 py-2.5 text-xs',
    md: 'px-6 py-3.5 text-sm',
    lg: 'px-8 py-4 text-base',
  }

  const variants = {
    primary:   'bg-white text-black border border-transparent hover:bg-zinc-200 hover:shadow-[0_0_20px_rgba(255,255,255,0.3)]',
    secondary: 'bg-zinc-900/80 backdrop-blur-2xl text-white border border-white/10 hover:bg-zinc-800 hover:border-white/20 shadow-xl',
    danger:    'bg-red-500/10 text-red-500 border border-red-500/20 hover:bg-red-500/20 hover:border-red-500/40',
    ghost:     'bg-transparent text-zinc-400 hover:text-white hover:bg-white/5 border border-transparent',
  }

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  )
}