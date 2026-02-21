import { NavLink, Outlet } from 'react-router-dom'

const nav = [
  { to: '/', label: 'Dashboard' },
  { to: '/browser', label: 'Article Browser' },
  { to: '/queue', label: 'Review Queue' },
  { to: '/audit', label: 'Audit Log' },
  { to: '/settings', label: 'Settings' },
]

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      <nav className="w-52 bg-slate-800 text-white p-4 flex-shrink-0">
        <div className="flex flex-col items-center mb-4">
          <img src="/logo.png" alt="TDX KA Fixer" className="w-28 h-28 object-contain rounded-xl mb-2" />
          <h2 className="text-blue-400 mt-0 mb-0 text-sm font-semibold tracking-wide text-center">TDX KA Fixer</h2>
        </div>
        {nav.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `block px-3 py-2 rounded text-sm mb-1 no-underline transition-colors ${
                isActive
                  ? 'text-blue-400 bg-slate-900'
                  : 'text-slate-300 hover:text-white hover:bg-slate-700'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <main className="flex-1 p-6 bg-slate-50 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
