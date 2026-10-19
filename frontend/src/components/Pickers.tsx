import { Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useApi, useDebounced } from "../hooks/useApi";
import { api } from "../services/api";
import type { TeamListItem } from "../types/api";
import { positionLabel } from "../utils/format";
import { Avatar, cx } from "./ui";

export interface PickedPlayer { id: number; name: string; sub?: string }

/** Buscador de jugadores para elegir uno (comparador, similares, valor). */
export function PlayerPicker({ onPick, exclude = [], placeholder = "Buscar jugador…", disabled }: {
  onPick: (p: PickedPlayer) => void; exclude?: number[]; placeholder?: string; disabled?: boolean;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const dq = useDebounced(q.trim(), 220);
  const ref = useRef<HTMLDivElement>(null);
  const { data, loading } = useApi(() => api.search(dq), [dq], dq.length >= 2);
  useEffect(() => {
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  const players = (data?.players || []).filter((p) => !exclude.includes(p.id));
  return (
    <div ref={ref} className="relative">
      <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
      <input className="input pl-8" value={q} disabled={disabled} placeholder={placeholder} aria-label={placeholder}
        onFocus={() => setOpen(true)} onChange={(e) => { setQ(e.target.value); setOpen(true); }} />
      {open && dq.length >= 2 && (
        <div className="absolute left-0 right-0 top-10 z-40 max-h-72 overflow-auto rounded-lg border border-line bg-panel p-1 shadow-2xl">
          {loading && <div className="px-3 py-2 text-xs text-muted">Buscando…</div>}
          {!loading && players.length === 0 && <div className="px-3 py-2 text-xs text-muted">Sin resultados.</div>}
          {players.map((p) => (
            <button key={p.id} className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left hover:bg-raised"
              onClick={() => {
                onPick({ id: p.id, name: p.name, sub: `${positionLabel(p.position)} · ${p.team_name ?? "sin club"}` });
                setQ("");
                setOpen(false);
              }}>
              <Avatar name={p.name} src={p.image_url} size={24} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm">{p.name}</span>
                <span className="block truncate text-[11px] text-muted">{positionLabel(p.position)} · {p.team_name ?? "sin club"}</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** Selector de equipo con filtro por texto, agrupado por liga. */
export function TeamSelect({ teams, value, onChange, label }: {
  teams: TeamListItem[]; value: number | null; onChange: (id: number) => void; label: string;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  const selected = teams.find((t) => t.id === value);
  const filtered = teams.filter((t) => `${t.name} ${t.league_name}`.toLowerCase().includes(q.toLowerCase())).slice(0, 60);
  return (
    <div ref={ref} className="relative">
      <button type="button" aria-label={label} onClick={() => setOpen((o) => !o)}
        className={cx("input flex items-center justify-between text-left", !selected && "text-faint")}>
        <span className="truncate">{selected ? selected.name : "Elegir equipo…"}</span>
        <span className="ml-2 truncate text-[11px] text-muted">{selected?.league_name}</span>
      </button>
      {open && (
        <div className="absolute left-0 right-0 top-10 z-40 rounded-lg border border-line bg-panel p-1 shadow-2xl">
          <input autoFocus className="input mb-1" placeholder="Filtrar por equipo o liga…" value={q} onChange={(e) => setQ(e.target.value)} />
          <div className="max-h-72 overflow-auto">
            {filtered.map((t) => (
              <button key={t.id} onClick={() => { onChange(t.id); setOpen(false); setQ(""); }}
                className={cx("flex w-full items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-left text-sm hover:bg-raised",
                  t.id === value && "bg-raised")}>
                <span className="flex min-w-0 items-center gap-2"><Avatar name={t.name} src={t.image_url} size={18} tone="team" /><span className="truncate">{t.name}</span></span>
                <span className="shrink-0 text-[11px] text-muted">{t.league_name}</span>
              </button>
            ))}
            {filtered.length === 0 && <div className="px-3 py-2 text-xs text-muted">Sin resultados.</div>}
          </div>
        </div>
      )}
    </div>
  );
}
