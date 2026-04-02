import { NavLink } from 'react-router-dom'
import { Activity, Building2, Mail, Settings } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/runs',     label: 'Runs',     Icon: Activity  },
  { to: '/clinics',  label: 'Clinics',  Icon: Building2 },
  { to: '/drafts',   label: 'Drafts',   Icon: Mail      },
  { to: '/settings', label: 'Settings', Icon: Settings  },
]

function LavenderMark() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="16" cy="16" r="16" fill="#7c4dbe" fillOpacity="0.2"/>
      <path d="M16 26V14" stroke="#7c4dbe" strokeWidth="1.8" strokeLinecap="round"/>
      <ellipse cx="16" cy="11" rx="2.5" ry="3.5" fill="#7c4dbe" opacity="0.9"/>
      <ellipse cx="12" cy="13" rx="2" ry="3" fill="#7c4dbe" opacity="0.6" transform="rotate(-20 12 13)"/>
      <ellipse cx="20" cy="13" rx="2" ry="3" fill="#7c4dbe" opacity="0.6" transform="rotate(20 20 13)"/>
    </svg>
  )
}

export default function Layout({ children }) {
  return (
    <div className="flex min-h-screen bg-bg">
      {/* Sidebar — 64px, dark, icon-only */}
      <aside className="w-16 bg-sidebar flex flex-col items-center py-5 gap-2 sticky top-0 h-screen shrink-0">
        {/* Logo mark */}
        <div className="mb-4">
          <LavenderMark />
        </div>

        {/* Nav items */}
        <nav className="flex flex-col items-center gap-1 w-full px-2">
          {NAV_ITEMS.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              title={label}
              className={({ isActive }) =>
                `w-10 h-10 flex items-center justify-center rounded-xl transition-all duration-150 ${
                  isActive
                    ? 'bg-primary text-white shadow-sm'
                    : 'text-muted hover:bg-sidebar-hover hover:text-white'
                }`
              }
            >
              <Icon size={20} strokeWidth={1.8} />
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-h-screen overflow-y-auto">
        <div className="max-w-6xl mx-auto px-8 py-8">
          {children}
        </div>
      </main>
    </div>
  )
}
