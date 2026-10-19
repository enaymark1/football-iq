import { ArrowLeft, Target } from "lucide-react";
import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AXIS, GRID, tooltip } from "../components/charts";
import { Avatar, Badge, Card, cx, EmptyState, ErrorState, Loading, Notice, ScorePill, Stat } from "../components/ui";
import { logActivity } from "../hooks/useActivity";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import type { TeamSeasonSummary } from "../types/api";
import { dateShort, dec1, dec2, eur, int, POSITION_SHORT } from "../utils/format";

function Split({ title, s }: { title: string; s: TeamSeasonSummary }) {
  return (
    <div className="rounded-md border border-line bg-bg/60 p-3">
      <div className="label">{title}</div>
      <div className="tabular mt-1 text-lg font-semibold">{s.wins}-{s.draws}-{s.losses}</div>
      <div className="tabular text-xs text-muted">{dec2(s.points_per_match)} pts/partido · GF {dec2(s.goals_for_pm)} · GC {dec2(s.goals_against_pm)}</div>
    </div>
  );
}

export default function TeamDetailPage() {
  const { id } = useParams();
  const tid = Number(id);
  const nav = useNavigate();
  const { data, error, loading, reload } = useApi(() => api.team(tid), [tid]);
  useEffect(() => {
    if (data) logActivity({ kind: "team", label: data.team.name, detail: data.team.league_name ?? undefined, path: `/teams/${tid}` });
  }, [data?.team.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (loading || !data) return <Loading label="Cargando equipo" />;
  const t = data.team;
  const latest = data.seasons.at(-1);
  const elo = (data.elo_history || []).map((e) => ({ ...e, ts: new Date(e.date).getTime() }));

  return (
    <div className="space-y-5">
      <button className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-ink" onClick={() => nav(-1)}><ArrowLeft size={14} /> Volver</button>
      <section className="card card-pad flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Avatar name={t.name} src={t.image_url} size={60} tone="team" />
          <div>
            <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{t.name}</h1>
            <div className="mt-1 flex flex-wrap gap-x-3 text-sm text-muted">
              <span>{t.league_name}</span>{t.country && <span>{t.country}</span>}
              {t.stadium && <span>{t.stadium}{t.stadium_seats ? ` (${int(t.stadium_seats)})` : ""}</span>}
            </div>
          </div>
        </div>
        <Link to="/match-predictor" className="btn-ghost"><Target size={14} /> Predecir un partido</Link>
      </section>

      {latest && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat label={`Récord ${latest.season_label}`} value={`${latest.wins}-${latest.draws}-${latest.losses}`} hint={`${latest.matches} partidos`} />
          <Stat label="Puntos" value={latest.points} hint={`${dec2(latest.points_per_match)} por partido`} />
          <Stat label="Goles" value={`${latest.goals_for} : ${latest.goals_against}`} hint="a favor : en contra" />
          <Stat label="Elo actual" value={data.current_elo ? data.current_elo.toFixed(0) : "—"} hint="Relativo a su liga" />
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2" title="Evolución del Elo" subtitle="Últimos 200 partidos de liga · calculado solo con resultados anteriores a cada partido">
          {elo.length < 2 ? <EmptyState title="Sin historial suficiente (entrená los modelos)" /> : (
            <div className="h-60">
              <ResponsiveContainer>
                <LineChart data={elo} margin={{ left: -6, right: 10, top: 6 }}>
                  <CartesianGrid {...GRID} />
                  <XAxis dataKey="ts" type="number" scale="time" domain={["dataMin", "dataMax"]} {...AXIS} fontSize={10}
                    tickCount={6} tickFormatter={(v) => new Date(v).toLocaleDateString("es-AR", { month: "short", year: "2-digit" })} />
                  <YAxis {...AXIS} fontSize={10} domain={["dataMin - 20", "dataMax + 20"]} tickFormatter={(v) => v.toFixed(0)} />
                  <Tooltip content={tooltip((p) => ({ title: dateShort(p[0].payload.date), rows: [{ label: "Elo", value: p[0].value.toFixed(0) }] }))} />
                  <Line dataKey="elo" stroke="rgb(var(--accent))" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>
        <Card title="Forma reciente" subtitle="Últimos 10 partidos de liga">
          {data.latest_splits && (
            <div className="mb-4 grid grid-cols-2 gap-2">
              <Split title="Local (últ. temp.)" s={data.latest_splits.home} />
              <Split title="Visitante (últ. temp.)" s={data.latest_splits.away} />
            </div>
          )}
          <ul className="space-y-1">
            {data.recent_matches.map((m, i) => (
              <li key={i} className="flex items-center gap-2 text-sm">
                <span className={cx("flex h-5 w-5 shrink-0 items-center justify-center rounded text-[10px] font-bold",
                  m.result === "W" ? "bg-good/20 text-[#5fd35f]" : m.result === "D" ? "bg-raised text-muted" : "bg-critical/20 text-[#f08080]")}>
                  {m.result === "W" ? "G" : m.result === "D" ? "E" : "P"}
                </span>
                <span className="w-16 shrink-0 text-[11px] text-faint">{dateShort(m.date).slice(0, 6)}</span>
                <span className="text-[11px] text-muted">{m.venue === "home" ? "vs" : "@"}</span>
                <Link to={`/teams/${m.opponent_id}`} className="link min-w-0 flex-1 truncate">{m.opponent}</Link>
                <span className="tabular font-medium">{m.gf}-{m.ga}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title="Plantel con minutos en la última temporada" subtitle="Ordenado por minutos" bodyClass="p-0 sm:p-0">
        {data.squad.length === 0 ? <div className="p-4"><Notice>{data.squad_note}</Notice></div> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead><tr className="table-head border-b border-line/70">
                <th className="px-4 py-2.5">Jugador</th><th className="px-3 py-2.5">Pos.</th><th className="px-3 py-2.5 text-right">Edad</th>
                <th className="px-3 py-2.5 text-right">Min.</th><th className="px-3 py-2.5 text-right">G</th><th className="px-3 py-2.5 text-right">A</th>
                <th className="px-3 py-2.5 text-right">Valor</th><th className="px-4 py-2.5 text-right">Rating</th>
              </tr></thead>
              <tbody>
                {data.squad.map((p) => (
                  <tr key={p.player_id} className="border-b border-line/40 last:border-0 hover:bg-raised/40">
                    <td className="px-4 py-2">
                      <Link to={`/players/${p.player_id}`} className="flex items-center gap-2">
                        <Avatar name={p.name} src={p.image_url} size={26} /><span className="link font-medium">{p.name}</span>
                      </Link>
                    </td>
                    <td className="px-3 py-2">{p.position ? <Badge>{POSITION_SHORT[p.position]}</Badge> : "—"}</td>
                    <td className="tabular px-3 py-2 text-right">{dec1(p.age)}</td>
                    <td className="tabular px-3 py-2 text-right">{int(p.minutes)}</td>
                    <td className="tabular px-3 py-2 text-right">{p.goals}</td>
                    <td className="tabular px-3 py-2 text-right">{p.assists}</td>
                    <td className="tabular px-3 py-2 text-right">{eur(p.market_value_eur)}</td>
                    <td className="px-4 py-2 text-right"><ScorePill value={p.rating} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Historial por temporada" bodyClass="p-0 sm:p-0">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[620px] text-sm">
            <thead><tr className="table-head border-b border-line/70">
              {["Temporada", "Liga", "PJ", "G", "E", "P", "GF", "GC", "Pts", "Pts/PJ"].map((h, i) => <th key={h} className={i > 1 ? "px-3 py-2.5 text-right" : "px-4 py-2.5"}>{h}</th>)}
            </tr></thead>
            <tbody>
              {data.seasons.slice().reverse().map((s) => (
                <tr key={`${s.season}${s.league_name}`} className="border-b border-line/40 last:border-0">
                  <td className="px-4 py-2">{s.season_label}</td><td className="px-4 py-2 text-muted">{s.league_name}</td>
                  {[s.matches, s.wins, s.draws, s.losses, s.goals_for, s.goals_against, s.points].map((v, i) => <td key={i} className="tabular px-3 py-2 text-right">{v}</td>)}
                  <td className="tabular px-3 py-2 text-right">{dec2(s.points_per_match)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
