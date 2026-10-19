import { Calculator, CircleDollarSign, Info, RotateCcw } from "lucide-react";
import { Fragment, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PlayerPicker } from "../components/Pickers";
import {
  Avatar, Badge, Card, cx, EmptyState, ErrorState, Field, Loading, Notice, NumberInput, PageHeader, ScorePill, Select, Tabs, UncertaintyBadge,
} from "../components/ui";
import { logActivity } from "../hooks/useActivity";
import { useAction, useApi, useDebounced } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { api } from "../services/api";
import type { Position, ValueEstimate } from "../types/api";
import { dec1, eur, int, positionLabel } from "../utils/format";

const COMPONENT_SHORT: Record<string, string> = {
  performance: "Rendimiento", value: "Valor bajo", model_gap: "Modelo vs valor", age: "Edad", minutes: "Minutos",
};
const COMPONENT_COLORS: Record<string, string> = {
  performance: "var(--series-1)", value: "var(--series-2)", model_gap: "var(--series-3)", age: "#8b929c", minutes: "#5b6170",
};

function Opportunities() {
  const meta = useMeta();
  const defaults = meta.data?.opportunity_default_weights ?? {};
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [position, setPosition] = useState<Position | "">("");
  const [league, setLeague] = useState("");
  const [maxAge, setMaxAge] = useState<number | "">(26);
  const [maxValue, setMaxValue] = useState<number | "">(15);
  const [minMinutes, setMinMinutes] = useState<number | "">(1200);
  const [sort, setSort] = useState("score");
  const w = Object.keys(weights).length ? weights : defaults;
  const body = {
    weights: w, position: position || null, league_ids: league ? [Number(league)] : [], max_age: maxAge === "" ? null : maxAge,
    max_value_eur: maxValue === "" ? null : maxValue * 1e6, min_minutes: minMinutes === "" ? 0 : minMinutes,
    sort_by: sort, sort_dir: sort === "age" || sort === "market_value_eur" ? "asc" : "desc", limit: 40,
  };
  const dBody = useDebounced(JSON.stringify(body), 350);
  const { data, error, loading, reload } = useApi(() => api.opportunities(JSON.parse(dBody)), [dBody], !!meta.data);
  useEffect(() => {
    if (data) logActivity({ kind: "market", label: "Oportunidades de mercado", detail: `${data.total} jugadores con los criterios`, path: "/market" });
  }, [data?.total]); // eslint-disable-line react-hooks/exhaustive-deps
  const totalW = Object.values(w).reduce((a, b) => a + b, 0) || 1;

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
      <Card title="Criterios y pesos" className="self-start">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Posición">
              <Select value={position} onChange={(v) => setPosition(v as Position | "")}>
                <option value="">Todas</option>
                {(meta.data?.positions || []).map((p) => <option key={p} value={p}>{positionLabel(p)}</option>)}
              </Select>
            </Field>
            <Field label="Liga">
              <Select value={league} onChange={setLeague}>
                <option value="">Todas</option>
                {meta.playerLeagues.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </Select>
            </Field>
            <Field label="Edad máxima"><NumberInput value={maxAge} min={15} max={45} onChange={setMaxAge} /></Field>
            <Field label="Valor máx. (M€)"><NumberInput value={maxValue} min={0} step={1} onChange={setMaxValue} /></Field>
            <Field label="Minutos mínimos"><NumberInput value={minMinutes} min={0} step={90} onChange={setMinMinutes} /></Field>
            <Field label="Ordenar por">
              <Select value={sort} onChange={setSort}>
                <option value="score">Índice</option><option value="rating">Rendimiento</option>
                <option value="market_value_eur">Valor (menor)</option><option value="age">Edad (menor)</option>
                <option value="minutes">Minutos</option>
              </Select>
            </Field>
          </div>
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="label">Pesos del índice</span>
              <button className="inline-flex items-center gap-1 text-[11px] text-muted hover:text-ink" onClick={() => setWeights({})}>
                <RotateCcw size={11} /> por defecto
              </button>
            </div>
            {Object.entries(meta.data?.opportunity_components || {}).map(([k, label]) => (
              <div key={k} className="mb-2">
                <div className="flex justify-between text-xs">
                  <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: COMPONENT_COLORS[k] }} />{label}</span>
                  <span className="tabular text-muted">{Math.round(((w[k] || 0) / totalW) * 100)}%</span>
                </div>
                <input type="range" min={0} max={1} step={0.05} value={w[k] ?? 0} aria-label={`Peso ${label}`}
                  className="w-full accent-[rgb(var(--accent))]" onChange={(e) => setWeights({ ...w, [k]: Number(e.target.value) })} />
              </div>
            ))}
          </div>
          <details className="rounded-md border border-line bg-bg/60 p-3 text-[11px] leading-relaxed text-muted">
            <summary className="cursor-pointer font-medium text-ink"><Info size={12} className="mr-1 inline" />Cómo se calcula</summary>
            <pre className="mt-2 whitespace-pre-wrap font-sans">{meta.data?.opportunity_definition?.trim()}</pre>
          </details>
        </div>
      </Card>

      <div className="space-y-3">
        <Notice title="Oportunidad estadística, no valoración oficial">
          {data?.disclaimer ?? "El índice combina rendimiento, valor, edad y minutos con los pesos elegidos."} El valor registrado
          es una estimación comunitaria de Transfermarkt; un número bajo puede deberse a contrato, lesiones o factores que los datos no ven.
        </Notice>
        {data?.notes.map((n) => <Notice key={n} tone="warning">{n}</Notice>)}
        {error && <ErrorState error={error} onRetry={reload} />}
        {loading && !data && <Loading label="Calculando índice" />}
        {data && (
          <Card title={`Posibles jugadores infravalorados · ${int(data.total)} cumplen los criterios`}
            subtitle={`Temporada ${meta.seasonLabel(data.season)} · se muestran ${data.results.length}. ${data.excluded_without_value} jugadores sin valor registrado no se evalúan.`}
            bodyClass="p-0 sm:p-0">
            {data.results.length === 0 ? <EmptyState title="Nadie cumple esos criterios" /> : (
              <div className={cx("overflow-x-auto", loading && "opacity-60")}>
                <table className="w-full min-w-[860px] text-sm">
                  <thead>
                    <tr className="table-head border-b border-line/70">
                      <th className="px-4 py-2.5">Jugador</th><th className="px-3 py-2.5 text-right">Edad</th>
                      <th className="px-3 py-2.5 text-right">Min. (PJ)</th><th className="px-3 py-2.5 text-right">Rating</th>
                      <th className="px-3 py-2.5 text-right">Valor registrado</th><th className="px-3 py-2.5 text-right">Estimado modelo</th>
                      <th className="px-3 py-2.5">Aporte por factor</th><th className="px-3 py-2.5 text-right">Índice</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.results.map((r) => (
                      <Fragment key={r.player_id}>
                        <tr className="hover:bg-raised/30">
                          <td className="px-4 pt-2.5">
                            <div className="flex items-center gap-2.5">
                              <Avatar name={r.name} src={r.image_url} size={30} />
                              <div className="min-w-0">
                                <Link to={`/players/${r.player_id}`} className="link font-medium">{r.name}</Link>
                                <div className="text-[11px] text-muted">{r.sub_position ?? positionLabel(r.position)} · {r.team_name} · {r.league_name}</div>
                              </div>
                            </div>
                          </td>
                          <td className="tabular px-3 pt-2.5 text-right">{dec1(r.age)}</td>
                          <td className="tabular whitespace-nowrap px-3 pt-2.5 text-right">{int(r.minutes)} <span className="text-muted">({r.matches})</span></td>
                          <td className="tabular px-3 pt-2.5 text-right">{dec1(r.rating)}</td>
                          <td className="tabular px-3 pt-2.5 text-right">{eur(r.market_value_eur)}</td>
                          <td className="tabular px-3 pt-2.5 text-right text-muted">{eur(r.predicted_value_eur)}</td>
                          <td className="px-3 pt-2.5">
                            <div className="flex h-2 w-36 gap-[2px] overflow-hidden rounded-full bg-raised" role="img"
                              aria-label={Object.entries(r.contributions).map(([k, v]) => `${COMPONENT_SHORT[k]} ${v ?? 0}`).join(", ")}>
                              {Object.entries(r.contributions).map(([k, v]) => v ? (
                                <div key={k} title={`${COMPONENT_SHORT[k]}: ${v.toFixed(1)} pts (componente ${r.components[k]?.toFixed(0)}/100)`}
                                  style={{ width: `${v}%`, background: COMPONENT_COLORS[k] }} />
                              ) : null)}
                            </div>
                          </td>
                          <td className="px-3 pt-2.5 text-right"><ScorePill value={r.score} /></td>
                        </tr>
                        <tr className="border-b border-line/40 last:border-0">
                          <td colSpan={8} className="px-4 pb-2.5 pt-1">
                            <div className="flex flex-wrap items-center gap-2 text-[11px] leading-snug text-muted">
                              <UncertaintyBadge level={r.uncertainty} />
                              <span>{r.explanation}</span>
                            </div>
                          </td>
                        </tr>
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}

function EstimateResult({ r }: { r: ValueEstimate }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-md border border-line bg-bg/60 p-4">
          <div className="label">Valor estimado por el modelo</div>
          <div className="tabular mt-1 text-2xl font-semibold">{eur(r.estimated_value_eur)}</div>
          <div className="text-xs text-muted">Rango típico: {eur(r.typical_range_eur[0])} – {eur(r.typical_range_eur[1])}</div>
        </div>
        <div className="rounded-md border border-line bg-bg/60 p-4">
          <div className="label">Valor registrado (Transfermarkt)</div>
          <div className="tabular mt-1 text-2xl font-semibold">{r.registered_value_eur != null ? eur(r.registered_value_eur) : "—"}</div>
          <div className="text-xs text-muted">
            {r.difference_pct != null ? `El modelo estima ${r.difference_pct > 0 ? "+" : ""}${r.difference_pct.toFixed(0)}% respecto del registrado` : "Perfil hipotético: no hay valor registrado"}
          </div>
        </div>
      </div>
      {!r.reliable && <Notice tone="warning" title="Estimación poco confiable">Muestra chica o liga con pocas observaciones.</Notice>}
      {r.notes.map((n) => <Notice key={n} tone="warning">{n}</Notice>)}
      <Notice>
        {r.explanation} Error en evaluación: MAE {eur(r.model_metrics.mae_eur)}, RMSE {eur(r.model_metrics.rmse_eur)},
        error porcentual mediano {r.model_metrics.median_abs_pct_error}%.
      </Notice>
    </div>
  );
}

function ValueEstimator() {
  const meta = useMeta();
  const [mode, setMode] = useState<"player" | "profile">("player");
  const [picked, setPicked] = useState<{ id: number; name: string } | null>(null);
  const [form, setForm] = useState({ age: 22, position: "Midfield", league_name: "", matches: 30, minutes: 2400, goals: 5, assists: 6,
    team_matches: 34 } as Record<string, any>);
  const action = useAction(api.valueEstimate);
  const run = async (body: unknown, label: string) => {
    const r = await action.run(body);
    if (r) logActivity({ kind: "value", label: `Valor estimado: ${label}`, detail: eur(r.estimated_value_eur), path: "/market?tab=value" });
  };
  const num = (k: string) => (
    <NumberInput value={form[k] ?? ""} min={0} onChange={(v) => setForm({ ...form, [k]: v === "" ? null : v })} />
  );
  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
      <Card title="Qué estimar" className="self-start">
        <div className="space-y-4">
          <Tabs value={mode} onChange={setMode} options={[{ value: "player", label: "Jugador existente" }, { value: "profile", label: "Perfil hipotético" }]} />
          {mode === "player" ? (
            <>
              <PlayerPicker onPick={(p) => setPicked({ id: p.id, name: p.name })} />
              {picked && <div className="text-sm">Seleccionado: <span className="font-medium">{picked.name}</span></div>}
              <button className="btn-primary w-full" disabled={!picked || action.loading}
                onClick={() => picked && run({ player_id: picked.id }, picked.name)}><Calculator size={15} /> Estimar valor</button>
            </>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Edad">{num("age")}</Field>
                <Field label="Posición">
                  <Select value={form.position} onChange={(v) => setForm({ ...form, position: v })}>
                    {(meta.data?.positions || []).map((p) => <option key={p} value={p}>{positionLabel(p)}</option>)}
                  </Select>
                </Field>
                <div className="col-span-2">
                  <Field label="Liga">
                    <Select value={form.league_name} onChange={(v) => setForm({ ...form, league_name: v })}>
                      <option value="">Sin especificar</option>
                      {meta.playerLeagues.map((l) => <option key={l.id} value={l.name}>{l.name}</option>)}
                    </Select>
                  </Field>
                </div>
                <Field label="Partidos">{num("matches")}</Field>
                <Field label="Minutos">{num("minutes")}</Field>
                <Field label="Goles">{num("goals")}</Field>
                <Field label="Asistencias">{num("assists")}</Field>
                <Field label="Partidos del club">{num("team_matches")}</Field>
              </div>
              <button className="btn-primary w-full" disabled={action.loading}
                onClick={() => run({ profile: { ...form, league_name: form.league_name || null } }, "perfil hipotético")}>
                <Calculator size={15} /> Estimar valor
              </button>
            </>
          )}
        </div>
      </Card>
      <div>
        {action.error && <ErrorState error={action.error} />}
        {action.loading && <Loading label="Estimando" />}
        {!action.data && !action.error && !action.loading && (
          <Card><EmptyState title="Elegí un jugador o cargá un perfil" icon={<CircleDollarSign size={22} />}>
            El modelo (Gradient Boosting) estima el valor a partir de edad, posición, liga, minutos y producción. No usa el historial de valores.
          </EmptyState></Card>
        )}
        {action.data && !action.loading && (
          <Card title={action.data.subject.name ?? "Perfil hipotético"}
            subtitle={action.data.subject.season ? `Temporada ${meta.seasonLabel(action.data.subject.season)}` : undefined}
            actions={action.data.subject.player_id ? <Link className="text-xs text-accent hover:underline" to={`/players/${action.data.subject.player_id}`}>Ver perfil</Link> : undefined}>
            <EstimateResult r={action.data} />
          </Card>
        )}
        <div className="mt-3"><Badge>Modelo: ver detalle de evaluación en Model Performance</Badge></div>
      </div>
    </div>
  );
}

export default function MarketPage() {
  const [sp, setSp] = useSearchParams();
  const tab = (sp.get("tab") as "opportunities" | "value") || "opportunities";
  return (
    <div className="space-y-5">
      <PageHeader title="Market Opportunities"
        subtitle="Jugadores con rendimiento estadístico alto en relación con su valor registrado, y un estimador de valor de mercado."
        actions={<Tabs value={tab} onChange={(v) => setSp({ tab: v }, { replace: true })}
          options={[{ value: "opportunities", label: "Índice de oportunidad" }, { value: "value", label: "Estimador de valor" }]} />} />
      {tab === "opportunities" ? <Opportunities /> : <ValueEstimator />}
    </div>
  );
}
