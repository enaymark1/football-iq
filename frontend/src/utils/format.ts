import type { MetricDef, Position } from "../types/api";

const nf0 = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2, minimumFractionDigits: 2 });

export const DASH = "—";

export function eur(v: number | null | undefined, compact = true): string {
  if (v == null || Number.isNaN(v)) return DASH;
  if (!compact) return `${nf0.format(v)} €`;
  if (Math.abs(v) >= 1e9) return `${nf2.format(v / 1e9)} B€`;
  if (Math.abs(v) >= 1e6) return `${nf1.format(v / 1e6)} M€`;
  if (Math.abs(v) >= 1e3) return `${nf0.format(v / 1e3)} k€`;
  return `${nf0.format(v)} €`;
}

export const int = (v: number | null | undefined) => (v == null ? DASH : nf0.format(v));
export const dec1 = (v: number | null | undefined) => (v == null ? DASH : nf1.format(v));
export const dec2 = (v: number | null | undefined) => (v == null ? DASH : nf2.format(v));
export const pct = (v: number | null | undefined, digits = 0) =>
  v == null ? DASH : `${(v * 100).toFixed(digits).replace(".", ",")}%`;
export const pctRaw = (v: number | null | undefined, digits = 0) =>
  v == null ? DASH : `${v.toFixed(digits).replace(".", ",")}%`;

/** Formatea un valor según la unidad de la métrica. */
export function metricValue(v: number | null | undefined, unit: MetricDef["unit"] | undefined): string {
  if (v == null) return DASH;
  switch (unit) {
    case "eur":
      return eur(v);
    case "ratio":
      return pct(v, 0);
    case "p90":
    case "per_match":
      return dec2(v);
    case "years":
      return dec1(v);
    default:
      return int(v);
  }
}

export const POSITION_LABEL: Record<Position, string> = {
  Goalkeeper: "Arquero",
  Defender: "Defensor",
  Midfield: "Mediocampista",
  Attack: "Delantero",
};
export const POSITION_SHORT: Record<Position, string> = { Goalkeeper: "ARQ", Defender: "DEF", Midfield: "MED", Attack: "DEL" };

export const positionLabel = (p: string | null | undefined) =>
  p ? POSITION_LABEL[p as Position] ?? p : "Sin dato";

export function initials(name: string): string {
  const parts = name.replace(/[^\p{L}\s-]/gu, "").split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] || "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

export function dateShort(iso: string | null | undefined): string {
  if (!iso) return DASH;
  const d = new Date(iso.length === 10 ? `${iso}T12:00:00` : iso);
  return d.toLocaleDateString("es-AR", { day: "2-digit", month: "short", year: "numeric" });
}

export function timeAgo(ts: number): string {
  const s = Math.round((Date.now() - ts) / 1000);
  if (s < 60) return "recién";
  if (s < 3600) return `hace ${Math.floor(s / 60)} min`;
  return `hace ${Math.floor(s / 3600)} h`;
}
