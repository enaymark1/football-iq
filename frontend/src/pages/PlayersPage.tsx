import { ArrowDown, ArrowUp, RotateCcw, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Avatar, Badge, Card, cx, EmptyState, ErrorState, Field, Loading, NumberInput, PageHeader, Pagination, ScorePill, Select } from "../components/ui";
import { useApi, useDebounced } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { api } from "../services/api";
import { dec1, dec2, eur, int, POSITION_SHORT } from "../utils/format";

const NUMERIC_FILTERS = [
  ["age_min", "Edad mín."], ["age_max", "Edad máx."], ["value_min", "Valor mín. (M€)"], ["value_max", "Valor máx. (M€)"],
  ["minutes_min", "Minutos mín."], ["goals_min", "Goles mín."], ["assists_min", "Asist. mín."], ["rating_min", "Rating mín."],
] as const;

const COLUMNS: { key: string; label: string; sort?: string; align?: "right"; hideSm?: boolean }[] = [
  { key: "name", label: "Jugador", sort: "name" },
  { key: "age", label: "Edad", sort: "age", align: "right" },
  { key: "nationality", label: "Nacionalidad", hideSm: true },
  { key: "position", label: "Pos." },
  { key: "team", label: "Club / Liga", hideSm: true },
  { key: "matches", label: "PJ", sort: "matches", align: "right" },
  { key: "minutes", label: "Min.", sort: "minutes", align: "right" },
  { key: "goals", label: "G", sort: "goals", align: "right" },
  { key: "assists", label: "A", sort: "assists", align: "right" },
  { key: "goals_p90", label: "G/90", sort: "goals_p90", align: "right", hideSm: true },
  { key: "value", label: "Valor", sort: "market_value_eur", align: "right" },
  { key: "rating", label: "Rating", sort: "rating", align: "right" },
];

export default function PlayersPage() {
  const [sp, setSp] = useSearchParams();
  const meta = useMeta();
  const [showFilters, setShowFilters] = useState(true);
  const get = (k: string) => sp.get(k) ?? "";
  const set = (patch: Record<string, string | number | "">) => {
    const next = new URLSearchParams(sp);
    Object.entries(patch).forEach(([k, v]) => (v === "" ? next.delete(k) : next.set(k, String(v))));
    if (!("page" in patch)) next.delete("page");
    setSp(next, { replace: true });
  };
  const q = useDebounced(get("q"), 300);
  const season = get("season");
  const sortBy = get("sort_by") || "rating";
  const sortDir = get("sort_dir") || "desc";
  const page = Number(get("page") || 1);
  const millions = (v: string) => (v === "" ? undefined : Number(v) * 1e6);

  const params = {
    season: season || undefined, q: q || undefined, position: get("position") || undefined,
    league_id: get("league_id") || undefined, team_id: get("team_id") || undefined, nationality: get("nationality") || undefined,
    age_min: get("age_min") || undefined, age_max: get("age_max") || undefined,
    value_min: millions(get("value_min")), value_max: millions(get("value_max")),
    minutes_min: get("minutes_min") || undefined, goals_min: get("goals_min") || undefined,
    assists_min: get("assists_min") || undefined, rating_min: get("rating_min") || undefined,
    sort_by: sortBy, sort_dir: sortDir, page, page_size: 25,
  };
  const { data, error, loading, reload } = useApi(() => api.players(params), [JSON.stringify(params)]);
  const filters = useApi(() => api.playerFilters(season ? Number(season) : undefined), [season]);
  const teams = useApi(() => api.teams({ league_id: get("league_id"), active_only: false }), [get("league_id")], !!get("league_id"));

  const toggleSort = (key: string) =>
    set(sortBy === key ? { sort_dir: sortDir === "desc" ? "asc" : "desc" } : { sort_by: key, sort_dir: key === "name" || key === "age" ? "asc" : "desc" });
  const activeFilters = Array.from(sp.keys()).filter((k) => !["sort_by", "sort_dir", "page", "season"].includes(k)).length;

  return (
    <div className="space-y-4">
      <PageHeader title="Players"
        subtitle="Estadísticas de liga por temporada. El rating es el FIQ Rating: percentil por posición dentro de su liga, ajustado por minutos."
        actions={<>
          <Select ariaLabel="Temporada" className="w-32" value={season || meta.data?.data.player_seasons.at(-1) || ""}
            onChange={(v) => set({ season: v })}>
            {(meta.data?.data.player_seasons || []).slice().reverse().map((s) => <option key={s} value={s}>{meta.seasonLabel(s)}</option>)}
          </Select>
          <button className="btn-ghost" onClick={() => setShowFilters((s) => !s)}>
            <SlidersHorizontal size={14} /> Filtros {activeFilters > 0 && <Badge tone="accent">{activeFilters}</Badge>}
          </button>
        </>} />

      {showFilters && (
        <Card>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6">
            <div className="col-span-2">
              <Field label="Nombre">
                <input className="input" placeholder="Buscar por nombre…" value={get("q")} onChange={(e) => set({ q: e.target.value })} />
              </Field>
            </div>
            <Field label="Posición">
              <Select value={get("position")} onChange={(v) => set({ position: v })}>
                <option value="">Todas</option>
                {(meta.data?.positions || []).map((p) => <option key={p} value={p}>{POSITION_SHORT[p]} · {p}</option>)}
              </Select>
            </Field>
            <Field label="Liga">
              <Select value={get("league_id")} onChange={(v) => set({ league_id: v, team_id: "" })}>
                <option value="">Todas</option>
                {meta.playerLeagues.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </Select>
            </Field>
            <Field label="Club">
              <Select value={get("team_id")} onChange={(v) => set({ team_id: v })}>
                <option value="">{get("league_id") ? "Todos" : "Elegí una liga"}</option>
                {(teams.data || []).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </Select>
            </Field>
            <Field label="Nacionalidad">
                <Select value={get("nationality")} onChange={(v) => set({ nationality: v })}>
                  <option value="">Todas</option>
                  {(filters.data?.nationalities || []).map((n) => <option key={n} value={n}>{n}</option>)}
                </Select>
              </Field>
            {NUMERIC_FILTERS.map(([key, label]) => (
              <Field key={key} label={label}>
                <NumberInput value={get(key) === "" ? "" : Number(get(key))} min={0} onChange={(v) => set({ [key]: v })} />
              </Field>
            ))}
            <div className="col-span-2 flex items-end">
              <button className="btn-ghost w-full" disabled={activeFilters === 0}
                onClick={() => setSp(new URLSearchParams(season ? { season } : {}), { replace: true })}>
                <RotateCcw size={14} /> Limpiar filtros
              </button>
            </div>
          </div>
          <p className="mt-3 text-[11px] text-faint">Los filtros se combinan entre sí. Valor = último valor registrado en Transfermarkt.</p>
        </Card>
      )}

      {error ? <ErrorState error={error} onRetry={reload} /> : (
        <section className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead>
                <tr className="table-head border-b border-line/70">
                  {COLUMNS.map((c) => (
                    <th key={c.key} className={cx("px-3 py-2.5 first:pl-4", c.align === "right" && "text-right", c.hideSm && "hidden md:table-cell")}>
                      {c.sort ? (
                        <button onClick={() => toggleSort(c.sort!)} className={cx("inline-flex items-center gap-1 uppercase hover:text-ink",
                          sortBy === c.sort && "text-ink")}>
                          {c.label}
                          {sortBy === c.sort && (sortDir === "desc" ? <ArrowDown size={11} /> : <ArrowUp size={11} />)}
                        </button>
                      ) : c.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className={cx(loading && "opacity-50 transition-opacity")}>
                {data?.items.map((p) => (
                  <tr key={p.player_id} className="border-b border-line/40 last:border-0 hover:bg-raised/40">
                    <td className="py-2 pl-4 pr-3">
                      <Link to={`/players/${p.player_id}`} className="flex items-center gap-2.5">
                        <Avatar name={p.name} src={p.image_url} size={28} />
                        <span className="link font-medium">{p.name}</span>
                      </Link>
                    </td>
                    <td className="tabular px-3 py-2 text-right">{dec1(p.age)}</td>
                    <td className="hidden max-w-[130px] truncate px-3 py-2 text-muted md:table-cell">{p.nationality ?? "—"}</td>
                    <td className="px-3 py-2">{p.position ? <Badge>{POSITION_SHORT[p.position]}</Badge> : "—"}</td>
                    <td className="hidden max-w-[220px] px-3 py-2 md:table-cell">
                      {p.team_id ? (
                        <Link to={`/teams/${p.team_id}`} className="link flex items-center gap-1.5 truncate">
                          <Avatar name={p.team_name ?? ""} src={p.team_image_url} size={16} tone="team" />
                          <span className="truncate">{p.team_name}</span>
                        </Link>
                      ) : "—"}
                      <div className="truncate text-[11px] text-muted">{p.league_name}</div>
                    </td>
                    <td className="tabular px-3 py-2 text-right text-muted">{p.matches}</td>
                    <td className="tabular px-3 py-2 text-right text-muted">{int(p.minutes)}</td>
                    <td className="tabular px-3 py-2 text-right">{p.goals}</td>
                    <td className="tabular px-3 py-2 text-right">{p.assists}</td>
                    <td className="tabular hidden px-3 py-2 text-right text-muted md:table-cell">{dec2(p.goals_p90)}</td>
                    <td className="tabular px-3 py-2 text-right">{eur(p.market_value_eur)}</td>
                    <td className="px-3 py-2 pr-4 text-right"
                      title={p.rating_reliability != null ? `Confianza por minutos: ${Math.round(p.rating_reliability * 100)}%` : undefined}>
                      <ScorePill value={p.rating} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {loading && !data && <Loading />}
          {data && data.items.length === 0 && <EmptyState title="Ningún jugador cumple esos filtros">Probá ampliando los rangos.</EmptyState>}
          {data && data.total > 0 && <Pagination page={data.page} pages={data.pages} total={data.total} onPage={(p) => set({ page: p })} />}
        </section>
      )}
    </div>
  );
}
