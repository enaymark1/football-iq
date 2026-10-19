// Piezas compartidas de los gráficos: tooltip, ejes y grilla con estilo recesivo.
import type { ReactNode } from "react";

export const AXIS = { stroke: "var(--grid)", tickLine: false, axisLine: false } as const;
export const GRID = { stroke: "var(--grid)", vertical: false } as const; // líneas sólidas, nunca punteadas

interface TooltipRow { label: string; value: ReactNode; color?: string }

export function TooltipBox({ title, rows }: { title?: ReactNode; rows: TooltipRow[] }) {
  return (
    <div className="min-w-[150px] rounded-md border border-line bg-[#0e1013] px-3 py-2 text-xs shadow-xl">
      {title && <div className="mb-1 font-semibold text-ink">{title}</div>}
      {rows.map((r, i) => (
        <div key={i} className="flex items-center justify-between gap-4 py-0.5">
          <span className="flex items-center gap-1.5 text-muted">
            {r.color && <span className="h-2 w-2 rounded-full" style={{ background: r.color }} />}
            {r.label}
          </span>
          <span className="tabular font-medium text-ink">{r.value}</span>
        </div>
      ))}
    </div>
  );
}

/** Adaptador para el prop `content` de <Tooltip> de Recharts. */
export function tooltip(render: (payload: any, label: any) => { title?: ReactNode; rows: TooltipRow[] } | null) {
  return ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const r = render(payload, label);
    return r ? <TooltipBox {...r} /> : null;
  };
}

export function Legend({ items }: { items: { label: string; color: string }[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted">
      {items.map((i) => (
        <span key={i.label} className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: i.color }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}
