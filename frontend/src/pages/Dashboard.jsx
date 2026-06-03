import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow, format } from 'date-fns'
import {
  Building2, Zap, TrendingUp, Bell, RefreshCw,
  Clock, CheckCircle, AlertCircle, Loader, WifiOff, ThumbsUp, ThumbsDown,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { companiesApi, signalsApi, adminApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
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
  other: 'Other',
}

function StatCard({ label, value, icon: Icon, color, onClick }) {
  return (
    <button
      onClick={onClick}
      className="card p-5 flex items-center gap-4 hover:shadow-md transition-shadow text-left w-full"
    >
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value ?? '—'}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </button>
  )
}

function SchedulerStatus() {
  const { data: status, isLoading, isError, refetch } = useQuery({
    queryKey: ['scheduler-status'],
    queryFn: () => adminApi.schedulerStatus().then((r) => r.data),
    refetchInterval: 15_000,
    retry: 2,
  })

  const triggerMutation = useMutation({
    mutationFn: () => adminApi.triggerDailyJob(),
    onSuccess: () => {
      toast.success('Intelligence job triggered — signals will appear shortly')
      refetch()
    },
    onError: (err) => {
      const detail = err.response?.data?.detail
      if (err.response?.status === 409) {
        toast.error('Job is already running')
      } else {
        toast.error(detail || 'Failed to trigger job')
      }
    },
  })

  if (isLoading) return null

  if (isError) {
    return (
      <div className="card p-4 flex items-center gap-3 text-gray-400">
        <WifiOff size={14} />
        <p className="text-sm">Scheduler status unavailable — backend may be restarting</p>
      </div>
    )
  }

  const statusIcon = status?.is_running
    ? <Loader size={14} className="animate-spin text-blue-500" />
    : status?.last_run_status === 'success'
    ? <CheckCircle size={14} className="text-emerald-500" />
    : status?.last_run_status === 'partial'
    ? <AlertCircle size={14} className="text-amber-500" />
    : status?.last_run_status === 'error'
    ? <AlertCircle size={14} className="text-red-500" />
    : <Clock size={14} className="text-gray-400" />

  return (
    <div className="card p-4 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        {statusIcon}
        <div>
          <p className="text-sm font-medium text-gray-800">
            {status?.is_running ? 'Job running…' : 'Daily intelligence job'}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            {status?.last_run_at
              ? <>Last run {formatDistanceToNow(new Date(status.last_run_at), { addSuffix: true })}
                  {' '}· {status.last_run_new_signals} new signals
                  {status.last_run_status === 'partial' && ' · some errors'}</>
              : 'Never run'}
            {status?.next_run_at && !status?.is_running && (
              <> · Next: {format(new Date(status.next_run_at), 'HH:mm')} UTC</>
            )}
          </p>
        </div>
      </div>
      <button
        onClick={() => triggerMutation.mutate()}
        disabled={status?.is_running || triggerMutation.isPending}
        className="btn-secondary flex items-center gap-2 text-sm py-1.5 shrink-0"
      >
        <RefreshCw size={14} className={clsx(status?.is_running && 'animate-spin')} />
        Run now
      </button>
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const feedbackMutation = useMutation({
    mutationFn: ({ id, isAccurate }) => signalsApi.feedback(id, isAccurate),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['signals', 'feed'] }),
  })

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companiesApi.list().then((r) => r.data),
  })

  const { data: recentSignals = [] } = useQuery({
    queryKey: ['signals', 'feed'],
    queryFn: () => signalsApi.list({ limit: 10, order_by: 'detected_at', sort: 'desc' }).then((r) => r.data),
  })

  // COUNT(*) queries — no limit, accurate regardless of portfolio size
  const { data: totalData } = useQuery({
    queryKey: ['signals', 'count', 'total'],
    queryFn: () => signalsApi.count().then((r) => r.data),
  })

  const { data: highData } = useQuery({
    queryKey: ['signals', 'count', 'high'],
    queryFn: () => signalsApi.count({ importance: 'high' }).then((r) => r.data),
  })

  const { data: unreadData } = useQuery({
    queryKey: ['unread-count'],
    queryFn: () => signalsApi.unreadCount().then((r) => r.data),
    refetchInterval: 60_000,
  })

  const totalSignals = totalData?.count ?? '—'
  const highCount = highData?.count ?? '—'
  const unread = unreadData?.unread_count ?? 0

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">Portfolio intelligence overview</p>
      </div>

      {/* Scheduler status — admin only */}
      {isAdmin && <SchedulerStatus />}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Portfolio companies"
          value={companies.length}
          icon={Building2}
          color="bg-brand-800"
          onClick={() => navigate('/companies')}
        />
        <StatCard
          label="Unread signals"
          value={unread}
          icon={Bell}
          color="bg-amber-500"
          onClick={() => navigate('/signals?unread=true')}
        />
        <StatCard
          label="High-priority signals"
          value={highCount}
          icon={TrendingUp}
          color="bg-red-500"
          onClick={() => navigate('/signals?importance=high')}
        />
        <StatCard
          label="Total signals"
          value={totalSignals}
          icon={Zap}
          color="bg-emerald-500"
          onClick={() => navigate('/signals')}
        />
      </div>

      {/* Recent signal feed */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Recent Signals</h2>
          <button
            onClick={() => navigate('/signals')}
            className="text-sm text-brand-600 hover:underline"
          >
            View all
          </button>
        </div>

        {recentSignals.length === 0 ? (
          <div className="py-12 text-center text-gray-400 text-sm">
            <Zap size={32} className="mx-auto mb-3 opacity-30" />
            <p>No signals yet. Add portfolio companies and run the intelligence job.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {recentSignals.map((s) => (
              <div
                key={s.id}
                className={clsx(
                  'px-5 py-3.5 flex items-start gap-3 hover:bg-gray-50',
                  !s.is_read && 'bg-blue-50/40',
                  s.source_url ? 'cursor-pointer' : 'cursor-default'
                )}
                onClick={() => s.source_url && window.open(s.source_url, '_blank', 'noreferrer')}
              >
                <div className="mt-0.5 shrink-0">
                  <span className={IMPORTANCE_CLASS[s.importance] || 'badge-low'}>
                    {s.importance}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-gray-500 font-medium">{s.company_name}</span>
                    <span className="text-xs text-gray-300">·</span>
                    <span className="text-xs text-gray-400">
                      {TYPE_LABEL[s.signal_type] || s.signal_type}
                    </span>
                    {s.person_name && (
                      <>
                        <span className="text-xs text-gray-300">·</span>
                        <span className="text-xs text-blue-500 font-medium">{s.person_name}</span>
                      </>
                    )}
                  </div>
                  <p className="text-sm text-gray-900 mt-0.5 font-medium truncate">{s.title}</p>
                  {s.description && (
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{s.description}</p>
                  )}
                </div>
                <div className="shrink-0 flex flex-col items-end gap-1.5">
                  <span className="text-xs text-gray-400">
                    {formatDistanceToNow(new Date(s.detected_at), { addSuffix: true })}
                  </span>
                  <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => feedbackMutation.mutate({ id: s.id, isAccurate: true })}
                      title="Mark accurate"
                      className={clsx('p-1 rounded transition-colors', s.is_accurate === true ? 'text-emerald-600 bg-emerald-50' : 'text-gray-300 hover:text-emerald-500')}
                    >
                      <ThumbsUp size={11} />
                    </button>
                    <button
                      onClick={() => feedbackMutation.mutate({ id: s.id, isAccurate: false })}
                      title="Mark inaccurate"
                      className={clsx('p-1 rounded transition-colors', s.is_accurate === false ? 'text-red-500 bg-red-50' : 'text-gray-300 hover:text-red-400')}
                    >
                      <ThumbsDown size={11} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
