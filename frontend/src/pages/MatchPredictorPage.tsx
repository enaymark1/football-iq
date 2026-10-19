import { ArrowLeftRight, Target } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AXIS, GRID, Legend, tooltip } from "../components/charts";
import { TeamSelect } from "../components/Pickers";
import { Avatar, Card, cx, EmptyState, ErrorState, Field, Loading, Notice, PageHeader, Select } from "../components/ui";
import { OUTCOME_COLORS } from "../config";
import { logActivity } from "../hooks/useActivity";
import { useAction, useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { api } from "../services/api";
import type { MatchPrediction, Outcome } from "../types/api";
import { dateShort, dec2, pct } from "../utils/format";

const OUTCOME_LABEL: Record<Outcome, string> = { home: "Local", draw: "Empate", away: "Visitante" };
const MODEL_LABEL = { poisson: "Poisson + Elo (principal)", logistic: "Logística multinomial", baseline: "Baseline (frecuencias históricas)" };

function ProbabilityBar({ probs, names }: { probs: Record<Outcome, number>; names: [string, string] }) {
  const order: Outcome[] = ["home", "draw", "away"];
  return (
    <div>
      <div className="flex h-10 gap-[2px] overflow-hidden rounded-md">
        {order.map((o) => (
          <div key={o} className="flex items-center justify-center text-xs font-semibold text-white/95"
            style={{ width: `${probs[o] * 100}%`, background: OUTCOME_COLORS[o], minWidth: probs[o] > 0.04 ? 0 : 4 }}
            title={`${OUTCOME_LABEL[o]}: ${pct(probs[o], 1)}`}>
            {probs[o] >= 0.1 && pct(probs[o], 0)}
          </div>
        ))}
      </div>
      <div className="mt-2 grid grid-cols-3 text-xs">
        <div><div className="font-medium text-ink">{names[0]}</div><div className="tabular text-muted">gana {pct(probs.home, 1)}</div></div>
        <div className="text-center"><div className="font-medium text-ink">Empate</div><div className="tabular text-muted">{pct(probs.draw, 1)}</div></div>
        <div className="text-right"><div className="font-medium text-ink">{names[1]}</div><div className="tabular text-muted">gana {pct(probs.away, 1)}</div></div>
      </div>
    </div>
  );
}

function Form({ pts }: { pts: number[] }) {
  return (
    <div className="flex gap-1">
      {pts.map((p, i) => {
        const r = p === 3 ? "G" : p === 1 ? "E" : "P";
        return <span key={i} title={r === "G" ? "Ganó" : r === "E" ? "Empató" : "Perdió"}
          className={cx("flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold",
            r === "G" ? "bg-good/20 text-[#5fd35f]" : r === "E" ? "bg-raised text-muted" : "bg-critical/20 text-[#f08080]")}>{r}</span>;
      })}
    </div>
  );
}

function Result({ r }: { r: MatchPrediction }) {
  const names: [string, string] = [r.home_team.name ?? "Local", r.away_team.name ?? "Visitante"];
  const scoreRows = r.scorelines.map((s) => ({ label: `${s.home}–${s.away}`, p: s.probability }));
  return (
    <div className="space-y-5">
      {r.warnings.map((w) => <Notice key={w} tone="warning">{w}</Notice>)}
      <Card title={`${names[0]} vs ${names[1]}${r.neutral ? " · cancha neutral" : ""}`}
        subtitle={`Modelo principal: Poisson con Elo y forma reciente · datos hasta ${dateShort(r.data_as_of)}`}>
        <ProbabilityBar probs={r.probabilities.poisson} names={names} />
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {(["home", "away"] as const).map((side, i) => {
            const c = r.team_context[side];
            return (
              <div key={side} className="rounded-md border border-line bg-bg/60 p-3">
                <div className="flex items-center justify-between">
                  <Link to={`/teams/${i === 0 ? r.home_team.id : r.away_team.id}`} className="link flex items-center gap-2 text-sm font-semibold">
                    <Avatar name={names[i]} src={(i === 0 ? r.home_team : r.away_team).image_url} size={28} tone="team" />{names[i]}
                  </Link>
                  <span className="label">{side === "home" && !r.neutral ? "Local" : side === "away" && !r.neutral ? "Visitante" : "Neutral"}</span>
                </div>
                <div className="tabular mt-2 text-3xl font-semibold">{dec2(r.expected_goals[side])}</div>
                <div className="text-[11px] text-muted">goles esperados</div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  <div><div className="text-faint">Elo</div><div className="tabular">{c.elo.toFixed(0)}</div></div>
                  <div><div className="text-faint">GF/GC últ. 10</div><div className="tabular">{dec2(c.recent_gf)} / {dec2(c.recent_ga)}</div></div>
                  <div><div className="text-faint">Partidos</div><div className="tabular">{c.matches}</div></div>
                </div>
                <div className="mt-2 flex items-center justify-between text-[11px] text-faint">Últimos 5 <Form pts={c.recent_points} /></div>
              </div>
            );
          })}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card title="Resultados exactos más probables" subtitle="Distribución de Poisson con los goles esperados">
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={scoreRows} margin={{ left: -14, right: 8 }}>
                <CartesianGrid {...GRID} />
                <XAxis dataKey="label" {...AXIS} />
                <YAxis {...AXIS} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                <Tooltip cursor={{ fill: "rgb(255 255 255 / 0.03)" }}
                  content={tooltip((p) => ({ title: `Resultado ${p[0].payload.label}`, rows: [{ label: "Probabilidad", value: pct(p[0].value, 1) }] }))} />
                <Bar dataKey="p" fill="var(--series-1)" radius={[4, 4, 0, 0]} maxBarSize={34} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Comparación de modelos" subtitle="Los tres se evaluaron con las mismas temporadas recientes">
          <table className="w-full text-sm">
            <thead><tr className="table-head"><th className="py-2">Modelo</th><th className="py-2 text-right">Local</th><th className="py-2 text-right">Empate</th><th className="py-2 text-right">Visitante</th></tr></thead>
            <tbody>
              {(Object.keys(MODEL_LABEL) as (keyof typeof MODEL_LABEL)[]).map((m) => (
                <tr key={m} className="border-t border-line/40">
                  <td className="py-2">{MODEL_LABEL[m]}</td>
                  {(["home", "draw", "away"] as Outcome[]).map((o) => <td key={o} className="tabular py-2 text-right">{pct(r.probabilities[m][o], 1)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
          {r.model_quality && (
            <p className="mt-4 text-xs leading-relaxed text-muted">
              En la evaluación ({r.model_quality.test_matches.toLocaleString("es-AR")} partidos), el modelo principal tuvo log loss {r.model_quality.log_loss.toFixed(3)} vs
              {" "}{r.model_quality.baseline_log_loss.toFixed(3)} del baseline, y acertó el resultado más probable en el {pct(r.model_quality.accuracy, 1)} de los partidos
              (baseline {pct(r.model_quality.baseline_accuracy, 1)}). <Link to="/models" className="text-accent hover:underline">Ver evaluación completa</Link>
            </p>
          )}
        </Card>
      </div>
      <Notice>{r.disclaimer} El modelo solo conoce resultados y goles anteriores: no sabe de lesiones, alineaciones ni transferencias.</Notice>
    </div>
  );
}

export default function MatchPredictorPage() {
  const meta = useMeta();
  const [league, setLeague] = useState("");
  const teams = useApi(() => api.teams(league ? { league_id: league } : {}), [league]);
  const [home, setHome] = useState<number | null>(null);
  const [away, setAway] = useState<number | null>(null);
  const [neutral, setNeutral] = useState(false);
  const action = useAction(api.predict);
  const list = teams.data ?? [];

  const predict = async () => {
    if (!home || !away) return;
    const r = await action.run(home, away, neutral);
    if (r) logActivity({ kind: "match", label: `${r.home_team.name} vs ${r.away_team.name}`,
      detail: `Local ${pct(r.probabilities.poisson.home)} · Empate ${pct(r.probabilities.poisson.draw)} · Visitante ${pct(r.probabilities.poisson.away)}`,
      path: "/match-predictor" });
  };

  return (
    <div className="space-y-5">
      <PageHeader title="Match Predictor"
        subtitle="Probabilidades de victoria, empate y derrota a partir de la historia previa de cada equipo. Las variables se calculan solo con partidos anteriores y el modelo se evaluó cronológicamente." />
      <Card>
        <div className="grid items-end gap-3 sm:grid-cols-2 2xl:grid-cols-[180px_minmax(0,1fr)_auto_minmax(0,1fr)_auto_auto]">
          <Field label="Liga">
            <Select value={league} onChange={(v) => { setLeague(v); setHome(null); setAway(null); }}>
              <option value="">Todas</option>
              {(meta.data?.data.leagues || []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </Select>
          </Field>
          <Field label="Local"><TeamSelect teams={list} value={home} onChange={setHome} label="Equipo local" /></Field>
          <button className="btn-ghost h-9 px-2.5" aria-label="Invertir localía" title="Invertir localía"
            onClick={() => { setHome(away); setAway(home); }}><ArrowLeftRight size={15} /></button>
          <Field label="Visitante"><TeamSelect teams={list} value={away} onChange={setAway} label="Equipo visitante" /></Field>
          <label className="flex h-9 items-center gap-2 text-sm text-muted">
            <input type="checkbox" className="accent-[rgb(var(--accent))]" checked={neutral} onChange={(e) => setNeutral(e.target.checked)} />
            Cancha neutral
          </label>
          <button className="btn-primary" disabled={!home || !away || home === away || action.loading} onClick={predict}>
            <Target size={15} /> Predecir
          </button>
        </div>
        {home && away && home === away && <p className="mt-2 text-xs text-warning">Elegí dos equipos distintos.</p>}
        <div className="mt-3"><Legend items={(["home", "draw", "away"] as Outcome[]).map((o) => ({ label: OUTCOME_LABEL[o], color: OUTCOME_COLORS[o] }))} /></div>
      </Card>
      {teams.error && <ErrorState error={teams.error} onRetry={teams.reload} />}
      {action.error && <ErrorState error={action.error} />}
      {action.loading && <Loading label="Calculando probabilidades" />}
      {!action.data && !action.loading && !action.error && (
        <Card><EmptyState title="Elegí dos equipos" icon={<Target size={22} />}>Funciona mejor con equipos de la misma liga: el Elo y la forma se miden dentro de cada liga.</EmptyState></Card>
      )}
      {action.data && !action.loading && <Result r={action.data} />}
    </div>
  );
}
