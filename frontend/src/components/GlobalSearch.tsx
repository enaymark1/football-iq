import { Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { logActivity } from "../hooks/useActivity";
import { useApi, useDebounced } from "../hooks/useApi";
import { api } from "../services/api";
import { positionLabel } from "../utils/format";
import { Avatar, cx } from "./ui";

export default function GlobalSearch() {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const dq = useDebounced(q.trim(), 220);
  const nav = useNavigate();
  const box = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const { data, loading } = useApi(() => api.search(dq), [dq], dq.length >= 2);

  const items = [
    ...(data?.players || []).map((p) => ({ key: `p${p.id}`, kind: "player" as const, id: p.id, name: p.name,
      sub: `${positionLabel(p.position)}${p.team_name ? ` · ${p.team_name}` : ""}`, image: p.image_url })),
    ...(data?.teams || []).map((t) => ({ key: `t${t.id}`, kind: "team" as const, id: t.id, name: t.name,
      sub: t.league_name || "", image: t.image_url })),
  ];

  useEffect(() => {
    const close = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false);
    const key = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        input.current?.focus();
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", key);
    };
  }, []);
  useEffect(() => setActive(0), [dq]);

  const go = (item: (typeof items)[number]) => {
    const path = item.kind === "player" ? `/players/${item.id}` : `/teams/${item.id}`;
    logActivity({ kind: "search", label: `Búsqueda: ${q.trim()}`, detail: item.name, path });
    setOpen(false);
    setQ("");
    nav(path);
  };

  return (
    <div ref={box} className="relative w-full max-w-md">
      <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
      <input ref={input} value={q} placeholder="Buscar jugadores o equipos…" aria-label="Búsqueda global"
        className="input pl-9 pr-14"
        onFocus={() => setOpen(true)}
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, items.length - 1)); }
          if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
          if (e.key === "Enter" && items[active]) go(items[active]);
          if (e.key === "Escape") setOpen(false);
        }} />
      <kbd className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-line px-1.5 font-mono text-[10px] text-faint sm:block">
        Ctrl K
      </kbd>
      {open && dq.length >= 2 && (
        <div className="absolute left-0 right-0 top-11 z-50 max-h-96 overflow-auto rounded-lg border border-line bg-panel p-1 shadow-2xl">
          {loading && <div className="px-3 py-2 text-xs text-muted">Buscando…</div>}
          {!loading && items.length === 0 && <div className="px-3 py-2 text-xs text-muted">Sin resultados para “{dq}”.</div>}
          {items.map((it, i) => (
            <button key={it.key} onMouseEnter={() => setActive(i)} onClick={() => go(it)}
              className={cx("flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left",
                i === active ? "bg-raised" : "hover:bg-raised/60")}>
              <Avatar name={it.name} src={it.image} size={26} tone={it.kind === "player" ? "default" : "team"} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm">{it.name}</span>
                <span className="block truncate text-[11px] text-muted">{it.sub}</span>
              </span>
              <span className="label text-[10px]">{it.kind === "player" ? "Jugador" : "Equipo"}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
