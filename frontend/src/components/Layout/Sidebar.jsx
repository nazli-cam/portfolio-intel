import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Building2, Zap, FileText, Users } from 'lucide-react'
import clsx from 'clsx'

const nav = [
  { to: '/',          label: 'Dashboard',  icon: LayoutDashboard, end: true },
  { to: '/companies', label: 'Portfolio',  icon: Building2 },
  { to: '/founders',  label: 'Founders',   icon: Users },
  { to: '/signals',   label: 'Signals',    icon: Zap },
  { to: '/reports',   label: 'Reports',    icon: FileText },
]

export default function Sidebar() {
  return (
    <aside className="w-56 bg-brand-900 flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-brand-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-brand-400 rounded-md flex items-center justify-center">
            <Zap size={16} className="text-brand-900" />
          </div>
          <span className="text-white font-semibold text-sm leading-tight">
            Portfolio<br />Intelligence
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-brand-800 text-white'
                  : 'text-brand-200 hover:bg-brand-800 hover:text-white'
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-brand-800">
        <p className="text-brand-400 text-xs">v1.0.0</p>
      </div>
    </aside>
  )
}
