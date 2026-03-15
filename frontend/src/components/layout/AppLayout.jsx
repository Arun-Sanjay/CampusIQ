import { NavLink, Outlet } from 'react-router-dom'

import { primaryNavLinks } from '../../utils/navigation'

const baseLinkClasses =
  'rounded-full px-4 py-2 text-sm font-medium transition'

function AppLayout() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-stone-100">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-0 h-80 w-80 -translate-x-1/2 rounded-full bg-amber-200/30 blur-3xl" />
        <div className="absolute bottom-10 right-0 h-72 w-72 rounded-full bg-slate-300/20 blur-3xl" />
      </div>

      <div className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <header className="rounded-[2rem] border border-slate-200/70 bg-slate-950 px-5 py-4 shadow-[0_20px_60px_-35px_rgba(15,23,42,0.5)]">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-amber-200">
                CampusIQ
              </p>
              <p className="mt-2 max-w-xl text-sm text-slate-300">
                V1 scaffold for AI-assisted academic workflows across students,
                teachers, and admins.
              </p>
            </div>

            <nav className="flex flex-wrap gap-2">
              {primaryNavLinks.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) =>
                    `${baseLinkClasses} ${
                      isActive
                        ? 'bg-amber-100 text-slate-950 shadow-[0_14px_40px_-22px_rgba(251,191,36,0.35)]'
                        : 'bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-white'
                    }`
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </header>

        <main className="flex-1 py-8">
          <div className="rounded-[2rem] border border-stone-300/80 bg-stone-50 p-6 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.35)] sm:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default AppLayout
