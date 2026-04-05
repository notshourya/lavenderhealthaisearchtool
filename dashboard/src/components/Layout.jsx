import { NavLink, useMatch, useResolvedPath } from 'react-router-dom'
import { Activity, Building2, Mail, Settings } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/runs',     label: 'Runs',     icon: Activity  },
  { to: '/clinics',  label: 'Clinics',  icon: Building2 },
  { to: '/drafts',   label: 'Drafts',   icon: Mail      },
  { to: '/settings', label: 'Settings', icon: Settings  },
]

function Monogram() {
  return (
    <div className="h-10 w-10 rounded-2xl bg-white text-black flex items-center justify-center text-sm font-bold shadow-[0_0_20px_rgba(255,255,255,0.2)]">
      LH
    </div>
  )
}

function NavItem({ to, label, icon }) {
  const Icon = icon
  const resolved = useResolvedPath(to)
  const isActive = useMatch({ path: resolved.pathname, end: true })

  return (
    <NavLink
      to={to}
      title={label}
      className={`flex w-full items-center gap-4 px-5 py-3.5 rounded-full transition-all duration-300 ${
        isActive
          ? 'bg-white/12 text-white font-medium shadow-sm backdrop-blur-xl border border-white/10'
          : 'bg-transparent text-zinc-500 hover:bg-white/6 hover:text-zinc-200 border border-transparent'
      }`}
    >
      <Icon size={20} strokeWidth={isActive ? 2.5 : 2} className={isActive ? 'text-white' : 'text-zinc-500'} />
      <span className={`text-base tracking-tight ${isActive ? 'text-white font-semibold' : 'text-zinc-500 font-medium'}`}>{label}</span>
    </NavLink>
  )
}

export default function Layout({ children }) {
  return (
    <div className="flex h-screen bg-black text-zinc-100 font-sans antialiased overflow-hidden p-6 gap-6 selection:bg-white/20">
      {/* Floating Sidebar */}
      <aside className="w-[280px] bg-zinc-950/80 backdrop-blur-2xl rounded-[32px] flex flex-col gap-10 h-full shrink-0 border border-white/5 shadow-2xl relative z-20">
        <div className="px-8 pt-10 pb-4">
          <div className="flex items-center gap-4">
            <Monogram />
            <div>
              <div className="font-bold text-white text-lg tracking-tight leading-tight">Lavender</div>
              <div className="text-[13px] text-zinc-500 font-medium tracking-wide">Operations</div>
            </div>
          </div>
        </div>

        <nav className="flex flex-col gap-3 px-6">
          {NAV_ITEMS.map(({ to, label, icon }) => (
            <NavItem key={to} to={to} label={label} icon={icon} />
          ))}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 h-full relative bg-zinc-950/40 backdrop-blur-3xl rounded-[40px] border border-white/5 shadow-2xl overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto no-scrollbar relative z-10">
          <div className="mx-auto w-full max-w-[1600px] px-12 py-16">
            {children}
          </div>
        </div>
      </main>
    </div>
  )
}