import { X } from "lucide-react";
import { useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { AXIS, GRID, Legend, tooltip } from "../components/charts";
import { PlayerPicker } from "../components/Pickers";
import { Avatar, Badge, Card, cx, EmptyState, ErrorState, Loading, Notice, PageHeader } from "../components/ui";
import { SERIES_COLORS } from "../config";
import { logActivity } from "../hooks/useActivity";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import type { CompareResponse } from "../types/api";
import { metricValue, positionLabel } from "../utils/format";

const BAR_METRICS = ["goals_p90", "assists_p90", "goal_contrib_p90", "cards_p90"];

function RadarBlock({ data }: { data: CompareResponse }) {
  const rows = data.radar.metrics.map((m) => {
    const row: Record<string, any> = { metric: m.label };
    data.players.forEach((_, i) => (row[`p${i}`] = data.radar.percentiles[i][m.key]));
    return row;
  });
  const chart = (idx: number[]) => (
    <ResponsiveContainer>
      <RadarChart data={rows} outerRadius="72%">
        <PolarGrid stroke="var(--grid)" />
        <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10 }} />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        {idx.map((i) => (
          <Radar key={i} dataKey={`p${i}`} name={data.players[i].name} stroke={SERIES_COLORS[i]} strokeWidth={2}
            fill={SERIES_COLORS[i]} fillOpacity={idx.length === 1 ? 0.18 : 0.08} dot={{ r: 3 }} />
        ))}
        <Tooltip content={tooltip((p) => ({ title: p[0].payload.metric,
          rows: p.map((x: any) => ({ label: x.name, value: x.value == null ? "sin dato" : `p${Math.round(x.value)}`, color: x.color })) }))} />
      </RadarChart>
    </ResponsiveContainer>
  );
  // Hasta 3 jugadores superpuestos (paleta validada para todas las parejas); con 4, un radar por jugador.
  if (data.players.length <= 3)
    return <div className="h-80">{chart(data.players.map((_, i) => i))}</div>;
  return (
    <div className="grid grid-cols-2 gap-2">
      {data.players.map((p, i) => (
        <div key={p.player_id}>
          <div className="text-center text-xs font-medium" style={{ color: "rgb(var(--ink))" }}>{p.name}</div>
          <div className="h-48">{chart([i])}</div>
        </div>
      ))}
    </div>
  );
}

export default function ComparePage() {
  const [sp, setSp] = useSearchParams();
  const ids = (sp.get("ids") || "").split(",").map(Number).filter((x) => x > 0).slice(0, 4);
  const setIds = (next: number[]) => setSp(next.length ? { ids: next.join(",") } : {}, { replace: true });
  const { data, error, loading, reload } = useApi(() => api.compare(ids), [ids.join(",")], ids.length >= 2);
  const single = useApi(() => api.player(ids[0]), [ids[0]], ids.length === 1);

  useEffect(() => {
    if (data) logActivity({ kind: "compare", label: `Comparación: ${data.players.map((p) => p.name.split(" ").at(-1)).join(" vs ")}`,
      detail: `${data.players.length} jugadores`, path: `/compare?ids=${ids.join(",")}` });
  }, [data]); // eslint-disable-line react-hooks/exhaustive-deps

  const chips = data?.players.map((p) => ({ id: p.player_id, name: p.name, image: p.image_url, sub: `${positionLabel(p.position)} · ${p.team_name}` }))
    ?? (single.data ? [{ id: ids[0], name: single.data.player.name, image: single.data.player.image_url, sub: positionLabel(single.data.player.position) }] : []);

  const barRows = data ? BAR_METRICS.map((k) => {
    const m = data.metrics.find((x) => x.metric === k);
    if (!m) return null;
    const row: Record<string, any> = { label: m.label, unit: m.unit };
    m.values.forEach((v, i) => (row[`p${i}`] = v));
    return row;
  }).filter(Boolean) as Record<string, any>[] : [];

  return (
    <div className="space-y-5">
      <PageHeader title="Player Comparison"
        subtitle="Compará de 2 a 4 jugadores. Se muestran solo las métricas que existen para todos; el radar usa percentiles dentro de la posición." />

      <Card>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="flex flex-1 flex-wrap gap-2">
            {chips.map((c, i) => (
              <span key={c.id} className="inline-flex items-center gap-2 rounded-md border border-line bg-raised/60 py-1 pl-1.5 pr-1">
                <span className="h-2.5 w-2.5 rounded-sm" style={{ background: SERIES_COLORS[i] }} />
                <Avatar name={c.name} src={c.image} size={22} />
                <Link to={`/players/${c.id}`} className="link text-sm">{c.name}</Link>
                <span className="hidden text-[11px] text-muted sm:inline">{c.sub}</span>
                <button className="rounded p-1 text-faint hover:bg-bg hover:text-ink" aria-label={`Quitar ${c.name}`}
                  onClick={() => setIds(ids.filter((x) => x !== c.id))}><X size={13} /></button>
              </span>
            ))}
            {ids.length === 0 && <span className="text-sm text-muted">Agregá jugadores con el buscador.</span>}
          </div>
          <div className="w-full lg:w-72">
            <PlayerPicker disabled={ids.length >= 4} exclude={ids}
              placeholder={ids.length >= 4 ? "Máximo 4 jugadores" : "Agregar jugador…"}
              onPick={(p) => setIds([...ids, p.id])} />
          </div>
        </div>
      </Card>

      {ids.length < 2 && <Card><EmptyState title="Elegí al menos dos jugadores">Tip: desde el perfil de un jugador, “Comparar” lo agrega acá.</EmptyState></Card>}
      {error && <ErrorState error={error} onRetry={reload} />}
      {loading && ids.length >= 2 && !data && <Loading label="Comparando" />}

      {data && ids.length >= 2 && (
        <div className={cx("space-y-5", loading && "opacity-60")}>
          {data.notes.map((n) => <Notice key={n} tone="warning">{n}</Notice>)}
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <Card title="Radar de percentiles" subtitle={data.radar.normalization}>
              <RadarBlock data={data} />
              <div className="mt-2"><Legend items={data.players.map((p, i) => ({ label: p.name, color: SERIES_COLORS[i] }))} /></div>
            </Card>
            <Card title="Producción por 90 minutos" subtitle="Valores absolutos de la temporada de cada jugador">
              <div className="h-80">
                <ResponsiveContainer>
                  <BarChart data={barRows} margin={{ left: -12, right: 8 }} barGap={2} barCategoryGap="22%">
                    <CartesianGrid {...GRID} />
                    <XAxis dataKey="label" {...AXIS} fontSize={10} interval={0} />
                    <YAxis {...AXIS} fontSize={10} />
                    <Tooltip cursor={{ fill: "rgb(255 255 255 / 0.03)" }} content={tooltip((p, label) => ({ title: label,
                      rows: p.map((x: any) => ({ label: data.players[Number(x.dataKey.slice(1))].name, value: metricValue(x.value, "p90"), color: x.color })) }))} />
                    {data.players.map((pl, i) => (
                      <Bar key={pl.player_id} dataKey={`p${i}`} name={pl.name} fill={SERIES_COLORS[i]} radius={[4, 4, 0, 0]} maxBarSize={22} />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <Legend items={data.players.map((p, i) => ({ label: p.name, color: SERIES_COLORS[i] }))} />
            </Card>
          </div>

          <Card title="Tabla de estadísticas" subtitle="Diferencias contra el primer jugador: % cuando la base es mayor que 0; en proporciones, puntos porcentuales"
            bodyClass="p-0 sm:p-0">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="table-head border-b border-line/70">
                    <th className="px-4 py-2.5">Métrica</th>
                    {data.players.map((p, i) => (
                      <th key={p.player_id} className="px-3 py-2.5 text-right normal-case tracking-normal">
                        <span className="inline-flex items-center gap-1.5 text-xs text-ink">
                          <span className="h-2 w-2 rounded-sm" style={{ background: SERIES_COLORS[i] }} />{p.name}
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-line/40">
                    <td className="px-4 py-2 text-muted">Posición · temporada</td>
                    {data.players.map((p) => <td key={p.player_id} className="px-3 py-2 text-right text-xs">{positionLabel(p.position)} · {p.season}</td>)}
                  </tr>
                  {data.metrics.map((m) => {
                    const valid = m.values.filter((v): v is number => v != null);
                    const best = valid.length > 1 && m.scope !== "profile" ? (m.higher_is_better ? Math.max(...valid) : Math.min(...valid)) : null;
                    return (
                      <tr key={m.metric} className="border-b border-line/40 last:border-0">
                        <td className="px-4 py-2">
                          {m.label}
                          {m.scope === "team_context" && <Badge className="ml-2">equipo</Badge>}
                        </td>
                        {m.values.map((v, i) => {
                          const d = m.diff_vs_first[i];
                          return (
                            <td key={i} className="tabular px-3 py-2 text-right">
                              <span className={cx(best != null && v === best && "font-semibold text-ink", best != null && v !== best && "text-muted")}>
                                {metricValue(v, m.unit)}
                              </span>
                              {i > 0 && d && (
                                <span className={cx("ml-1.5 text-[11px]", d.value >= 0 ? "text-muted" : "text-faint")}>
                                  {d.value > 0 ? "+" : ""}{d.value.toFixed(1).replace(".", ",")}{d.type === "percent" ? "%" : " pp"}
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
          <Notice>
            Se resalta el mejor valor de cada métrica de rendimiento, pero tener más goles no hace mejor a un jugador por sí solo:
            el rol, la liga y el contexto del equipo cambian la lectura. No disponibles en la fuente: {data.unavailable_metrics.join(", ")}.
          </Notice>
        </div>
      )}
    </div>
  );
}
