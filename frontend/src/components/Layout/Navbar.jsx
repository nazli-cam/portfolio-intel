import { useQuery } from '@tanstack/react-query'
import { Bell, LogOut, User } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'
import { signalsApi } from '../../services/api'
import { useNavigate } from 'react-router-dom'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const { data: unreadData } = useQuery({
    queryKey: ['unread-count'],
    queryFn: () => signalsApi.unreadCount().then((r) => r.data),
    refetchInterval: 30_000,
  })

  const unread = unreadData?.unread_count ?? 0

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
      <div />
      <div className="flex items-center gap-4">
        {/* Bell */}
        <button
          onClick={() => navigate('/signals?unread=true')}
          className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
          title="Unread signals"
        >
          <Bell size={18} className="text-gray-600" />
          {unread > 0 && (
            <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] bg-red-500 text-white
                             text-[10px] font-bold rounded-full flex items-center justify-center px-1">
              {unread > 99 ? '99+' : unread}
            </span>
          )}
        </button>

        {/* User info */}
        <div className="flex items-center gap-2 pl-4 border-l border-gray-200">
          <div className="w-7 h-7 bg-brand-100 rounded-full flex items-center justify-center">
            <User size={14} className="text-brand-700" />
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-medium text-gray-800 leading-none">{user?.name}</p>
            <p className="text-xs text-gray-400 capitalize mt-0.5">{user?.role}</p>
          </div>
          <button
            onClick={logout}
            className="ml-2 p-1.5 rounded hover:bg-gray-100 transition-colors"
            title="Sign out"
          >
            <LogOut size={16} className="text-gray-500" />
          </button>
        </div>
      </div>
    </header>
  )
}
