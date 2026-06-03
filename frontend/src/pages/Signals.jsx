import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import { ExternalLink, CheckCheck, Filter, ThumbsDown, ThumbsUp, Zap } from 'lucide-react'
import { signalsApi, companiesApi } from '../services/api'
import clsx from 'clsx'

const IMPORTANCE_CLASS = {
  high: 'badge-high',
  medium: 'badge-medium',
  low: 'badge-low',
}

const TYPE_LABEL = {
  new_hire: 'New Hire',
  departure: 'Departure',
  founder_post: 'Founder Post',
  funding: 'Funding',
  partnership: 'Partnership',
  product_launch: 'Product Launch',
  exit: 'Exit',
  other: 'Other',
}

const TYPE_COLOR = {
  new_hire: 'bg-emerald-100 text-emerald-700',
  departure: 'bg-red-100 text-red-700',
  founder_post: 'bg-purple-100 text-purple-700',
  funding: 'bg-blue-100 text-blue-700',
  partnership: 'bg-indigo-100 text-indigo-700',
  product_launch: 'bg-orange-100 text-orange-700',
  exit: 'bg-red-900 text-red-100',
  other: 'bg-gray-100 text-gray-600',
}

export default function Signals() {
  const qc = useQueryClient()
  const [searchParams] = useSearchParams()
  const [filters, setFilters] = useState({
    companyId: '',
    signalType: '',
    unreadOnly: searchParams.get('unread') === 'true',
    hideDuplicates: false,
  })

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companiesApi.list().then((r) => r.data),
  })

  const { data: signals = [], isLoading, refetch } = useQuery({
    queryKey: ['signals', filters],
    queryFn: () =>
      signalsApi
        .list({
          company_id: filters.companyId || undefined,
          signal_type: filters.signalType || undefined,
          unread_only: filters.unreadOnly,
          hide_duplicates: filters.hideDuplicates,
          limit: 100,
        })
        .then((r) => r.data),
  })

  const markReadMutation = useMutation({
    mutationFn: (id) => signalsApi.update(id, { is_read: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['signals'] })
      qc.invalidateQueries({ queryKey: ['unread-count'] })
    },
  })

  const feedbackMutation = useMutation({
    mutationFn: ({ id, isAccurate }) => signalsApi.feedback(id, isAccurate),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['signals'] }),
  })

  const markAllReadMutation = useMutation({
    mutationFn: () => signalsApi.markAllRead(filters.companyId || undefined),
    onSuccess: ({ data }) => {
      qc.invalidateQueries({ queryKey: ['signals'] })
      qc.invalidateQueries({ queryKey: ['unread-count'] })
      toast.success(`Marked ${data.marked_read} signals as read`)
    },
  })

  const unreadCount = signals.filter((s) => !s.is_read).length

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Signals</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {signals.length} signals {unreadCount > 0 && `· ${unreadCount} unread`}
          </p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={() => markAllReadMutation.mutate()}
            disabled={markAllReadMutation.isPending}
            className="btn-secondary flex items-center gap-2 text-sm"
          >
            <CheckCheck size={15} />
            Mark all read
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap items-center gap-3">
        <Filter size={15} className="text-gray-400 shrink-0" />
        <select
          value={filters.companyId}
          onChange={(e) => setFilters((f) => ({ ...f, companyId: e.target.value }))}
          className="input !w-auto text-sm"
        >
          <option value="">All companies</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>

        <select
          value={filters.signalType}
          onChange={(e) => setFilters((f) => ({ ...f, signalType: e.target.value }))}
          className="input !w-auto text-sm"
        >
          <option value="">All types</option>
          {Object.entries(TYPE_LABEL).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>

        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.unreadOnly}
            onChange={(e) => setFilters((f) => ({ ...f, unreadOnly: e.target.checked }))}
            className="rounded"
          />
          Unread only
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.hideDuplicates}
            onChange={(e) => setFilters((f) => ({ ...f, hideDuplicates: e.target.checked }))}
            className="rounded"
          />
          Hide duplicates
        </label>
      </div>

      {/* Signal list */}
      {isLoading ? (
        <div className="py-12 text-center text-gray-400 text-sm">Loading signals...</div>
      ) : signals.length === 0 ? (
        <div className="card py-16 text-center">
          <Zap size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="text-gray-500 font-medium">No signals found</p>
          <p className="text-gray-400 text-sm mt-1">
            {filters.unreadOnly ? 'All signals have been read!' : 'Run the intelligence job to start collecting signals.'}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {signals.map((s) => (
            <div
              key={s.id}
              className={clsx(
                'card p-4 hover:shadow-md transition-shadow cursor-pointer',
                !s.is_read && 'border-l-4 border-l-brand-500'
              )}
              onClick={() => {
                if (!s.is_read) markReadMutation.mutate(s.id)
              }}
            >
              <div className="flex items-start gap-3">
                {/* Type badge */}
                <span
                  className={clsx(
                    'shrink-0 inline-flex items-center px-2 py-1 rounded text-xs font-medium mt-0.5',
                    TYPE_COLOR[s.signal_type] || TYPE_COLOR.other
                  )}
                >
                  {TYPE_LABEL[s.signal_type] || s.signal_type}
                </span>

                <div className="flex-1 min-w-0">
                  {/* Company + importance + badges */}
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="text-xs font-semibold text-gray-600">{s.company_name}</span>
                    <span className={IMPORTANCE_CLASS[s.importance] || 'badge-low'}>
                      {s.importance}
                    </span>
                    {!s.is_read && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-brand-100 text-brand-700">
                        NEW
                      </span>
                    )}
                    {s.is_duplicate && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-400 border border-gray-200">
                        Possible duplicate
                      </span>
                    )}
                  </div>

                  {/* Title */}
                  <p className="text-sm font-medium text-gray-900">{s.title}</p>

                  {/* Person name */}
                  {s.person_name && (
                    <p className="text-xs text-blue-500 font-medium mt-0.5">{s.person_name}</p>
                  )}

                  {/* Description */}
                  {s.description && (
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{s.description}</p>
                  )}
                </div>

                <div className="shrink-0 flex flex-col items-end gap-2">
                  <span className="text-xs text-gray-400">
                    {formatDistanceToNow(new Date(s.detected_at), { addSuffix: true })}
                  </span>
                  {s.confidence != null && (
                    <span className="text-[10px] text-gray-400 font-medium">
                      {Math.round(s.confidence * 100)}% conf.
                    </span>
                  )}
                  {s.source_url && (
                    <a
                      href={s.source_url}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-gray-400 hover:text-brand-600"
                    >
                      <ExternalLink size={13} />
                    </a>
                  )}
                  <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => feedbackMutation.mutate({ id: s.id, isAccurate: true })}
                      title="Accurate"
                      className={clsx('p-1 rounded transition-colors', s.is_accurate === true ? 'text-emerald-600 bg-emerald-50' : 'text-gray-300 hover:text-emerald-500')}
                    >
                      <ThumbsUp size={12} />
                    </button>
                    <button
                      onClick={() => feedbackMutation.mutate({ id: s.id, isAccurate: false })}
                      title="Inaccurate"
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
  )
}
