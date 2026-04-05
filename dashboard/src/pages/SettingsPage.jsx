import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ShieldCheck, CalendarDays, KeyRound, SlidersHorizontal } from 'lucide-react'
import client from '../api/client'
import Button from '../components/Button'

function Field({ label, value, onChange, type = 'text', placeholder, helper }) {
  return (
    <div className="space-y-3">
      <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest">{label}</label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full border border-white/10 rounded-2xl bg-black/50 px-6 py-4 text-base text-white focus:outline-none focus:ring-2 focus:ring-white/20 transition-all backdrop-blur-xl shadow-inner"
      />
      {helper && <p className="text-sm font-medium text-zinc-500 leading-relaxed">{helper}</p>}
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
    <section className="py-16 border-t border-white/5">
      <div className="flex items-center gap-4 mb-10">
        <div className="p-3 bg-white/10 rounded-2xl backdrop-blur-xl border border-white/5 shadow-lg"><CalendarDays size={24} className="text-white" /></div>
        <h2 className="font-medium text-white text-3xl tracking-tight">Scheduled Runs</h2>
      </div>

      <div className="grid gap-8 mb-12 w-full bg-zinc-950/60 backdrop-blur-2xl border border-white/5 rounded-[32px] p-10 shadow-2xl">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_120px] gap-6">
          <input
            value={city}
            onChange={e => setCity(e.target.value)}
            placeholder="City"
            className="w-full border border-white/10 rounded-2xl bg-black/50 px-6 py-4 text-base text-white focus:outline-none focus:ring-2 focus:ring-white/20 transition-all shadow-inner"
          />
          <input
            value={state}
            onChange={e => setState(e.target.value.toUpperCase())}
            placeholder="ST"
            maxLength={2}
            className="w-full border border-white/10 rounded-2xl bg-black/50 px-6 py-4 text-base text-white focus:outline-none focus:ring-2 focus:ring-white/20 transition-all shadow-inner text-left"
          />
        </div>
        <div className="space-y-3">
          <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest">Cron Expression</label>
          <input
            value={cron}
            onChange={e => setCron(e.target.value)}
            placeholder="0 9 * * 1"
            className="w-full border border-white/10 rounded-2xl bg-black/50 px-6 py-4 text-base text-white focus:outline-none focus:ring-2 focus:ring-white/20 transition-all shadow-inner font-mono"
          />
          <p className="text-sm font-medium text-zinc-500">Format: min hour dom month dow. Example: <span className="font-bold text-zinc-300">0 9 * * 1</span> for Monday 9am.</p>
        </div>
        <div className="pt-2">
          <Button onClick={() => addSchedule.mutate({ city, state, cron })} disabled={!city || !state} size="lg">
            Add Schedule
          </Button>
        </div>
      </div>

      {schedules.length > 0 && (
        <div className="flex flex-col gap-4">
          {schedules.map(s => (
            <div key={s.job_id} className="flex items-center justify-between gap-6 p-6 bg-zinc-950/40 backdrop-blur-xl border border-white/5 rounded-3xl shadow-lg transition-all hover:bg-zinc-900/60">
              <div className="min-w-0">
                <div className="font-medium text-white text-xl">{s.job_id}</div>
                <div className="text-zinc-500 text-sm font-medium mt-2">Next run: {s.next_run || '—'}</div>
              </div>
              <Button size="md" variant="danger" onClick={() => removeSchedule.mutate(s.job_id)}>Remove</Button>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default function SettingsPage() {
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => client.get('/settings').then(r => r.data),
  })

  const [form, setForm] = useState({
    apollo_api_key: '',
    gemini_api_key: '',
    proxy_url: '',
    max_reviews_default: 0,
  })

  const save = useMutation({
    mutationFn: (data) => client.put('/settings', data),
  })

  if (isLoading) return <div className="text-zinc-500 font-medium text-lg py-16 text-left">Loading settings...</div>

  return (
    <div className="w-full max-w-[1600px] pb-32">
      <header className="mb-20">
        <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/10 backdrop-blur-xl px-5 py-2 text-xs font-bold uppercase tracking-widest text-zinc-300 mb-8 shadow-sm">
          <SlidersHorizontal size={14} />
          System Settings
        </div>
        <h1 className="text-5xl lg:text-6xl font-medium text-white tracking-tighter mb-6 leading-tight">Pipeline Controls</h1>
        <p className="text-zinc-400 text-xl font-medium mt-4 leading-relaxed w-full">
          Manage API keys, default scraper configurations, and automated job schedules.
        </p>
      </header>

      <div className="space-y-0">
        <section className="py-16 border-t border-white/5">
          <div className="flex items-center gap-4 mb-10">
            <div className="p-3 bg-white/10 rounded-2xl backdrop-blur-xl border border-white/5 shadow-lg"><KeyRound size={24} className="text-white" /></div>
            <h2 className="font-medium text-white text-3xl tracking-tight">API Keys</h2>
          </div>
          <div className="grid gap-8 w-full bg-zinc-950/60 backdrop-blur-2xl border border-white/5 rounded-[32px] p-10 shadow-2xl">
            <Field
              label="Apollo API Key"
              name="apollo_api_key"
              type="password"
              value={form.apollo_api_key}
              onChange={e => setForm(f => ({ ...f, apollo_api_key: e.target.value }))}
              placeholder={settings?.apollo_api_key ? '(set — enter new value to update)' : 'Not set'}
              helper="Used to enrich clinics with verified contacts."
            />
            <Field
              label="Gemini API Key"
              name="gemini_api_key"
              type="password"
              value={form.gemini_api_key}
              onChange={e => setForm(f => ({ ...f, gemini_api_key: e.target.value }))}
              placeholder={settings?.gemini_api_key ? '(set — enter new value to update)' : 'Not set'}
              helper="Used for review filtering and draft generation."
            />
          </div>
        </section>

        <section className="py-16 border-t border-white/5">
          <div className="flex items-center gap-4 mb-10">
            <div className="p-3 bg-white/10 rounded-2xl backdrop-blur-xl border border-white/5 shadow-lg"><ShieldCheck size={24} className="text-white" /></div>
            <h2 className="font-medium text-white text-3xl tracking-tight">Scraper Config</h2>
          </div>
          <div className="grid gap-8 w-full bg-zinc-950/60 backdrop-blur-2xl border border-white/5 rounded-[32px] p-10 shadow-2xl">
            <Field
              label="Proxy URL (optional)"
              name="proxy_url"
              value={form.proxy_url}
              onChange={e => setForm(f => ({ ...f, proxy_url: e.target.value }))}
              placeholder={settings?.proxy_url ? '(set — enter new value to update)' : 'http://proxy:8080'}
              helper="Use this only when rotating egress is required for scraping."
            />
            <div className="space-y-3">
              <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest">Max Reviews Default</label>
              <input
                type="number"
                value={form.max_reviews_default}
                onChange={e => setForm(f => ({ ...f, max_reviews_default: Number(e.target.value) }))}
                min={0}
                className="w-full border border-white/10 rounded-2xl bg-black/50 px-6 py-4 text-base text-white focus:outline-none focus:ring-2 focus:ring-white/20 transition-all shadow-inner"
              />
              <p className="text-sm font-medium text-zinc-500">Set to <span className="font-bold text-zinc-300">0</span> for uncapped review scraping.</p>
            </div>
          </div>
        </section>

        <div className="py-10 flex items-center gap-6 border-t border-white/5">
          <Button size="lg" onClick={() => save.mutate(form)} disabled={save.isPending}>
            {save.isPending ? 'Saving...' : 'Save Settings'}
          </Button>
          {save.isSuccess && <span className="text-emerald-400 text-base font-bold bg-emerald-500/10 px-5 py-3 rounded-2xl border border-emerald-500/20 shadow-sm">Changes saved successfully.</span>}
        </div>

        <SchedulerConfig />
      </div>
    </div>
  )
}