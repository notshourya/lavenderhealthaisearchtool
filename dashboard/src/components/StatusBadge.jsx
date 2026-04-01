const STATUS_STYLES = {
  pending:     'bg-gray-100 text-gray-600',
  running:     'bg-blue-100 text-blue-700 animate-pulse',
  completed:   'bg-green-100 text-green-700',
  failed:      'bg-red-100 text-red-600',
  scraped:     'bg-gray-100 text-gray-600',
  filtered_out:'bg-gray-200 text-gray-500',
  qualified:   'bg-yellow-100 text-yellow-700',
  enriched:    'bg-purple-100 text-purple-700',
  drafted:     'bg-green-100 text-green-700',
  draft:       'bg-yellow-100 text-yellow-700',
  approved:    'bg-green-100 text-green-700',
  sent:        'bg-blue-100 text-blue-700',
}

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${style}`}>
      {status?.replace(/_/g, ' ')}
    </span>
  )
}
