import {
  Activity, BarChart3, Binoculars, CircleDollarSign, GitCompareArrows, LayoutDashboard, Menu, Shield, Sparkles, Target,
  Users, X,
} from "lucide-react";
import { Suspense, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import GlobalSearch from "../components/GlobalSearch";
import { cx, Loading } from "../components/ui";
import { APP_NAME, APP_TAGLINE } from "../config";
import { useMeta } from "../hooks/useMeta";
import { dateShort } from "../utils/format";

export const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/players", label: "Players", icon: Users },
  { to: "/compare", label: "Player Comparison", icon: GitCompareArrows },
  { to: "/scouting", label: "Scouting", icon: Binoculars },
  { to: "/similar", label: "Similar Players", icon: Sparkles },
  { to: "/market", label: "Market Opportunities", icon: CircleDollarSign },
  { to: "/match-predictor", label: "Match Predictor", icon: Target },
  { to: "/teams", label: "Teams", icon: Shield },
  { to: "/models", label: "Model Performance", icon: BarChart3 },
];

function Brand() {
  return (
    <div className="flex items-center gap-2.5 px-2">
      <span className="flex h-8 w-8 items-center justify-center rounded-md border border-accent/30 bg-accent/10">
        <Activity size={17} className="text-accent" />
      </span>
      <div className="leading-tight">
        <div className="text-[15px] font-bold tracking-tight">{APP_NAME}</div>
        <div className="text-[10px] uppercase tracking-[0.14em] text-faint">{APP_TAGLINE}</div>
      </div>
    </div>
  );
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { data } = useMeta();
  const d = data?.data;
  return (
    <div className="flex h-full flex-col">
      <div className="py-5"><Brand /></div>
      <nav className="flex-1 space-y-0.5" aria-label="Secciones">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} onClick={onNavigate}
            className={({ isActive }) => cx(
              "group flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] transition-colors",
              isActive ? "bg-raised text-ink shadow-[inset_2px_0_0_rgb(var(--accent))]" : "text-muted hover:bg-raised/50 hover:text-ink")}>
            {({ isActive }) => (
              <>
                <Icon size={16} className={isActive ? "text-accent" : "text-faint group-hover:text-muted"} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="mt-4 rounded-md border border-line/70 bg-bg/60 p-3 text-[11px] leading-relaxed text-muted">
        <div className="label mb-1 text-[10px]">Datos</div>
        {d?.imported ? (
          <>
            <div className="text-ink">{d.source}</div>
            <div>Partidos hasta {dateShort(d.date_range?.last_match)}</div>
            <div>Licencia {d.source_license}</div>
          </>
        ) : (
          <div>Sin datos importados</div>
        )}
      </div>
    </div>
  );
}

export default function AppLayout() {
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [loc.pathname]);
  return (
    <div className="min-h-full">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 border-r border-line/70 bg-panel/60 px-3 pb-4 lg:block">
        <Sidebar />
      </aside>
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 border-r border-line bg-panel px-3 pb-4">
            <button className="absolute right-2 top-5 p-2 text-muted" onClick={() => setOpen(false)} aria-label="Cerrar menú">
              <X size={18} />
            </button>
            <Sidebar onNavigate={() => setOpen(false)} />
          </aside>
        </div>
      )}
      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line/70 bg-bg/85 px-4 backdrop-blur sm:px-6">
          <button className="p-1.5 text-muted lg:hidden" onClick={() => setOpen(true)} aria-label="Abrir menú"><Menu size={19} /></button>
          <GlobalSearch />
        </header>
        <main className="mx-auto min-w-0 max-w-[1400px] overflow-x-clip px-4 py-6 sm:px-6">
          <Suspense fallback={<Loading />}><Outlet /></Suspense>
        </main>
      </div>
    </div>
  );
}
