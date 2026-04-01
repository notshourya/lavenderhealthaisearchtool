export default function Card({ children, className = '' }) {
  return (
    <div className={`bg-surface rounded-card shadow-card p-6 ${className}`}>
      {children}
    </div>
  )
}
