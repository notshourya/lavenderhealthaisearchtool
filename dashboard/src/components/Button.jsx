export default function Button({ children, onClick, variant = 'primary', disabled = false, size = 'md', type = 'button' }) {
  const base = 'inline-flex items-center justify-center font-semibold rounded-btn transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50 disabled:cursor-not-allowed'

  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-5 py-2 text-sm',
    lg: 'px-7 py-3 text-base',
  }

  const variants = {
    primary:   'bg-primary text-white hover:bg-primary-hover shadow-sm',
    secondary: 'bg-surface text-ink border border-subtle hover:bg-subtle',
    danger:    'bg-danger text-white hover:opacity-90',
    ghost:     'bg-transparent text-muted hover:bg-subtle hover:text-ink',
  }

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${sizes[size]} ${variants[variant]}`}
    >
      {children}
    </button>
  )
}
