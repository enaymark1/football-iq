import { ArrowLeft, ExternalLink, GitCompareArrows, Sparkles, ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AXIS, GRID, tooltip } from "../components/charts";
import { Avatar, Badge, Card, EmptyState, ErrorState, Loading, Notice, PercentileBar, ScorePill, Stat, Tabs } from "../components/ui";
import { logActivity } from "../hooks/useActivity";
import { useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { api } from "../services/api";
import type { MetricComparison, PlayerProfile } from "../types/api";
import { dateShort, dec1, dec2, eur, int, metricValue, pct, positionLabel } from "../utils/format";

function StrengthList({ items, kind }: { items: MetricComparison[]; kind: "strength" | "weakness" }) {
  const { metricMap } = useMeta();
  if (!items.length)
    return <p className="text-xs text-muted">{kind === "strength" ? "Ninguna métrica en el 25% superior de su posición." : "Ninguna métrica en el 25% inferior de su posición."}</p>;
  return (
    <ul className="space-y-1.5">
      {items.map((m) => (
        <li key={m.metric} className="flex items-center justify-between gap-3 text-sm">
          <span>{m.label}{m.scope === "team_context" && <span className="ml-1 text-[11px] text-faint">(equipo)</span>}</span>
          <span className="tabular text-xs text-muted">{metricValue(m.value, metricMap[m.metric]?.unit)} · p{Math.round(m.percentile!)}</span>
        </li>
      ))}
    </ul>
  );
}

function SeasonCharts({ seasons }: { seasons: PlayerProfile["seasons"] }) {
  if (seasons.length < 2)
    return <EmptyState title="Una sola temporada en los datos">La evolución aparece cuando hay dos o más temporadas.</EmptyState>;
  const rows = seasons.map((s) => ({ ...s, ga90: s.goal_contrib_p90 }));
  const small = (dataKey: string, title: string, fmt: (v: number) => string, kind: "line" | "bar") => (
    <div>
      <div className="label mb-2">{title}</div>
      <div className="h-36">
        <ResponsiveContainer>
          {kind === "bar" ? (
            <BarChart data={rows} margin={{ left: -18, right: 4 }}>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="season_label" {...AXIS} fontSize={10} />
              <YAxis {...AXIS} fontSize={10} />
              <Tooltip cursor={{ fill: "rgb(255 255 255 / 0.03)" }}
                content={tooltip((p) => ({ title: p[0].payload.season_label, rows: [{ label: title, value: fmt(p[0].value) }, { label: "Club", value: p[0].payload.team_name }] }))} />
              <Bar dataKey={dataKey} fill="rgb(var(--accent))" radius={[4, 4, 0, 0]} maxBarSize={28} />
            </BarChart>
          ) : (
            <LineChart data={rows} margin={{ left: -18, right: 8, top: 6 }}>
              <CartesianGrid {...GRID} />
              <XAxis dataKey="season_label" {...AXIS} fontSize={10} />
              <YAxis {...AXIS} fontSize={10} />
              <Tooltip content={tooltip((p) => ({ title: p[0].payload.season_label, rows: [{ label: title, value: fmt(p[0].value) }, { label: "Minutos", value: int(p[0].payload.minutes) }] }))} />
              <Line dataKey={dataKey} stroke="rgb(var(--accent))" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
      {small("minutes", "Minutos", (v) => int(v), "bar")}
      {small("ga90", "Goles + asistencias / 90", (v) => dec2(v), "line")}
      {small("rating", "FIQ Rating", (v) => dec1(v), "line")}
    </div>
  );
}

function ValueChart({ profile }: { profile: PlayerProfile }) {
  const v = profile.valuations;
  if (v.length < 2) return <EmptyState title="Sin historial de valor suficiente" />;
  const data = v.map((x) => ({ date: x.date, value: x.value_eur, t: new Date(x.date).getTime() }));
  return (
    <div className="h-48">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ left: 4, right: 8, top: 6 }}>
          <CartesianGrid {...GRID} />
          <XAxis dataKey="t" type="number" domain={["dataMin", "dataMax"]} scale="time" {...AXIS} fontSize={10}
            tickFormatter={(t) => new Date(t).getFullYear().toString()} />
          <YAxis {...AXIS} fontSize={10} tickFormatter={(x) => (x >= 1e6 ? `${Math.round(x / 1e6)}M` : `${Math.round(x / 1e3)}k`)} width={44} />
          <Tooltip content={tooltip((p) => ({ title: dateShort(p[0].payload.date), rows: [{ label: "Valor registrado", value: eur(p[0].value) }] }))} />
          <Line type="stepAfter" dataKey="value" stroke="var(--series-1)" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function PlayerProfilePage() {
  const { id } = useParams();
  const pid = Number(id);
  const nav = useNavigate();
  const [season, setSeason] = useState<number | undefined>();
  const { data, error, loading, reload } = useApi(() => api.player(pid, season), [pid, season]);
  const { metricMap } = useMeta();
  useEffect(() => setSeason(undefined), [pid]);
  useEffect(() => {
    if (data) logActivity({ kind: "player", label: data.player.name, detail: `Perfil · ${data.player.current_team_name ?? "sin club"}`, path: `/players/${pid}` });
  }, [data?.player.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <ErrorState error={error} onRetry={reload} />;
  if (!data) return <Loading label="Cargando perfil" />;
  const p = data.player;
  const s = data.seasons.find((x) => x.season === data.selected_season);
  const age = p.date_of_birth ? (Date.now() - new Date(p.date_of_birth).getTime()) / (365.25 * 864e5) : null;
  const dq = data.data_quality;

  return (
    <div className={loading ? "space-y-5 opacity-60 transition-opacity" : "space-y-5"}>
      <button className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-ink" onClick={() => nav(-1)}>
        <ArrowLeft size={14} /> Volver
      </button>

      <section className="card card-pad flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-4">
          <Avatar name={p.name} src={p.image_url} size={64} />
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{p.name}</h1>
              {p.position && <Badge tone="accent">{positionLabel(p.position)}</Badge>}
              {p.sub_position && p.sub_position !== p.position && <Badge>{p.sub_position}</Badge>}
            </div>
            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm text-muted">
              {p.current_team_id ? (
                <Link className="link inline-flex items-center gap-1.5" to={`/teams/${p.current_team_id}`}>
                  <Avatar name={p.current_team_name ?? ""} src={p.current_team_image_url} size={18} tone="team" />{p.current_team_name}
                </Link>
              ) : <span>Sin club en los datos</span>}
              {p.current_league_name && <span>{p.current_league_name}</span>}
              <span>{p.nationality ?? "Nacionalidad sin dato"}</span>
              <span>{age ? `${Math.floor(age)} años` : "Edad sin dato"}</span>
              {p.height_cm && <span>{p.height_cm} cm</span>}
              {p.foot && <span>Pie {p.foot === "right" ? "derecho" : p.foot === "left" ? "izquierdo" : "ambos"}</span>}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="btn-ghost" to={`/compare?ids=${pid}`}><GitCompareArrows size={14} /> Comparar</Link>
          <Link className="btn-ghost" to={`/similar?id=${pid}`}><Sparkles size={14} /> Similares</Link>
          {p.profile_url && <a className="btn-ghost" href={p.profile_url} target="_blank" rel="noreferrer"><ExternalLink size={14} /> Fuente</a>}
        </div>
      </section>

      {data.seasons.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Tabs value={String(data.selected_season)} onChange={(v) => setSeason(Number(v))}
            options={data.seasons.map((x) => ({ value: String(x.season), label: x.season_label }))} />
          {s && <span className="text-xs text-muted">{s.team_name} · {s.league_name}{s.teams_count > 1 ? ` · ${s.teams_count} clubes en la temporada` : ""}</span>}
        </div>
      )}

      {s ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-8">
          <Stat label="Partidos" value={s.matches} />
          <Stat label="Minutos" value={int(s.minutes)} hint={`${pct(s.minutes_share)} de su club`} />
          <Stat label="Goles" value={s.goals} hint={`${dec2(s.goals_p90)} por 90`} />
          <Stat label="Asistencias" value={s.assists} hint={`${dec2(s.assists_p90)} por 90`} />
          <Stat label="G+A / 90" value={dec2(s.goal_contrib_p90)} />
          <Stat label="Tarjetas" value={`${s.yellow_cards} / ${s.red_cards}`} hint="amarillas / rojas" />
          <Stat label="FIQ Rating" value={<ScorePill value={s.rating} />} hint={`confianza ${pct(s.rating_reliability)}`} />
          <Stat label="Valor registrado" value={eur(p.market_value_eur)} hint={p.market_value_date ? `al ${dateShort(p.market_value_date)}` : "sin fecha"} />
        </div>
      ) : <Notice>Este jugador no tiene estadísticas de liga importadas.</Notice>}

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2" title="Comparación con su posición"
          subtitle={data.position_comparison ? `Percentil contra ${int(data.position_comparison.reference_size)} ${positionLabel(data.position_comparison.position).toLowerCase()}s con 450+ minutos en la temporada (todas las ligas)` : undefined}>
          {data.position_comparison ? (
            <>
              {data.position_comparison.sample_warning && <div className="mb-3"><Notice tone="warning">{data.position_comparison.sample_warning}</Notice></div>}
              <div className="overflow-x-auto">
                <table className="w-full min-w-[480px] text-sm">
                  <thead><tr className="table-head"><th className="py-2">Métrica</th><th className="py-2 text-right">Valor</th>
                    <th className="py-2 text-right">Mediana pos.</th><th className="w-48 py-2 pl-6">Percentil</th></tr></thead>
                  <tbody>
                    {data.position_comparison.metrics.map((m) => (
                      <tr key={m.metric} className="border-t border-line/40">
                        <td className="py-2" title={metricMap[m.metric]?.description}>
                          {m.label}
                          {m.scope === "team_context" && <Badge className="ml-2">equipo</Badge>}
                          {!m.higher_is_better && <span className="ml-1 text-[11px] text-faint">(menos es mejor)</span>}
                        </td>
                        <td className="tabular py-2 text-right">{metricValue(m.value, metricMap[m.metric]?.unit)}</td>
                        <td className="tabular py-2 text-right text-muted">{metricValue(m.position_median, metricMap[m.metric]?.unit)}</td>
                        <td className="py-2 pl-6"><PercentileBar value={m.percentile} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : <EmptyState title="Sin estadísticas para comparar" />}
        </Card>
        <div className="space-y-5">
          <Card title={<span className="inline-flex items-center gap-1.5"><ThumbsUp size={14} className="text-accent" /> Fortalezas estadísticas</span>}>
            <StrengthList items={data.strengths} kind="strength" />
          </Card>
          <Card title={<span className="inline-flex items-center gap-1.5"><ThumbsDown size={14} className="text-serious" /> Debilidades estadísticas</span>}>
            <StrengthList items={data.weaknesses} kind="weakness" />
          </Card>
        </div>
      </div>

      <Card title="Rendimiento por temporada" subtitle="Solo partidos de liga doméstica">
        <SeasonCharts seasons={data.seasons} />
      </Card>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card title="Valor de mercado" subtitle="Historial registrado en Transfermarkt (no es precio de transferencia)">
          <ValueChart profile={data} />
          {data.value_estimate && (
            <div className="mt-4 rounded-md border border-line bg-bg/60 p-3">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="label">Valor estimado por el modelo</span>
                <Badge tone={data.value_estimate.out_of_sample ? "info" : "warning"}>
                  {data.value_estimate.out_of_sample ? "fuera de muestra" : "temporada de entrenamiento"}
                </Badge>
              </div>
              <div className="tabular mt-1 text-lg font-semibold">{eur(data.value_estimate.estimated_value_eur)}</div>
              <div className="text-xs text-muted">
                Rango típico de error: {eur(data.value_estimate.typical_range_eur[0])} – {eur(data.value_estimate.typical_range_eur[1])}.
                Distinto del valor registrado ({eur(p.market_value_eur)}): el modelo solo ve edad, posición, liga y estadísticas.
              </div>
              {data.value_estimate.notes.map((n) => <div key={n} className="mt-1 text-[11px] text-warning">{n}</div>)}
            </div>
          )}
        </Card>
        <Card title="Jugadores similares" subtitle="Similitud coseno sobre perfil estadístico de la misma posición"
          actions={<Link to={`/similar?id=${pid}`} className="text-xs text-accent hover:underline">Ver 10 y ajustar</Link>}>
          {data.similar?.results.length ? (
            <ul className="divide-y divide-line/50">
              {data.similar.results.map((r) => (
                <li key={r.player_id} className="flex items-center gap-3 py-2">
                  <Avatar name={r.name} src={r.image_url} size={28} />
                  <div className="min-w-0 flex-1">
                    <Link to={`/players/${r.player_id}`} className="link block truncate text-sm font-medium">{r.name}</Link>
                    <div className="truncate text-[11px] text-muted">{r.team_name} · {r.league_name}</div>
                  </div>
                  <span className="tabular text-xs text-muted" title="Índice de similitud coseno ×100 (no es una probabilidad)">
                    sim. {(r.similarity * 100).toFixed(0)}
                  </span>
                </li>
              ))}
            </ul>
          ) : <EmptyState title="Sin similares para mostrar">{data.similar?.warnings.join(" ")}</EmptyState>}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="Todas las temporadas" bodyClass="p-0 sm:p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead><tr className="table-head border-b border-line/70">
                {["Temporada", "Club", "Edad", "PJ", "Min.", "G", "A", "G+A/90", "Valor fin", "Rating"].map((h, i) => (
                  <th key={h} className={i > 1 ? "px-3 py-2 text-right" : "px-4 py-2"}>{h}</th>))}
              </tr></thead>
              <tbody>
                {data.seasons.slice().reverse().map((x) => (
                  <tr key={x.season} className="border-b border-line/40 last:border-0">
                    <td className="px-4 py-2">{x.season_label}</td>
                    <td className="max-w-[180px] truncate px-4 py-2 text-muted">{x.team_name}</td>
                    <td className="tabular px-3 py-2 text-right">{dec1(x.age)}</td>
                    <td className="tabular px-3 py-2 text-right">{x.matches}</td>
                    <td className="tabular px-3 py-2 text-right">{int(x.minutes)}</td>
                    <td className="tabular px-3 py-2 text-right">{x.goals}</td>
                    <td className="tabular px-3 py-2 text-right">{x.assists}</td>
                    <td className="tabular px-3 py-2 text-right">{dec2(x.goal_contrib_p90)}</td>
                    <td className="tabular px-3 py-2 text-right">{eur(x.market_value_end_eur)}</td>
                    <td className="px-3 py-2 text-right"><ScorePill value={x.rating} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card title="Calidad y cobertura de datos">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-muted">Perfil completo</dt><dd className="tabular">{pct(dq.profile_completeness)}</dd></div>
            {dq.profile_fields_missing?.length > 0 && <div className="text-[11px] text-warning">Sin dato: {dq.profile_fields_missing.join(", ")}</div>}
            {dq.minutes != null && <div className="flex justify-between"><dt className="text-muted">Muestra de la temporada</dt><dd>{dq.sample} ({int(dq.minutes)} min)</dd></div>}
            {dq.rating_reliability != null && <div className="flex justify-between"><dt className="text-muted">Confianza del rating</dt><dd className="tabular">{pct(dq.rating_reliability)}</dd></div>}
            <div className="flex justify-between"><dt className="text-muted">Puntos de valoración</dt><dd className="tabular">{dq.valuation_points}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Última valoración</dt><dd>{dateShort(dq.last_valuation_date)}</dd></div>
          </dl>
          <div className="mt-4"><Notice>
            No disponibles en la fuente: {data.unavailable_metrics.join(", ")}. {data.unavailable_reason}
          </Notice></div>
        </Card>
      </div>
    </div>
  );
}
