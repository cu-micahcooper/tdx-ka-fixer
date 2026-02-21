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
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'sans-serif' }}>
      <nav style={{ width: 200, background: '#1e293b', color: '#fff', padding: 16, flexShrink: 0 }}>
        <h2 style={{ color: '#60a5fa', marginTop: 0, fontSize: 16 }}>TDX KA Fixer</h2>
        {nav.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              display: 'block',
              padding: '8px 12px',
              color: isActive ? '#60a5fa' : '#cbd5e1',
              textDecoration: 'none',
              borderRadius: 4,
              marginBottom: 4,
              background: isActive ? '#0f172a' : 'transparent',
              fontSize: 14,
            })}
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <main style={{ flex: 1, padding: 24, background: '#f8fafc', overflow: 'auto' }}>
        <Outlet />
      </main>
    </div>
  )
}
