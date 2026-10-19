import { Binoculars, CircleDollarSign, Clock, GitCompareArrows, Search, Shield, Sparkles, Target, Trash2, User, Users } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AXIS, GRID, tooltip } from "../components/charts";
import { Avatar, Card, EmptyState, ErrorState, Loading, Notice, PageHeader, ScorePill, Select, Stat } from "../components/ui";
import { useActivity, type ActivityItem } from "../hooks/useActivity";
import { useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { api } from "../services/api";
import type { TopPlayer } from "../types/api";
import { dec1, dec2, eur, int, pctRaw, positionLabel, timeAgo } from "../utils/format";

const ACTIVITY_ICON: Record<ActivityItem["kind"], typeof User> = {
  player: User, team: Shield, compare: GitCompareArrows, scouting: Binoculars, similar: Sparkles,
  market: CircleDollarSign, value: CircleDollarSign, match: Target, search: Search,
};

function TopList({ rows, metric }: { rows: TopPlayer[]; metric: "value" | "rating" }) {
  if (!rows.length) return <EmptyState title="Sin jugadores para mostrar" />;
  return (
    <ol className="divide-y divide-line/60">
      {rows.map((p, i) => (
        <li key={p.player_id} className="flex items-center gap-3 py-2">
          <span className="tabular w-4 text-right text-xs text-faint">{i + 1}</span>
          <Avatar name={p.name} src={p.image_url} size={28} />
          <div className="min-w-0 flex-1">
            <Link to={`/players/${p.player_id}`} className="link block truncate text-sm font-medium">{p.name}</Link>
            <div className="truncate text-[11px] text-muted">{positionLabel(p.position)} · {p.team_name}</div>
          </div>
          {metric === "value" ? (
            <span className="tabular text-sm font-semibold">{eur(p.market_value_eur)}</span>
          ) : (
            <div className="text-right">
              <ScorePill value={p.rating} />
              <div className="tabular mt-0.5 text-[11px] text-muted">{p.goals} G · {p.assists} A</div>
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}

function ActivityPanel() {
  const { items, clear } = useActivity();
  return (
    <Card title="Actividad reciente" subtitle="Búsquedas y análisis de esta sesión (solo en este navegador)"
      actions={items.length > 0 && (
        <button className="btn-ghost h-7 px-2 text-xs" onClick={clear}><Trash2 size={13} /> Limpiar</button>
      )}>
      {items.length === 0 ? (
        <EmptyState title="Todavía no hay actividad" icon={<Clock size={20} />}>
          Lo que busques, compares o analices durante la sesión va a aparecer acá.
        </EmptyState>
      ) : (
        <ul className="space-y-1">
          {items.slice(0, 8).map((a) => {
            const Icon = ACTIVITY_ICON[a.kind];
            return (
              <li key={`${a.kind}${a.path}${a.at}`}>
                <Link to={a.path} className="flex items-center gap-2.5 rounded-md px-2 py-1.5 hover:bg-raised">
                  <Icon size={14} className="shrink-0 text-faint" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm">{a.label}</span>
                    {a.detail && <span className="block truncate text-[11px] text-muted">{a.detail}</span>}
                  </span>
                  <span className="shrink-0 text-[11px] text-faint">{timeAgo(a.at)}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

export default function OverviewPage() {
  const [season, setSeason] = useState<number | undefined>();
  const { data, error, loading, reload } = useApi(() => api.overview(season), [season]);
  const meta = useMeta();

  if (error) return <><PageHeader title="Overview" /><ErrorState error={error} onRetry={reload} /></>;
  if (loading && !data) return <Loading label="Calculando indicadores" />;
  if (!data) return null;
  const k = data.kpis;
  const leaguesTotal = meta.data?.data.leagues.length ?? 0;

  return (
    <div className="space-y-5">
      <PageHeader title="Overview"
        subtitle={<>Temporada {data.season_label} · ligas domésticas con estadísticas de jugadores. Todo se calcula a partir de los datos importados.</>}
        actions={
          <Select ariaLabel="Temporada" value={data.season} onChange={(v) => setSeason(Number(v))} className="w-36">
            {data.available_seasons.map((s) => <option key={s.year} value={s.year}>{s.label}</option>)}
          </Select>
        } />

      {leaguesTotal > k.leagues_with_player_stats && (
        <Notice>
          La fuente trae estadísticas de jugadores para {k.leagues_with_player_stats} ligas y solo resultados de partidos
          para otras {leaguesTotal - k.leagues_with_player_stats} (Argentina, Brasil, MLS, etc.). Esas ligas están disponibles
          en Teams y Match Predictor, no en el análisis de jugadores.
        </Notice>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Jugadores" value={int(k.players)} icon={<Users size={15} />} hint={`${k.leagues_with_player_stats} ligas con estadísticas`} />
        <Stat label="Equipos" value={int(k.teams)} icon={<Shield size={15} />} hint={`${int(k.matches)} partidos de liga en la temporada`} />
        <Stat label="Edad promedio" value={dec1(k.average_age)} hint="Edad durante la temporada" />
        <Stat label="Valor de mercado total" value={eur(k.total_market_value_eur)}
          hint={`${int(k.players_with_market_value)} de ${int(k.players)} jugadores con valor registrado`} />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card title="Jugadores por posición" subtitle="Cantidad de jugadores con minutos en la temporada">
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={data.positions.map((p) => ({ ...p, label: positionLabel(p.position) }))} layout="vertical"
                margin={{ left: 8, right: 24 }} barCategoryGap={6}>
                <CartesianGrid {...GRID} horizontal={false} vertical />
                <XAxis type="number" {...AXIS} />
                <YAxis type="category" dataKey="label" width={104} {...AXIS} />
                <Tooltip cursor={{ fill: "rgb(255 255 255 / 0.03)" }}
                  content={tooltip((p) => ({ title: p[0].payload.label, rows: [{ label: "Jugadores", value: int(p[0].value) }] }))} />
                <Bar dataKey="players" fill="rgb(var(--accent))" radius={[0, 4, 4, 0]} maxBarSize={26} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Distribución por edad" subtitle="Tramos de 2 años">
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={data.age_distribution.map((a) => ({ ...a, start: a.range.split("-")[0] }))} margin={{ left: -12, right: 8 }} barCategoryGap={2}>
                <CartesianGrid {...GRID} />
                <XAxis dataKey="start" {...AXIS} fontSize={10} />
                <YAxis {...AXIS} />
                <Tooltip cursor={{ fill: "rgb(255 255 255 / 0.03)" }}
                  content={tooltip((p) => ({ title: `${p[0].payload.range} años`, rows: [{ label: "Jugadores", value: int(p[0].value) }] }))} />
                <Bar dataKey="players" fill="rgb(var(--accent))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2 2xl:grid-cols-3">
        <Card title="Mayor valor de mercado" subtitle="Último valor registrado en Transfermarkt">
          <TopList rows={data.top_market_value} metric="value" />
        </Card>
        <Card title="Mayor rendimiento estadístico" subtitle={`FIQ Rating · mínimo ${int(data.top_rating_min_minutes)} minutos`}>
          <TopList rows={data.top_rating} metric="rating" />
        </Card>
        <div className="lg:col-span-2 2xl:col-span-1"><ActivityPanel /></div>
      </div>

      <Card title="Comparación entre ligas" subtitle={`Temporada ${data.season_label} · ordenado por valor total del plantel analizado`} bodyClass="p-0 sm:p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="table-head border-b border-line/70">
                <th className="px-4 py-2.5">Liga</th>
                <th className="px-3 py-2.5 text-right">Jugadores</th>
                <th className="px-3 py-2.5 text-right">Edad prom.</th>
                <th className="px-3 py-2.5 text-right">Valor mediano</th>
                <th className="px-3 py-2.5">Valor total</th>
                <th className="px-3 py-2.5 text-right">Goles/partido</th>
                <th className="px-4 py-2.5 text-right">% victorias local</th>
              </tr>
            </thead>
            <tbody>
              {data.leagues.map((l) => {
                const max = data.leagues[0]?.total_market_value_eur || 1;
                return (
                  <tr key={l.league_id} className="border-b border-line/40 last:border-0 hover:bg-raised/40">
                    <td className="px-4 py-2 font-medium">
                      <span className="flex items-center gap-2">
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-white/90 p-0.5">
                          <Avatar name={l.league_name} src={l.image_url} size={20} tone="league" />
                        </span>{l.league_name}
                      </span>
                    </td>
                    <td className="tabular px-3 py-2 text-right text-muted">{int(l.players)}</td>
                    <td className="tabular px-3 py-2 text-right text-muted">{dec1(l.average_age)}</td>
                    <td className="tabular px-3 py-2 text-right text-muted">{eur(l.median_market_value_eur)}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-28 overflow-hidden rounded-full bg-raised">
                          <div className="h-full rounded-full bg-accent/80" style={{ width: `${((l.total_market_value_eur || 0) / max) * 100}%` }} />
                        </div>
                        <span className="tabular whitespace-nowrap text-xs">{eur(l.total_market_value_eur)}</span>
                      </div>
                    </td>
                    <td className="tabular px-3 py-2 text-right">{dec2(l.goals_per_match)}</td>
                    <td className="tabular px-4 py-2 text-right">{pctRaw(l.home_win_pct, 1)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card title="Evolución: goles por partido" subtitle={data.evolution_note}>
          {data.evolution.length < 2 ? <EmptyState title="No hay suficientes temporadas para mostrar una evolución" /> : (
            <div className="h-56">
              <ResponsiveContainer>
                <LineChart data={data.evolution} margin={{ left: -8, right: 12, top: 8 }}>
                  <CartesianGrid {...GRID} />
                  <XAxis dataKey="season_label" {...AXIS} fontSize={10} />
                  <YAxis {...AXIS} domain={["dataMin - 0.1", "dataMax + 0.1"]} tickFormatter={(v) => v.toFixed(2)} />
                  <Tooltip content={tooltip((p) => ({ title: p[0].payload.season_label,
                    rows: [{ label: "Goles por partido", value: dec2(p[0].value) }, { label: "Partidos", value: int(p[0].payload.matches) }] }))} />
                  <Line dataKey="goals_per_match" stroke="rgb(var(--accent))" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
        <Card title="Evolución: ventaja de local" subtitle="% de partidos ganados por el local (2020/21 se jugó mayormente sin público)">
          {data.evolution.length < 2 ? <EmptyState title="No hay suficientes temporadas" /> : (
            <div className="h-56">
              <ResponsiveContainer>
                <LineChart data={data.evolution} margin={{ left: -8, right: 12, top: 8 }}>
                  <CartesianGrid {...GRID} />
                  <XAxis dataKey="season_label" {...AXIS} fontSize={10} />
                  <YAxis {...AXIS} domain={["dataMin - 2", "dataMax + 2"]} tickFormatter={(v) => `${v.toFixed(0)}%`} />
                  <Tooltip content={tooltip((p) => ({ title: p[0].payload.season_label,
                    rows: [{ label: "Victorias local", value: pctRaw(p[0].value, 1) }, { label: "Empates", value: pctRaw(p[0].payload.draw_pct, 1) }] }))} />
                  <Line dataKey="home_win_pct" stroke="var(--series-1)" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
