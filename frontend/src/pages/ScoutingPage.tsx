import { Binoculars, Filter } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Avatar, Badge, Card, cx, EmptyState, ErrorState, Field, Notice, NumberInput, PageHeader, PercentileBar, ScorePill, Select } from "../components/ui";
import { logActivity } from "../hooks/useActivity";
import { useAction } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { api } from "../services/api";
import type { Position } from "../types/api";
import { dec1, eur, int, metricValue, positionLabel } from "../utils/format";

const PRESETS: Record<string, { position: Position; weights: Record<string, number> }> = {
  "Mediocampista creador": { position: "Midfield", weights: { assists_p90: 3, goal_involvement_share: 2, team_ppm: 1, minutes_share: 1 } },
  "Delantero goleador": { position: "Attack", weights: { goals_p90: 4, goal_involvement_share: 2, minutes_share: 1 } },
  "Defensor sólido": { position: "Defender", weights: { team_ga_pm: 3, clean_sheet_rate: 2, minutes_share: 2, cards_p90: 1 } },
  "Arquero titular": { position: "Goalkeeper", weights: { clean_sheet_rate: 3, team_ga_pm: 3, minutes_share: 2 } },
};

export default function ScoutingPage() {
  const meta = useMeta();
  const [position, setPosition] = useState<Position | "">("Midfield");
  const [maxAge, setMaxAge] = useState<number | "">(24);
  const [budget, setBudget] = useState<number | "">(10);
  const [minMinutes, setMinMinutes] = useState<number | "">(900);
  const [leagues, setLeagues] = useState<number[]>([]);
  const [weights, setWeights] = useState<Record<string, number>>(PRESETS["Mediocampista creador"].weights);
  const action = useAction(api.scouting);
  const res = action.data;

  const metricKeys = (meta.data?.scouting_metrics || []).filter((k) => !["minutes", "goals", "assists"].includes(k));
  const active = Object.entries(weights).filter(([, w]) => w > 0);
  const totalW = active.reduce((s, [, w]) => s + w, 0);

  const run = async () => {
    const body = {
      position: position || null, max_age: maxAge === "" ? null : maxAge,
      max_budget_eur: budget === "" ? null : budget * 1e6, league_ids: leagues,
      min_minutes: minMinutes === "" ? 0 : minMinutes, metrics: Object.fromEntries(active), limit: 30,
    };
    const r = await action.run(body);
    if (r) logActivity({ kind: "scouting", label: `Scouting: ${positionLabel(position || null)}${maxAge !== "" ? ` ≤${maxAge} años` : ""}`,
      detail: `${r.candidates.length} candidatos${budget !== "" ? ` · hasta ${budget} M€` : ""}`, path: "/scouting" });
  };

  return (
    <div className="space-y-5">
      <PageHeader title="Scouting" subtitle="Definí el perfil buscado. Primero se aplican los requisitos obligatorios; después cada métrica se pasa a percentil dentro de la posición, se respeta su dirección (más o menos es mejor) y se pondera con tus pesos." />
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
        <Card title="Perfil buscado" className="self-start">
          <div className="space-y-4">
            <Field label="Plantillas">
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(PRESETS).map(([name, p]) => (
                  <button key={name} className="btn-ghost h-7 px-2 text-xs" onClick={() => { setPosition(p.position); setWeights(p.weights); }}>{name}</button>
                ))}
              </div>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Posición">
                <Select value={position} onChange={(v) => setPosition(v as Position | "")}>
                  <option value="">Cualquiera</option>
                  {(meta.data?.positions || []).map((p) => <option key={p} value={p}>{positionLabel(p)}</option>)}
                </Select>
              </Field>
              <Field label="Edad máxima"><NumberInput value={maxAge} min={15} max={45} onChange={setMaxAge} placeholder="Sin límite" /></Field>
              <Field label="Presupuesto (M€)" hint="Contra el valor registrado"><NumberInput value={budget} min={0} step={0.5} onChange={setBudget} placeholder="Sin límite" /></Field>
              <Field label="Minutos mínimos"><NumberInput value={minMinutes} min={0} step={90} onChange={setMinMinutes} /></Field>
            </div>
            <Field label={`Ligas (${leagues.length ? leagues.length : "todas"})`}>
              <div className="max-h-36 space-y-1 overflow-auto rounded-md border border-line bg-bg p-2">
                {meta.playerLeagues.map((l) => (
                  <label key={l.id} className="flex cursor-pointer items-center gap-2 text-sm">
                    <input type="checkbox" className="accent-[rgb(var(--accent))]" checked={leagues.includes(l.id)}
                      onChange={(e) => setLeagues(e.target.checked ? [...leagues, l.id] : leagues.filter((x) => x !== l.id))} />
                    {l.name}
                  </label>
                ))}
              </div>
            </Field>
            <div>
              <div className="label mb-2">Métricas prioritarias y peso</div>
              <div className="space-y-2.5">
                {metricKeys.map((k) => {
                  const m = meta.metricMap[k];
                  const w = weights[k] || 0;
                  return (
                    <div key={k} title={m?.description}>
                      <div className="flex items-center justify-between text-xs">
                        <span className={w ? "text-ink" : "text-muted"}>
                          {m?.label}{m && !m.higher_is_better && <span className="text-faint"> · menos es mejor</span>}
                        </span>
                        <span className="tabular text-muted">{w ? `${Math.round((w / totalW) * 100)}%` : "—"}</span>
                      </div>
                      <input type="range" min={0} max={5} step={1} value={w} aria-label={`Peso de ${m?.label}`}
                        className="mt-1 w-full accent-[rgb(var(--accent))]"
                        onChange={(e) => setWeights({ ...weights, [k]: Number(e.target.value) })} />
                    </div>
                  );
                })}
              </div>
            </div>
            <button className="btn-primary w-full" disabled={!active.length || action.loading} onClick={run}>
              <Binoculars size={15} /> {action.loading ? "Buscando…" : "Buscar candidatos"}
            </button>
            {!active.length && <p className="text-[11px] text-warning">Elegí al menos una métrica con peso mayor a 0.</p>}
          </div>
        </Card>

        <div className="space-y-4">
          {action.error && <ErrorState error={action.error} />}
          {!res && !action.error && (
            <Card><EmptyState title="Configurá el perfil y buscá" icon={<Binoculars size={22} />}>
              Ejemplo cargado: mediocampista de hasta 24 años, presupuesto de 10 M€, priorizando asistencias, participación en goles y resultados del equipo.
            </EmptyState></Card>
          )}
          {res && (
            <>
              <Card title={<span className="inline-flex items-center gap-1.5"><Filter size={14} /> Requisitos obligatorios</span>}
                subtitle={`Temporada ${meta.seasonLabel(res.season)}`}>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  {res.funnel.map((f, i) => (
                    <span key={f.step} className="inline-flex items-center gap-2">
                      {i > 0 && <span className="text-faint">→</span>}
                      <span className="rounded-md border border-line bg-bg px-2 py-1"><span className="text-muted">{f.step}</span>
                        <span className="tabular ml-1.5 font-semibold">{int(f.remaining)}</span></span>
                    </span>
                  ))}
                </div>
                {res.excluded_without_value > 0 && <p className="mt-2 text-[11px] text-muted">{res.excluded_without_value} jugadores sin valor registrado quedaron afuera del filtro de presupuesto.</p>}
                {res.reference && <p className="mt-1 text-[11px] text-faint">{res.reference}</p>}
              </Card>
              {res.candidates.length === 0 ? (
                <Card><EmptyState title="Ningún jugador cumple los requisitos">Probá con más edad, más presupuesto o menos minutos mínimos.</EmptyState></Card>
              ) : (
                <div className="space-y-2.5">
                  {res.candidates.map((c, i) => (
                    <article key={c.player_id} className={cx("card card-pad animate-fadein", i < 3 && "border-accent/25")}>
                      <div className="flex flex-col gap-3 md:flex-row md:items-start">
                        <div className="flex min-w-0 flex-1 items-start gap-3">
                          <span className="tabular mt-1 w-5 text-right text-sm text-faint">{i + 1}</span>
                          <Avatar name={c.name} src={c.image_url} size={36} />
                          <div className="min-w-0">
                            <Link to={`/players/${c.player_id}`} className="link font-semibold">{c.name}</Link>
                            <div className="text-xs text-muted">{c.sub_position ?? positionLabel(c.position)} · {c.team_name} · {c.league_name}</div>
                            <div className="tabular mt-1 flex flex-wrap gap-x-3 text-xs text-muted">
                              <span>{dec1(c.age)} años</span><span>{int(c.minutes)} min</span><span>{eur(c.market_value_eur)}</span>
                              <span>Rating {dec1(c.rating)}</span>
                            </div>
                            <p className="mt-2 text-sm leading-relaxed text-ink/90">{c.explanation}</p>
                          </div>
                        </div>
                        <div className="w-full shrink-0 space-y-1.5 md:w-64">
                          <div className="flex items-center justify-between">
                            <span className="label">Adecuación</span><ScorePill value={c.score} />
                          </div>
                          {Object.entries(c.percentiles).map(([k, v]) => (
                            <div key={k} className="grid grid-cols-[1fr_120px] items-center gap-2 text-[11px]">
                              <span className="truncate text-muted" title={`${meta.metricMap[k]?.label}: ${metricValue(c.values[k], meta.metricMap[k]?.unit)}`}>
                                {meta.metricMap[k]?.label}
                              </span>
                              <PercentileBar value={v} />
                            </div>
                          ))}
                          {c.data_coverage < 1 && <Badge tone="warning">Datos incompletos</Badge>}
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              )}
              <Notice>El puntaje mide cuánto se ajusta el jugador al perfil pedido con las métricas disponibles (goles, asistencias, minutos, tarjetas y contexto de equipo). No incluye pases, duelos ni datos físicos.</Notice>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
