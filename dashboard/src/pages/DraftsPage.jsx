import { useState } from 'react'
import { useDrafts, usePatchDraft, exportDraft } from '../api/drafts'
import Button from '../components/Button'
import StatusBadge from '../components/StatusBadge'

function DraftItem({ draft }) {
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
    <div className="bg-zinc-950/60 backdrop-blur-3xl border border-white/5 p-10 rounded-[40px] shadow-2xl mb-8 group transition-all duration-500 hover:shadow-[0_20px_60px_rgba(0,0,0,0.4)]">
      <div className="flex flex-col lg:flex-row items-start justify-between gap-8 mb-10">
        <div className="flex-1 min-w-0 w-full">
          {draft.subject_variants?.length > 1 ? (
            <div className="flex gap-3 flex-wrap mb-6 bg-black/40 p-2 rounded-full border border-white/5 inline-flex">
              {draft.subject_variants.map((v, i) => (
                <button
                  key={i}
                  onClick={() => { setActiveVariant(i); setSubject(v) }}
                  className={`text-xs px-5 py-2.5 rounded-full transition-all duration-300 font-bold ${
                    activeVariant === i
                      ? 'bg-white text-black shadow-lg'
                      : 'bg-transparent text-zinc-500 hover:bg-white/10 hover:text-white'
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
              className="w-full border border-white/20 rounded-2xl bg-black/50 px-6 py-5 text-2xl font-medium text-white focus:outline-none focus:ring-2 focus:ring-white/30 mb-6 backdrop-blur-xl shadow-inner transition-all"
            />
          ) : (
            <h3 className="font-medium text-4xl text-white mb-4 leading-tight tracking-tight">{subject}</h3>
          )}
          <div className="text-base text-zinc-500 font-medium">
            <span className="text-zinc-300">{draft.clinic_name || 'Clinic'}</span>
            <span className="mx-3 opacity-50">·</span>
            {draft.contact_email || 'No email yet'}
          </div>
        </div>
        <StatusBadge status={draft.status} />
      </div>

      {editing ? (
        <textarea
          value={body}
          onChange={e => setBody(e.target.value)}
          rows={14}
          className="w-full border border-white/20 rounded-[32px] bg-black/50 px-8 py-8 text-base font-mono text-zinc-300 focus:outline-none focus:ring-2 focus:ring-white/30 mb-10 leading-relaxed backdrop-blur-xl shadow-inner transition-all"
        />
      ) : (
        <div
          className="text-lg text-zinc-300 leading-relaxed mb-10 prose prose-invert prose-lg max-w-none bg-black/30 border border-white/5 rounded-[32px] p-10 shadow-inner"
          dangerouslySetInnerHTML={{ __html: body }}
        />
      )}

      <div className="flex gap-4 flex-wrap items-center pt-8 border-t border-white/5">
        {draft.status === 'draft' && (
          <Button size="lg" onClick={approve} disabled={patch.isPending}>
            Approve Draft
          </Button>
        )}
        {editing ? (
          <>
            <Button size="lg" variant="secondary" onClick={save} disabled={patch.isPending}>Save Changes</Button>
            <Button size="lg" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
          </>
        ) : (
          <Button size="lg" variant="secondary" onClick={() => setEditing(true)}>Edit Draft</Button>
        )}
        <div className="w-px h-6 bg-white/10 mx-3 hidden sm:block"></div>
        <Button size="lg" variant="ghost" onClick={() => exportDraft(draft.id, 'pdf')}>
          Export PDF
        </Button>
        <Button size="lg" variant="ghost" onClick={() => exportDraft(draft.id, 'html')}>
          Export HTML
        </Button>
      </div>
    </div>
  )
}

export default function DraftsPage() {
  const [statusFilter, setStatusFilter] = useState('draft')
  const { data: drafts = [], isLoading } = useDrafts(statusFilter || undefined)

  return (
    <div className="max-w-6xl pb-32">
      <header className="mb-20">
        <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/10 backdrop-blur-xl px-5 py-2 text-xs font-bold uppercase tracking-widest text-zinc-300 mb-8 shadow-sm">
          Outreach Inbox
        </div>
        <h1 className="text-5xl lg:text-6xl font-medium text-white tracking-tighter mb-6 leading-tight">Email Drafts</h1>
        <p className="text-zinc-400 text-xl font-medium w-full leading-relaxed">
          Review subject variants, edit the email body inline, and approve or export without leaving the queue.
        </p>

        <div className="flex gap-4 flex-wrap mt-14 bg-zinc-950/40 backdrop-blur-2xl border border-white/5 rounded-full p-2 w-max shadow-xl">
          {['draft', 'approved', ''].map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`text-sm px-8 py-4 rounded-full font-bold transition-all duration-300 shadow-sm ${
                statusFilter === s
                  ? 'bg-white text-black border border-white'
                  : 'bg-transparent text-zinc-500 border border-transparent hover:bg-white/10 hover:text-white'
              }`}
            >
              {s ? (s.charAt(0).toUpperCase() + s.slice(1)) : 'All Drafts'}
            </button>
          ))}
        </div>
      </header>

      {isLoading ? (
        <div className="text-zinc-500 font-medium text-lg py-16 text-left">Loading drafts...</div>
      ) : drafts.length === 0 ? (
        <div className="text-zinc-500 py-32 border border-white/5 bg-zinc-950/40 backdrop-blur-3xl rounded-[48px] text-center text-2xl font-medium shadow-2xl flex items-center justify-center">No drafts found in this view.</div>
      ) : (
        <div className="flex flex-col gap-8">
          {drafts.map(draft => <DraftItem key={draft.id} draft={draft} />)}
        </div>
      )}
    </div>
  )
}