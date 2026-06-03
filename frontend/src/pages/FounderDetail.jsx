import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ExternalLink, Linkedin, ThumbsDown, ThumbsUp, Twitter } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { foundersApi, signalsApi } from '../services/api'
import clsx from 'clsx'

const TYPE_LABEL = {
  new_hire: 'New Hire', departure: 'Departure', founder_post: 'Founder Post',
  funding: 'Funding', partnership: 'Partnership', product_launch: 'Product Launch',
  exit: 'Exit', other: 'Other',
}
const TYPE_COLOR = {
  new_hire: 'bg-emerald-100 text-emerald-700', departure: 'bg-red-100 text-red-700',
  founder_post: 'bg-purple-100 text-purple-700', funding: 'bg-blue-100 text-blue-700',
  partnership: 'bg-indigo-100 text-indigo-700', product_launch: 'bg-orange-100 text-orange-700',
  exit: 'bg-red-900 text-red-100', other: 'bg-gray-100 text-gray-600',
}

export default function FounderDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: founder, isLoading } = useQuery({
    queryKey: ['founder', Number(id)],
    queryFn: () => foundersApi.get(id).then((r) => r.data),
  })

  const { data: signals = [], isLoading: loadingSignals } = useQuery({
    queryKey: ['founder-signals', Number(id)],
    queryFn: () => foundersApi.signals(id).then((r) => r.data),
    enabled: !!id,
  })

  const feedbackMutation = useMutation({
    mutationFn: ({ signalId, isAccurate }) => signalsApi.feedback(signalId, isAccurate),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['founder-signals', Number(id)] }),
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="w-7 h-7 border-2 border-brand-800 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }
  if (!founder) {
    return (
      <div className="py-24 text-center">
        <p className="text-gray-500">Founder not found.</p>
        <button onClick={() => navigate('/founders')} className="btn-secondary mt-4">Back</button>
      </div>
    )
  }

  return (
    <div className="max-w-3xl space-y-6">
      <button onClick={() => navigate('/founders')} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-800">
        <ArrowLeft size={16} /> Back to founders
      </button>

      {/* Header card */}
      <div className="card p-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-brand-100 flex items-center justify-center shrink-0">
            <span className="text-xl font-bold text-brand-700">{founder.name[0]}</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">{founder.name}</h1>
            {founder.company_name && (
              <p
                className="text-sm text-brand-600 hover:underline cursor-pointer mt-0.5"
                onClick={() => navigate(`/companies/${founder.company_id}`)}
              >
                {founder.company_name}
              </p>
            )}
            <div className="flex items-center gap-3 mt-2">
              {founder.linkedin_url && (
                <a href={founder.linkedin_url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-sm text-gray-500 hover:text-brand-600">
                  <Linkedin size={14} /> LinkedIn
                </a>
              )}
              {founder.twitter_url && (
                <a href={founder.twitter_url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-sm text-gray-500 hover:text-brand-600">
                  <Twitter size={14} /> Twitter
                </a>
              )}
            </div>
          </div>
        </div>
        {founder.notes && (
          <p className="mt-4 text-sm text-gray-600 leading-relaxed border-t border-gray-100 pt-4">{founder.notes}</p>
        )}
      </div>

      {/* Signals mentioning this founder */}
      <div className="card">
        <div className="px-6 pt-5 pb-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Signals mentioning {founder.name}</h2>
        </div>
        <div className="px-6 pb-4">
          {loadingSignals ? (
            <div className="py-10 text-center text-gray-400 text-sm">Loading…</div>
          ) : signals.length === 0 ? (
            <div className="py-12 text-center">
              <p className="text-gray-500 text-sm">No signals found for this person yet.</p>
            </div>
          ) : (
            <div>
              {signals.map((s) => (
                <div key={s.id} className="flex gap-4 py-4 border-b border-gray-50 last:border-0">
                  <div className="pt-0.5 shrink-0">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${TYPE_COLOR[s.signal_type] || TYPE_COLOR.other}`}>
                      {TYPE_LABEL[s.signal_type] || s.signal_type}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-gray-500 mb-0.5">{s.company_name}</p>
                    <p className="font-medium text-gray-900 text-sm leading-snug">{s.title}</p>
                    {s.description && (
                      <p className="text-sm text-gray-600 mt-1 leading-relaxed line-clamp-2">{s.description}</p>
                    )}
                    <div className="flex items-center gap-3 mt-2">
                      {s.source_url && (
                        <a href={s.source_url} target="_blank" rel="noreferrer" className="text-xs text-brand-600 hover:underline flex items-center gap-1">
                          Source <ExternalLink size={11} />
                        </a>
                      )}
                      <span className="text-xs text-gray-400 ml-auto">
                        {formatDistanceToNow(new Date(s.detected_at), { addSuffix: true })}
                      </span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => feedbackMutation.mutate({ signalId: s.id, isAccurate: true })}
                          className={clsx('p-1 rounded transition-colors', s.is_accurate === true ? 'text-emerald-600 bg-emerald-50' : 'text-gray-300 hover:text-emerald-500')}
                        >
                          <ThumbsUp size={12} />
                        </button>
                        <button
                          onClick={() => feedbackMutation.mutate({ signalId: s.id, isAccurate: false })}
                          className={clsx('p-1 rounded transition-colors', s.is_accurate === false ? 'text-red-500 bg-red-50' : 'text-gray-300 hover:text-red-400')}
                        >
                          <ThumbsDown size={12} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
