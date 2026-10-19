import { AlertTriangle, ChevronLeft, ChevronRight, Database, Info, Loader2, RotateCw } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { SHOW_IMAGES } from "../config";
import type { ApiError } from "../services/api";
import { initials } from "../utils/format";

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{title}</h1>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ title, subtitle, actions, children, className, bodyClass }: {
  title?: ReactNode; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; bodyClass?: string;
}) {
  return (
    <section className={cx("card animate-fadein", className)}>
      {(title || actions) && (
        <header className="flex items-start justify-between gap-3 border-b border-line/70 px-4 py-3 sm:px-5">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-semibold">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      <div className={cx("card-pad", bodyClass)}>{children}</div>
    </section>
  );
}

export function Stat({ label, value, hint, icon }: { label: string; value: ReactNode; hint?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="card card-pad animate-fadein">
      <div className="flex items-center justify-between">
        <span className="label">{label}</span>
        {icon && <span className="text-faint">{icon}</span>}
      </div>
      <div className="tabular mt-2 text-2xl font-semibold tracking-tight">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}

type Tone = "neutral" | "accent" | "good" | "warning" | "serious" | "critical" | "info";
const TONES: Record<Tone, string> = {
  neutral: "border-line bg-raised text-muted",
  accent: "border-accent/30 bg-accent/10 text-accent",
  good: "border-good/40 bg-good/10 text-[#5fd35f]",
  warning: "border-warning/40 bg-warning/10 text-warning",
  serious: "border-serious/40 bg-serious/10 text-serious",
  critical: "border-critical/50 bg-critical/10 text-[#f08080]",
  info: "border-[#3987e5]/40 bg-[#3987e5]/10 text-[#7fb2ef]",
};

export function Badge({ children, tone = "neutral", className }: { children: ReactNode; tone?: Tone; className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded border px-1.5 py-0.5 text-[11px] font-medium", TONES[tone], className)}>
      {children}
    </span>
  );
}

export function Notice({ children, tone = "info", title }: { children: ReactNode; tone?: "info" | "warning"; title?: string }) {
  const Icon = tone === "warning" ? AlertTriangle : Info;
  return (
    <div className={cx("flex gap-2.5 rounded-md border px-3 py-2.5 text-xs leading-relaxed",
      tone === "warning" ? "border-warning/30 bg-warning/[0.06] text-[#f3cf7a]" : "border-line bg-raised/50 text-muted")}>
      <Icon size={15} className="mt-0.5 shrink-0" aria-hidden />
      <div>{title && <div className="mb-0.5 font-semibold text-ink">{title}</div>}{children}</div>
    </div>
  );
}

export function EmptyState({ title, children, icon }: { title: string; children?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-10 text-center">
      <div className="mb-3 text-faint">{icon ?? <Database size={22} />}</div>
      <div className="text-sm font-medium">{title}</div>
      {children && <div className="mt-1 max-w-md text-xs text-muted">{children}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  const hint =
    error.status === 409 ? "Importá los datos con: python scripts/import_data.py"
      : error.status === 503 ? "Entrená los modelos con: python scripts/train_models.py"
        : error.status === 0 ? "Iniciá el backend (ver README) y volvé a intentar." : null;
  return (
    <div className="card flex flex-col items-center px-6 py-10 text-center">
      <AlertTriangle className="mb-3 text-warning" size={22} />
      <div className="text-sm font-medium">{error.message}</div>
      {hint && <code className="mt-2 rounded bg-raised px-2 py-1 font-mono text-xs text-muted">{hint}</code>}
      {onRetry && (
        <button className="btn-ghost mt-4" onClick={onRetry}><RotateCw size={14} /> Reintentar</button>
      )}
    </div>
  );
}

export function Loading({ label = "Cargando" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted">
      <Loader2 className="animate-spin" size={16} /> {label}…
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-pulse rounded bg-raised", className)} />;
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="label mb-1.5 block">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-faint">{hint}</span>}
    </label>
  );
}

export function Select({ value, onChange, children, className, ariaLabel }: {
  value: string | number; onChange: (v: string) => void; children: ReactNode; className?: string; ariaLabel?: string;
}) {
  return (
    <select aria-label={ariaLabel} className={cx("input appearance-none pr-8", className)} value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{ backgroundImage: "linear-gradient(45deg,transparent 50%,#8b929c 50%),linear-gradient(135deg,#8b929c 50%,transparent 50%)",
        backgroundPosition: "calc(100% - 16px) 15px, calc(100% - 11px) 15px", backgroundSize: "5px 5px", backgroundRepeat: "no-repeat" }}>
      {children}
    </select>
  );
}

export function NumberInput({ value, onChange, placeholder, min, max, step }: {
  value: number | "" ; onChange: (v: number | "") => void; placeholder?: string; min?: number; max?: number; step?: number;
}) {
  return (
    <input type="number" className="input tabular" value={value} placeholder={placeholder} min={min} max={max} step={step}
      onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))} />
  );
}

export function Pagination({ page, pages, total, onPage }: { page: number; pages: number; total: number; onPage: (p: number) => void }) {
  return (
    <div className="flex items-center justify-between gap-3 border-t border-line/70 px-4 py-3 text-xs text-muted">
      <span className="tabular">{total.toLocaleString("es-AR")} resultados · página {page} de {pages}</span>
      <div className="flex gap-1.5">
        <button className="btn-ghost h-8 px-2" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Página anterior">
          <ChevronLeft size={15} />
        </button>
        <button className="btn-ghost h-8 px-2" disabled={page >= pages} onClick={() => onPage(page + 1)} aria-label="Página siguiente">
          <ChevronRight size={15} />
        </button>
      </div>
    </div>
  );
}

/** Foto de jugador (recortada en círculo) o escudo/logo (contenido entero). Sin imagen o si falla: iniciales. */
export function Avatar({ name, src, size = 32, tone = "default" }: {
  name: string; src?: string | null; size?: number; tone?: "default" | "team" | "league";
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [src]);
  const showImg = SHOW_IMAGES && !!src && !failed;
  if (showImg && tone !== "default") {
    return (
      <img src={src!} alt="" aria-hidden width={size} height={size} loading="lazy" referrerPolicy="no-referrer"
        onError={() => setFailed(true)} className="shrink-0 object-contain" style={{ width: size, height: size }} />
    );
  }
  return (
    <span aria-hidden className={cx("inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full border font-semibold",
      tone === "default" ? "border-line bg-raised text-ink" : "border-line bg-bg text-muted")}
      style={{ width: size, height: size, fontSize: Math.max(10, size * 0.36) }}>
      {showImg ? (
        <img src={src!} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setFailed(true)}
          className="h-full w-full object-cover object-top" />
      ) : initials(name)}
    </span>
  );
}

/** Barra de percentil 0-100 con marca de la mediana (50). */
export function PercentileBar({ value, className }: { value: number | null; className?: string }) {
  if (value == null) return <span className="text-xs text-faint">sin dato</span>;
  const tone = value >= 75 ? "bg-accent" : value >= 40 ? "bg-[#8b929c]" : "bg-serious";
  return (
    <div className={cx("flex items-center gap-2", className)}>
      <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-raised">
        <div className={cx("h-full rounded-full", tone)} style={{ width: `${Math.max(2, value)}%` }} />
        <div className="absolute inset-y-0 left-1/2 w-px bg-line" />
      </div>
      <span className="tabular w-7 text-right text-xs text-muted">{Math.round(value)}</span>
    </div>
  );
}

export function UncertaintyBadge({ level }: { level: "baja" | "media" | "alta" }) {
  const tone = level === "baja" ? "good" : level === "media" ? "warning" : "critical";
  return <Badge tone={tone}><AlertTriangle size={11} className={level === "baja" ? "hidden" : ""} />Incertidumbre {level}</Badge>;
}

export function ScorePill({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="text-faint">—</span>;
  return (
    <span className="tabular inline-flex min-w-[42px] justify-center rounded border border-accent/30 bg-accent/10 px-1.5 py-0.5 text-xs font-semibold text-accent">
      {value.toFixed(1)}
    </span>
  );
}

export function Tabs<T extends string>({ value, onChange, options }: {
  value: T; onChange: (v: T) => void; options: { value: T; label: string }[];
}) {
  return (
    <div role="tablist" className="inline-flex rounded-md border border-line bg-bg p-0.5">
      {options.map((o) => (
        <button key={o.value} role="tab" aria-selected={value === o.value} onClick={() => onChange(o.value)}
          className={cx("rounded px-3 py-1.5 text-xs font-medium transition-colors",
            value === o.value ? "bg-raised text-ink" : "text-muted hover:text-ink")}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
