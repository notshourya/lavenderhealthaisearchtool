export default function Button({ children, onClick, variant = 'primary', disabled = false, size = 'md' }) {
  const base = 'font-semibold rounded-btn transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50 disabled:cursor-not-allowed'
  const sizes = { sm: 'px-3 py-1.5 text-sm', md: 'px-5 py-2.5 text-sm', lg: 'px-7 py-3 text-base' }
  const variants = {
    primary: 'bg-primary text-white hover:bg-[#3d52f0] shadow-sm hover:shadow-md',
    secondary: 'bg-subtle text-primary border border-primary/20 hover:bg-primary/10',
    danger: 'bg-accent text-white hover:bg-[#e0306e]',
    ghost: 'bg-transparent text-muted hover:bg-subtle',
  }
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${sizes[size]} ${variants[variant]}`}
    >
      {children}
    </button>
  )
}
