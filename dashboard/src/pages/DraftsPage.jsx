import { useState } from 'react'
import { useDrafts, usePatchDraft, exportDraft } from '../api/drafts'
import Card from '../components/Card'
import Button from '../components/Button'
import StatusBadge from '../components/StatusBadge'

function DraftCard({ draft }) {
  const [editing, setEditing] = useState(false)
  const [subject, setSubject] = useState(draft.subject)
  const [body, setBody] = useState(draft.body)
  const [activeVariant, setActiveVariant] = useState(0)
  const patch = usePatchDraft()

  const save = () => {
    patch.mutate({ id: draft.id, subject, body }, { onSuccess: () => setEditing(false) })
  }

  const approve = () => {
    patch.mutate({ id: draft.id, status: 'approved' })
  }

  return (
    <Card className="border-l-4 border-primary/30">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 pr-4">
          {/* Subject line selector */}
          {draft.subject_variants?.length > 1 ? (
            <div className="flex gap-2 flex-wrap mb-2">
              {draft.subject_variants.map((v, i) => (
                <button
                  key={i}
                  onClick={() => { setActiveVariant(i); setSubject(v) }}
                  className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                    activeVariant === i
                      ? 'bg-primary text-white border-primary'
                      : 'border-gray-200 text-muted hover:border-primary'
                  }`}
                >
                  Option {i + 1}
                </button>
              ))}
            </div>
          ) : null}
          {editing ? (
            <input
              value={subject}
              onChange={e => setSubject(e.target.value)}
              className="w-full border border-gray-200 rounded-btn px-3 py-2 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary/30 mb-2"
            />
          ) : (
            <div className="font-semibold text-sm text-ink mb-1">{subject}</div>
          )}
        </div>
        <StatusBadge status={draft.status} />
      </div>

      {editing ? (
        <textarea
          value={body}
          onChange={e => setBody(e.target.value)}
          rows={8}
          className="w-full border border-gray-200 rounded-btn px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/30 mb-3"
        />
      ) : (
        <div
          className="text-sm text-ink leading-relaxed mb-3 prose prose-sm max-w-none"
          dangerouslySetInnerHTML={{ __html: body }}
        />
      )}

      <div className="flex gap-2 flex-wrap">
        {draft.status === 'draft' && (
          <Button size="sm" onClick={approve} disabled={patch.isPending}>
            ✓ Approve
          </Button>
        )}
        {editing ? (
          <>
            <Button size="sm" onClick={save} disabled={patch.isPending}>Save</Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
          </>
        ) : (
          <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>Edit</Button>
        )}
        <Button size="sm" variant="ghost" onClick={() => exportDraft(draft.id, 'pdf')}>
          ↓ PDF
        </Button>
        <Button size="sm" variant="ghost" onClick={() => exportDraft(draft.id, 'html')}>
          ↓ HTML
        </Button>
      </div>
    </Card>
  )
}

export default function DraftsPage() {
  const [statusFilter, setStatusFilter] = useState('draft')
  const { data: drafts = [], isLoading } = useDrafts(statusFilter || undefined)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-ink">Email Drafts</h1>
          <p className="text-muted text-sm mt-0.5">{drafts.length} drafts</p>
        </div>
        <div className="flex gap-2">
          {['draft', 'approved', ''].map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`text-sm px-3 py-1.5 rounded-btn font-semibold transition-colors ${
                statusFilter === s ? 'bg-primary text-white' : 'text-muted hover:bg-subtle'
              }`}
            >
              {s || 'All'}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="text-muted text-sm">Loading…</div>
      ) : drafts.length === 0 ? (
        <Card>
          <p className="text-muted text-center py-8">No drafts found.</p>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          {drafts.map(draft => <DraftCard key={draft.id} draft={draft} />)}
        </div>
      )}
    </div>
  )
}
