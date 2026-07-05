import { Outlet, NavLink } from 'react-router-dom'
import { Film, History, LayoutDashboard, Zap } from 'lucide-react'
import clsx from 'clsx'

export default function Layout() {
  return (
    <div className="min-h-screen bg-cinema-black flex flex-col">
      {/* Top bar with film strip effect */}
      <div className="h-1 film-stripe w-full" />

      <nav className="bg-cinema-dark border-b border-cinema-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 rounded-lg bg-cinema-gold/10 border border-cinema-gold/30 flex items-center justify-center group-hover:bg-cinema-gold/20 transition-colors">
              <Film className="w-4 h-4 text-cinema-gold" />
            </div>
            <span className="font-display text-sm font-semibold tracking-wide text-cinema-text">
              IMAX<span className="text-cinema-gold">CONVERT</span>
            </span>
          </NavLink>

          {/* Nav links */}
          <div className="flex items-center gap-1">
            <NavLink
              to="/"
              end
              className={({ isActive }) => clsx(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all',
                isActive
                  ? 'bg-cinema-gold/10 text-cinema-gold border border-cinema-gold/20'
                  : 'text-cinema-text-dim hover:text-cinema-text hover:bg-cinema-card'
              )}
            >
              <Zap className="w-3.5 h-3.5" />
              Convert
            </NavLink>
            <NavLink
              to="/process"
              className={({ isActive }) => clsx(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all',
                isActive
                  ? 'bg-cinema-gold/10 text-cinema-gold border border-cinema-gold/20'
                  : 'text-cinema-text-dim hover:text-cinema-text hover:bg-cinema-card'
              )}
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              Dashboard
            </NavLink>
            <NavLink
              to="/history"
              className={({ isActive }) => clsx(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all',
                isActive
                  ? 'bg-cinema-gold/10 text-cinema-gold border border-cinema-gold/20'
                  : 'text-cinema-text-dim hover:text-cinema-text hover:bg-cinema-card'
              )}
            >
              <History className="w-3.5 h-3.5" />
              History
            </NavLink>
          </div>
        </div>
      </nav>

      <main className="flex-1">
        <Outlet />
      </main>

      {/* Bottom film strip */}
      <div className="h-1 film-stripe w-full opacity-50" />
    </div>
  )
}
