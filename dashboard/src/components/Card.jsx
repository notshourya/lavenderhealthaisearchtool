const VARIANT_CLASSES = {
  default:  'bg-surface shadow-card hover:shadow-card-hover',
  lavender: 'bg-card-lavender',
  blue:     'bg-card-blue',
  orange:   'bg-card-orange',
  green:    'bg-card-green',
}

export default function Card({ children, className = '', variant = 'default', onClick }) {
  return (
    <div
      onClick={onClick}
      className={`rounded-card p-6 transition-shadow duration-200 ${VARIANT_CLASSES[variant]} ${onClick ? 'cursor-pointer' : ''} ${className}`}
    >
      {children}
    </div>
  )
}
