import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { Building2, Zap, TrendingUp, Bell, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import { companiesApi, signalsApi, adminApi } from '../services/api'

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

export default function Dashboard() {
  const navigate = useNavigate()

  const { data: companies = [] } = useQuery({
    queryKey: ['companies'],
    queryFn: () => companiesApi.list().then((r) => r.data),
  })

  const { data: signals = [] } = useQuery({
    queryKey: ['signals', 'recent'],
    queryFn: () => signalsApi.list({ limit: 10 }).then((r) => r.data),
  })

  const { data: unreadData } = useQuery({
    queryKey: ['unread-count'],
    queryFn: () => signalsApi.unreadCount().then((r) => r.data),
    refetchInterval: 60_000,
  })

  const highSignals = signals.filter((s) => s.importance === 'high')
  const unread = unreadData?.unread_count ?? 0

  const triggerJob = async () => {
    try {
      await adminApi.triggerDailyJob()
      toast.success('Intelligence job triggered — check Signals in a few minutes')
    } catch {
      toast.error('Failed to trigger job')
    }
  }

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Portfolio intelligence overview</p>
        </div>
        <button onClick={triggerJob} className="btn-secondary flex items-center gap-2 text-sm">
          <RefreshCw size={15} />
          Run intelligence job
        </button>
      </div>

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
          value={highSignals.length}
          icon={TrendingUp}
          color="bg-red-500"
          onClick={() => navigate('/signals?importance=high')}
        />
        <StatCard
          label="Signals (all time)"
          value={signals.length > 0 ? undefined : 0}
          icon={Zap}
          color="bg-emerald-500"
          onClick={() => navigate('/signals')}
        />
      </div>

      {/* Recent signals */}
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

        {signals.length === 0 ? (
          <div className="py-12 text-center text-gray-400 text-sm">
            <Zap size={32} className="mx-auto mb-3 opacity-30" />
            <p>No signals yet. Add portfolio companies and run the intelligence job.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {signals.map((s) => (
              <div
                key={s.id}
                className={`px-5 py-3.5 flex items-start gap-3 hover:bg-gray-50 cursor-pointer ${
                  !s.is_read ? 'bg-blue-50/40' : ''
                }`}
                onClick={() => navigate('/signals')}
              >
                <div className="mt-0.5 shrink-0">
                  <span className={IMPORTANCE_CLASS[s.importance] || 'badge-low'}>
                    {s.importance}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-gray-500 font-medium">{s.company_name}</span>
                    <span className="text-xs text-gray-400">·</span>
                    <span className="text-xs text-gray-400">
                      {TYPE_LABEL[s.signal_type] || s.signal_type}
                    </span>
                  </div>
                  <p className="text-sm text-gray-900 mt-0.5 font-medium truncate">{s.title}</p>
                  {s.description && (
                    <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{s.description}</p>
                  )}
                </div>
                <span className="text-xs text-gray-400 shrink-0 mt-0.5">
                  {formatDistanceToNow(new Date(s.detected_at), { addSuffix: true })}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
