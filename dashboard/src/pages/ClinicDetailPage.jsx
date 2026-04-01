import { useParams, useNavigate } from 'react-router-dom'
import { useClinicReviews } from '../api/clinics'
import Card from '../components/Card'
import Button from '../components/Button'

function highlightInsuranceText(text) {
  // Wrap insurance-related terms in a highlight span
  const terms = [
    'insurance claim', 'insurance denied', 'claim rejected', 'reimbursement',
    'out of pocket', 'overcharged', 'billed incorrectly', 'double charged',
    'billing issue', 'never paid',
  ]
  let result = text
  terms.forEach(term => {
    const regex = new RegExp(`(${term})`, 'gi')
    result = result.replace(regex, '<mark class="flag-highlight">$1</mark>')
  })
  return result
}

export default function ClinicDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: reviews = [], isLoading } = useClinicReviews(id)

  const flaggedReviews = reviews.filter(r => r.insurance_flag)
  const otherReviews = reviews.filter(r => !r.insurance_flag)

  return (
    <div>
      <div className="mb-6">
        <Button variant="ghost" size="sm" onClick={() => navigate('/clinics')}>← Back to Clinics</Button>
      </div>

      <h1 className="text-2xl font-bold text-ink mb-1">Clinic Reviews</h1>
      <p className="text-muted text-sm mb-6">
        {flaggedReviews.length} flagged · {otherReviews.length} other
      </p>

      {isLoading ? (
        <div className="text-muted text-sm">Loading…</div>
      ) : (
        <div className="flex flex-col gap-4">
          {flaggedReviews.length > 0 && (
            <>
              <div className="text-xs font-semibold text-accent uppercase tracking-widest mb-1">
                🚩 Flagged Reviews
              </div>
              {flaggedReviews.map(review => (
                <Card key={review.id} className="border-l-4 border-accent">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-semibold text-sm text-ink">{review.author || 'Anonymous'}</span>
                    <span className="text-yellow-500 text-xs">{'★'.repeat(review.rating || 0)}{'☆'.repeat(5 - (review.rating || 0))}</span>
                    {review.flag_reason && (
                      <span className="text-xs bg-accent/10 text-accent px-2 py-0.5 rounded-full">
                        {review.flag_reason}
                      </span>
                    )}
                  </div>
                  <p
                    className="text-sm text-ink leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: highlightInsuranceText(review.text) }}
                  />
                  {review.llm_reasoning && (
                    <p className="text-xs text-muted mt-2 italic">AI: {review.llm_reasoning}</p>
                  )}
                </Card>
              ))}
            </>
          )}

          {otherReviews.length > 0 && (
            <>
              <div className="text-xs font-semibold text-muted uppercase tracking-widest mb-1 mt-4">Other Reviews</div>
              {otherReviews.map(review => (
                <Card key={review.id}>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-semibold text-sm text-ink">{review.author || 'Anonymous'}</span>
                    <span className="text-yellow-500 text-xs">{'★'.repeat(review.rating || 0)}{'☆'.repeat(5 - (review.rating || 0))}</span>
                  </div>
                  <p className="text-sm text-muted leading-relaxed">{review.text}</p>
                </Card>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}
