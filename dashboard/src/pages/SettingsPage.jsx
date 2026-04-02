import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import client from '../api/client'
import Card from '../components/Card'
import Button from '../components/Button'

export default function SettingsPage() {
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => client.get('/settings').then(r => r.data),
  })

  const [form, setForm] = useState({
    apollo_api_key: '',
    gemini_api_key: '',
    proxy_url: '',
    max_reviews_default: 200,
  })

  const save = useMutation({
    mutationFn: (data) => client.put('/settings', data),
  })

  if (isLoading) return <div className="text-muted text-sm">Loading…</div>

  const Field = ({ label, name, type = 'text', placeholder }) => (
    <div>
      <label className="block text-sm font-semibold text-ink mb-1">{label}</label>
      <input
        type={type}
        value={form[name]}
        onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))}
        placeholder={placeholder || (settings?.[name] ? '(set — enter new value to update)' : 'Not set')}
        className="w-full border border-gray-200 rounded-btn px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
      />
    </div>
  )

  return (
    <div>
      <h1 className="text-2xl font-bold text-ink mb-6">Settings</h1>

      <div className="flex flex-col gap-6 max-w-lg">
        <Card>
          <h2 className="font-semibold text-ink mb-4">API Keys</h2>
          <div className="flex flex-col gap-4">
            <Field label="Apollo API Key" name="apollo_api_key" type="password" />
            <Field label="Gemini API Key" name="gemini_api_key" type="password" />
          </div>
        </Card>

        <Card>
          <h2 className="font-semibold text-ink mb-4">Scraper Config</h2>
          <div className="flex flex-col gap-4">
            <Field label="Proxy URL (optional)" name="proxy_url" placeholder="http://proxy:8080" />
            <div>
              <label className="block text-sm font-semibold text-ink mb-1">Max Reviews Default</label>
              <input
                type="number"
                value={form.max_reviews_default}
                onChange={e => setForm(f => ({ ...f, max_reviews_default: Number(e.target.value) }))}
                min={20}
                max={500}
                className="w-full border border-gray-200 rounded-btn px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>
          </div>
        </Card>

        <div className="flex gap-2">
          <Button
            onClick={() => save.mutate(form)}
            disabled={save.isPending}
          >
            {save.isPending ? 'Saving…' : 'Save Settings'}
          </Button>
          {save.isSuccess && <span className="text-green-600 text-sm self-center">Saved ✓</span>}
        </div>

        {/* Scheduler */}
        <SchedulerConfig />
      </div>
    </div>
  )
}

function SchedulerConfig() {
  const [city, setCity] = useState('')
  const [state, setState] = useState('')
  const [cron, setCron] = useState('0 9 * * 1')
  const qc = useQueryClient()

  const { data: schedules = [] } = useQuery({
    queryKey: ['schedules'],
    queryFn: () => client.get('/settings/schedules').then(r => r.data),
  })

  const addSchedule = useMutation({
    mutationFn: (data) => client.post('/settings/schedules', data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['schedules'] }); setCity(''); setState('') },
  })

  const removeSchedule = useMutation({
    mutationFn: (jobId) => client.delete(`/settings/schedules/${jobId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedules'] }),
  })

  return (
    <Card>
      <h2 className="font-semibold text-ink mb-4">Scheduled Runs</h2>
      <div className="flex flex-col gap-3 mb-4">
        <div className="flex gap-2">
          <input value={city} onChange={e => setCity(e.target.value)} placeholder="City" className="flex-1 border border-gray-200 rounded-btn px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
          <input value={state} onChange={e => setState(e.target.value.toUpperCase())} placeholder="ST" maxLength={2} className="w-16 border border-gray-200 rounded-btn px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
        </div>
        <div>
          <label className="block text-xs font-semibold text-muted mb-1">Cron Expression</label>
          <input value={cron} onChange={e => setCron(e.target.value)} placeholder="0 9 * * 1" className="w-full border border-gray-200 rounded-btn px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30" />
          <p className="text-xs text-muted mt-1">Format: min hour dom month dow — e.g. every Monday 9am: <code>0 9 * * 1</code></p>
        </div>
        <Button size="sm" onClick={() => addSchedule.mutate({ city, state, cron })} disabled={!city || !state}>
          Add Schedule
        </Button>
      </div>
      {schedules.length > 0 && (
        <div className="flex flex-col gap-2">
          {schedules.map(s => (
            <div key={s.job_id} className="flex items-center justify-between text-sm bg-subtle rounded-btn px-3 py-2">
              <div>
                <span className="font-semibold text-ink">{s.job_id}</span>
                <span className="text-muted ml-2 text-xs">next: {s.next_run || '—'}</span>
              </div>
              <Button size="sm" variant="ghost" onClick={() => removeSchedule.mutate(s.job_id)}>Remove</Button>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
