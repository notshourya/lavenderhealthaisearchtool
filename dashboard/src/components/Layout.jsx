import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/runs', label: 'Runs', icon: '⚡' },
  { to: '/clinics', label: 'Clinics', icon: '🏥' },
  { to: '/drafts', label: 'Drafts', icon: '✉️' },
  { to: '/settings', label: 'Settings', icon: '⚙️' },
]

export default function Layout({ children }) {
  return (
    <div className="flex min-h-screen bg-[#f8f9ff]">
      {/* Sidebar */}
      <aside className="w-60 bg-surface shadow-card flex flex-col py-8 px-4 sticky top-0 h-screen">
        <div className="mb-10 px-2">
          <div className="text-primary font-bold text-lg tracking-tight">LavenderHealth</div>
          <div className="text-muted text-xs mt-0.5">Outreach Pipeline</div>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-btn text-sm font-semibold transition-all duration-150 ${
                  isActive
                    ? 'bg-primary text-white shadow-sm'
                    : 'text-muted hover:bg-subtle hover:text-ink'
                }`
              }
            >
              <span>{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 px-8 py-8 max-w-6xl">
        {children}
      </main>
    </div>
  )
}
