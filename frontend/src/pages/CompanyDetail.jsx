import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import {
  ArrowLeft, ExternalLink, Globe, Linkedin, Pencil, RefreshCw, ThumbsDown, ThumbsUp, Twitter, X,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useAuth } from '../contexts/AuthContext'
import { companiesApi, signalsApi } from '../services/api'
import clsx from 'clsx'

const SIGNAL_TYPE_LABELS = {
  new_hire: 'New Hire',
  departure: 'Departure',
  founder_post: 'Founder Post',
  funding: 'Funding',
  partnership: 'Partnership',
  product_launch: 'Product Launch',
  exit: 'Exit',
  other: 'Other',
}

const SIGNAL_TYPE_COLORS = {
  new_hire: 'bg-green-100 text-green-700',
  departure: 'bg-red-100 text-red-700',
  founder_post: 'bg-purple-100 text-purple-700',
  funding: 'bg-blue-100 text-blue-700',
  partnership: 'bg-yellow-100 text-yellow-700',
  product_launch: 'bg-orange-100 text-orange-700',
  exit: 'bg-red-900 text-red-100',
  other: 'bg-gray-100 text-gray-600',
}

const STAGE_OPTIONS = ['Pre-seed', 'Seed', 'Series A', 'Series B', 'Series C+', 'Growth', 'Public']

const TABS = [
  { key: '', label: 'All' },
  { key: 'new_hire', label: 'Hires' },
  { key: 'departure', label: 'Departures' },
  { key: 'founder_post', label: 'Press' },
  { key: 'funding', label: 'Funding' },
  { key: 'exit', label: 'Exit' },
]

function EditModal({ company, onClose }) {
  const qc = useQueryClient()
  const { register, handleSubmit, formState: { errors } } = useForm({ defaultValues: company })

  const mutation = useMutation({
    mutationFn: (data) => companiesApi.update(company.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['company', company.id] })
      toast.success('Company updated')
      onClose()
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to save'),
  })

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Edit Company</h2>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg">
            <X size={18} className="text-gray-500" />
          </button>
        </div>
        <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="label">Company name *</label>
              <input {...register('name', { required: 'Name is required' })} className="input" />
              {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
            </div>
            <div>
              <label className="label">Website</label>
              <input {...register('website')} className="input" />
            </div>
            <div>
              <label className="label">LinkedIn URL</label>
              <input {...register('linkedin_url')} className="input" />
            </div>
            <div>
              <label className="label">Industry</label>
              <input {...register('industry')} className="input" />
            </div>
            <div>
              <label className="label">Stage</label>
              <select {...register('stage')} className="input">
                <option value="">Select stage</option>
                {STAGE_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Headquarters</label>
              <input {...register('headquarters')} className="input" />
            </div>
            <div>
              <label className="label">Founded year</label>
              <input {...register('founded_year', { valueAsNumber: true })} type="number" className="input" min={1900} max={new Date().getFullYear()} />
            </div>
            <div className="col-span-2">
              <label className="label">Description / Notes</label>
              <textarea {...register('description')} className="input" rows={3} />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={mutation.isPending} className="btn-primary">
              {mutation.isPending ? 'Saving...' : 'Save changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function SignalCard({ signal, onFeedback }) {
  const typeColor = SIGNAL_TYPE_COLORS[signal.signal_type] || SIGNAL_TYPE_COLORS.other
  const typeLabel = SIGNAL_TYPE_LABELS[signal.signal_type] || signal.signal_type
  const isExit = signal.signal_type === 'exit'

  return (
    <div className={clsx('flex gap-4 py-4 border-b border-gray-50 last:border-0', isExit && 'bg-red-50/50 -mx-6 px-6 rounded')}>
      <div className="pt-0.5 shrink-0 flex flex-col gap-1">
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${typeColor}`}>
          {isExit ? '⚠ Exit Signal' : typeLabel}
        </span>
        {signal.is_duplicate && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-400 border border-gray-200">
            Possible duplicate
          </span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 text-sm leading-snug">{signal.title}</p>
        {signal.person_name && (
          <p className="text-xs text-gray-500 mt-0.5">{signal.person_name}</p>
        )}
        {signal.description && (
          <p className="text-sm text-gray-600 mt-1 leading-relaxed">{signal.description}</p>
        )}
        <div className="flex items-center gap-3 mt-2">
          {signal.confidence != null && (
            <span className="text-xs text-gray-400">
              {Math.round(signal.confidence * 100)}% confidence
            </span>
          )}
          {signal.source_url && (
            <a
              href={signal.source_url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-brand-600 hover:underline flex items-center gap-1"
            >
              Source <ExternalLink size={11} />
            </a>
          )}
          <span className="text-xs text-gray-400 ml-auto">
            {formatDistanceToNow(new Date(signal.detected_at), { addSuffix: true })}
          </span>
          {/* Vote buttons */}
          <div className="flex items-center gap-1 ml-2">
            <button
              onClick={() => onFeedback(signal.id, true)}
              title="Accurate"
              className={clsx('p-1 rounded transition-colors', signal.is_accurate === true ? 'text-emerald-600 bg-emerald-50' : 'text-gray-300 hover:text-emerald-500')}
            >
              <ThumbsUp size={12} />
            </button>
            <button
              onClick={() => onFeedback(signal.id, false)}
              title="Inaccurate"
              className={clsx('p-1 rounded transition-colors', signal.is_accurate === false ? 'text-red-500 bg-red-50' : 'text-gray-300 hover:text-red-400')}
            >
              <ThumbsDown size={12} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function CompanyDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [activeTab, setActiveTab] = useState('')
  const [showEdit, setShowEdit] = useState(false)
  const [scanning, setScanning] = useState(false)

  const feedbackMutation = useMutation({
    mutationFn: ({ signalId, isAccurate }) => signalsApi.feedback(signalId, isAccurate),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['company-signals', Number(id)] }),
  })

  const handleFeedback = (signalId, isAccurate) =>
    feedbackMutation.mutate({ signalId, isAccurate })

  const { data: company, isLoading: loadingCompany } = useQuery({
    queryKey: ['company', Number(id)],
    queryFn: () => companiesApi.get(id).then((r) => r.data),
  })

  const { data: signals = [], isLoading: loadingSignals } = useQuery({
    queryKey: ['company-signals', Number(id), activeTab],
    queryFn: () => companiesApi.signals(id, activeTab ? { signal_type: activeTab } : {}).then((r) => r.data),
    enabled: !!id,
  })

  const { data: keyPeople = [] } = useQuery({
    queryKey: ['key-people', Number(id)],
    queryFn: () => companiesApi.keyPeople(id).then((r) => r.data),
    enabled: !!id,
  })

  const handleScan = async () => {
    setScanning(true)
    try {
      await companiesApi.refresh(id)
      toast.success('Intelligence scan queued')
    } catch {
      toast.error('Failed to queue scan')
    } finally {
      setScanning(false)
    }
  }

  if (loadingCompany) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="w-7 h-7 border-2 border-brand-800 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!company) {
    return (
      <div className="py-24 text-center">
        <p className="text-gray-500">Company not found.</p>
        <button onClick={() => navigate('/companies')} className="btn-secondary mt-4">Back to companies</button>
      </div>
    )
  }

  return (
    <div className="max-w-4xl space-y-6">
      {/* Back button */}
      <button
        onClick={() => navigate('/companies')}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800 transition-colors"
      >
        <ArrowLeft size={16} /> Back to companies
      </button>

      {/* Company header card */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900">{company.name}</h1>
            <div className="flex flex-wrap items-center gap-3 mt-2">
              {company.stage && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-brand-100 text-brand-700">
                  {company.stage}
                </span>
              )}
              {company.industry && (
                <span className="text-sm text-gray-500">{company.industry}</span>
              )}
              {company.headquarters && (
                <span className="text-sm text-gray-400">{company.headquarters}</span>
              )}
            </div>
            {company.description && (
              <p className="mt-3 text-sm text-gray-600 leading-relaxed">{company.description}</p>
            )}
          </div>
          {isAdmin && (
            <button
              onClick={() => setShowEdit(true)}
              className="btn-secondary flex items-center gap-2 shrink-0"
            >
              <Pencil size={14} /> Edit
            </button>
          )}
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap gap-4 mt-5 pt-5 border-t border-gray-100">
          {company.website && (
            <a href={company.website} target="_blank" rel="noreferrer"
              className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-brand-600">
              <Globe size={14} /> {company.website.replace(/^https?:\/\//, '')}
            </a>
          )}
          {company.linkedin_url && (
            <a href={company.linkedin_url} target="_blank" rel="noreferrer"
              className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-brand-600">
              <Linkedin size={14} /> LinkedIn
            </a>
          )}
          {company.founded_year && (
            <span className="text-sm text-gray-400">Founded {company.founded_year}</span>
          )}
          {company.last_synced_at && (
            <span className="text-sm text-gray-400 ml-auto">
              Last synced {formatDistanceToNow(new Date(company.last_synced_at), { addSuffix: true })}
            </span>
          )}
        </div>
      </div>

      {/* Signal feed */}
      <div className="card">
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Signal feed</h2>
          {isAdmin && (
            <button
              onClick={handleScan}
              disabled={scanning}
              className="btn-secondary flex items-center gap-2 text-sm"
            >
              <RefreshCw size={14} className={scanning ? 'animate-spin' : ''} />
              {scanning ? 'Scanning…' : 'Run scan'}
            </button>
          )}
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 px-6 pt-3">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'bg-brand-100 text-brand-700'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="px-6 pb-4">
          {loadingSignals ? (
            <div className="py-10 text-center text-gray-400 text-sm">Loading signals…</div>
          ) : signals.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-gray-500 text-sm font-medium">No signals collected yet.</p>
              <p className="text-gray-400 text-xs mt-1">Run the intelligence job to start.</p>
            </div>
          ) : (
            <div className="mt-2">
              {signals.map((s) => <SignalCard key={s.id} signal={s} onFeedback={handleFeedback} />)}
            </div>
          )}
        </div>
      </div>

      {/* Key People */}
      <div className="card p-6">
        <h2 className="font-semibold text-gray-900 mb-4">Key People</h2>
        {keyPeople.length === 0 ? (
          <p className="text-sm text-gray-400">
            No key people yet. Run a scan to fetch key people from Apollo.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {keyPeople.map((p) => (
              <div
                key={p.id}
                className="flex items-start gap-3 p-3 rounded-lg border border-gray-100 hover:bg-gray-50"
              >
                <div className="w-9 h-9 rounded-full bg-brand-100 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-sm font-semibold text-brand-700">{p.name[0]}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-medium text-gray-900 truncate">{p.name}</p>
                    {p.is_founder && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-brand-100 text-brand-700">
                        Founder
                      </span>
                    )}
                  </div>
                  {p.title && (
                    <p className="text-xs text-gray-500 mt-0.5 truncate">{p.title}</p>
                  )}
                  {p.linkedin_url && (
                    <a
                      href={p.linkedin_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-gray-400 hover:text-brand-600 mt-1 inline-block"
                    >
                      <Linkedin size={12} />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showEdit && <EditModal company={company} onClose={() => setShowEdit(false)} />}
    </div>
  )
}
