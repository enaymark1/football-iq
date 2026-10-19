import { useState } from "react";
import { Link } from "react-router-dom";
import { Avatar, Badge, Card, EmptyState, ErrorState, Field, Loading, PageHeader, Select } from "../components/ui";
import { useApi, useDebounced } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { api } from "../services/api";

export default function TeamsPage() {
  const meta = useMeta();
  const [league, setLeague] = useState("");
  const [q, setQ] = useState("");
  const [activeOnly, setActiveOnly] = useState(true);
  const dq = useDebounced(q, 250);
  const { data, error, loading, reload } = useApi(
    () => api.teams({ league_id: league || undefined, q: dq || undefined, active_only: activeOnly }), [league, dq, activeOnly]);
  const leagues = meta.data?.data.leagues || [];
  const byLeague = new Map<string, NonNullable<typeof data>>();
  (data || []).slice().sort((a, b) => (b.elo ?? 0) - (a.elo ?? 0)).forEach((t) => {
    const k = t.league_name || "Sin liga";
    byLeague.set(k, [...(byLeague.get(k) || []), t]);
  });

  return (
    <div className="space-y-5">
      <PageHeader title="Teams" subtitle="Equipos de las ligas importadas, ordenados por Elo dentro de cada liga (calculado solo con resultados de liga)." />
      <Card>
        <div className="grid gap-3 sm:grid-cols-[1fr_240px_auto] sm:items-end">
          <Field label="Buscar"><input className="input" placeholder="Nombre del equipo…" value={q} onChange={(e) => setQ(e.target.value)} /></Field>
          <Field label="Liga">
            <Select value={league} onChange={setLeague}>
              <option value="">Todas</option>
              {leagues.map((l) => <option key={l.id} value={l.id}>{l.name}{l.has_player_stats ? "" : " (solo resultados)"}</option>)}
            </Select>
          </Field>
          <label className="flex h-9 items-center gap-2 text-sm text-muted">
            <input type="checkbox" className="accent-[rgb(var(--accent))]" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} />
            Solo última temporada
          </label>
        </div>
      </Card>
      {error && <ErrorState error={error} onRetry={reload} />}
      {loading && !data && <Loading />}
      {data && data.length === 0 && <Card><EmptyState title="No hay equipos con esos filtros" /></Card>}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2 2xl:grid-cols-3">
        {Array.from(byLeague.entries()).map(([name, teams]) => (
          <Card key={name} title={
            <span className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded bg-white/90 p-0.5">
                <Avatar name={name} src={teams[0]?.league_image_url} size={20} tone="league" />
              </span>{name}
            </span>
          } subtitle={`${teams.length} equipos`} bodyClass="p-0 sm:p-0">
            <ol>
              {teams.map((t, i) => (
                <li key={t.id} className="border-b border-line/40 last:border-0">
                  <Link to={`/teams/${t.id}`} className="flex items-center gap-3 px-4 py-2 hover:bg-raised/40">
                    <span className="tabular w-5 text-right text-xs text-faint">{i + 1}</span>
                    <Avatar name={t.name} src={t.image_url} size={26} tone="team" />
                    <span className="min-w-0 flex-1 truncate text-sm">{t.name}</span>
                    {t.last_season != null && meta.data && t.last_season < Math.max(...leagues.map((l) => l.last_season ?? 0)) &&
                      <Badge>hasta {meta.seasonLabel(t.last_season)}</Badge>}
                    <span className="tabular text-xs text-muted">{t.elo ? t.elo.toFixed(0) : "—"}</span>
                  </Link>
                </li>
              ))}
            </ol>
          </Card>
        ))}
      </div>
    </div>
  );
}
