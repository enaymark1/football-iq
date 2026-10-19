import { AlertTriangle, CheckCircle2, Database } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { AXIS, GRID, tooltip } from "../components/charts";
import { Badge, Card, EmptyState, ErrorState, Loading, Notice, PageHeader } from "../components/ui";
import { OUTCOME_COLORS } from "../config";
import { useApi } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { api } from "../services/api";
import type { ModelRun } from "../types/api";
import { dateShort, eur, int, pct, positionLabel } from "../utils/format";

const OUT_LABEL: Record<string, string> = { home: "Local", draw: "Empate", away: "Visitante" };

function RunHeader({ run }: { run: ModelRun }) {
  const feats = Array.isArray(run.features) ? run.features : Object.entries(run.features).map(([k, v]) => `${positionLabel(k)}: ${(v as string[]).join(", ")}`);
  return (
    <div className="grid gap-4 text-sm md:grid-cols-2">
      <dl className="space-y-1.5">
        <div><dt className="label">Objetivo</dt><dd>{run.objective}</dd></div>
        <div className="flex gap-6">
          <div><dt className="label">Entrenado</dt><dd>{dateShort(run.trained_at)}</dd></div>
          <div><dt className="label">Obs. entrenamiento</dt><dd className="tabular">{int(run.n_train)}</dd></div>
          <div><dt className="label">Obs. evaluación</dt><dd className="tabular">{int(run.n_test)}</dd></div>
        </div>
        <div><dt className="label">Validación</dt><dd className="text-muted">{run.validation}</dd></div>
      </dl>
      <div className="space-y-3">
        <div><div className="label mb-1">Variables</div>
          <div className="flex flex-wrap gap-1">{feats.map((f: string) => <Badge key={f}>{f}</Badge>)}</div></div>
        <div><div className="label mb-1">Limitaciones conocidas</div>
          <ul className="list-disc space-y-0.5 pl-4 text-xs text-muted">{run.limitations.map((l) => <li key={l}>{l}</li>)}</ul></div>
      </div>
    </div>
  );
}

function MatchModel({ run }: { run: ModelRun }) {
  const m = run.metrics;
  const models = [["poisson", "Poisson + Elo"], ["logistic", "Logística multinomial"], ["baseline", "Baseline (frecuencias)"]];
  const cm = m.poisson.confusion_matrix;
  const total = cm.rows_true_cols_pred.flat().reduce((a: number, b: number) => a + b, 0);
  return (
    <div className="space-y-5">
      <RunHeader run={run} />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-sm">
          <thead><tr className="table-head"><th className="py-2">Modelo</th><th className="py-2 text-right">Log loss ↓</th><th className="py-2 text-right">Brier ↓</th>
            <th className="py-2 text-right">RPS ↓</th><th className="py-2 text-right">Accuracy ↑</th></tr></thead>
          <tbody>
            {models.map(([k, label]) => (
              <tr key={k} className="border-t border-line/40">
                <td className="py-2">{label}</td>
                <td className="tabular py-2 text-right">{m[k].log_loss.toFixed(4)}</td>
                <td className="tabular py-2 text-right">{m[k].brier.toFixed(4)}</td>
                <td className="tabular py-2 text-right">{m[k].rps.toFixed(4)}</td>
                <td className="tabular py-2 text-right">{pct(m[k].accuracy, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-[11px] text-faint">
          Evaluación: temporadas {m.split.test_seasons.join("–")} · frecuencias reales: local {pct(m.split.test_outcome_rates[0], 1)},
          empate {pct(m.split.test_outcome_rates[1], 1)}, visitante {pct(m.split.test_outcome_rates[2], 1)}.
          Error absoluto medio de goles esperados: local {m.poisson.goals_mae_home}, visitante {m.poisson.goals_mae_away}.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[320px_1fr]">
        <div>
          <div className="label mb-2">Matriz de confusión (Poisson)</div>
          <table className="w-full text-xs">
            <thead><tr><th className="p-1 text-left text-faint">Real ↓ / Pred. →</th>{cm.labels.map((l: string) => <th key={l} className="p-1 text-faint">{OUT_LABEL[l]}</th>)}</tr></thead>
            <tbody>
              {cm.rows_true_cols_pred.map((row: number[], i: number) => (
                <tr key={i}>
                  <td className="p-1 text-muted">{OUT_LABEL[cm.labels[i]]}</td>
                  {row.map((v, j) => (
                    <td key={j} className="tabular p-1 text-center">
                      <div className="rounded py-2" style={{ background: `rgba(57,135,229,${0.08 + (v / total) * 1.6})` }}>{int(v)}</div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-[11px] text-faint">El modelo casi nunca elige “empate” como resultado más probable: es lo habitual en fútbol, aunque asigna probabilidad de empate en cada partido.</p>
        </div>
        <div>
          <div className="label mb-2">Curvas de calibración (Poisson) · probabilidad predicha vs frecuencia observada</div>
          <div className="grid gap-3 sm:grid-cols-3">
            {(["home", "draw", "away"] as const).map((o) => (
              <div key={o}>
                <div className="mb-1 text-xs text-muted">{OUT_LABEL[o]}</div>
                <div className="h-44">
                  <ResponsiveContainer>
                    <LineChart data={m.poisson.calibration[o]} margin={{ left: -24, right: 6, top: 4 }}>
                      <CartesianGrid {...GRID} vertical />
                      <XAxis dataKey="predicted" type="number" domain={[0, 1]} {...AXIS} fontSize={9} tickFormatter={(v) => `${Math.round(v * 100)}`} />
                      <YAxis type="number" domain={[0, 1]} {...AXIS} fontSize={9} tickFormatter={(v) => `${Math.round(v * 100)}`} />
                      <Line data={[{ predicted: 0, observed: 0 }, { predicted: 1, observed: 1 }]} dataKey="observed" stroke="#4a505a" strokeWidth={1} dot={false} isAnimationActive={false} />
                      <Line dataKey="observed" stroke={OUTCOME_COLORS[o]} strokeWidth={2} dot={{ r: 3 }} />
                      <Tooltip content={tooltip((p) => {
                        const d = p[p.length - 1].payload;
                        return d.n ? { title: `Predicho ${pct(d.predicted, 1)}`, rows: [{ label: "Observado", value: pct(d.observed, 1) }, { label: "Partidos", value: int(d.n) }] } : null;
                      })} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-1 text-[11px] text-faint">La diagonal gris es la calibración perfecta. Solo se muestran tramos con 20+ partidos.</p>
        </div>
      </div>
    </div>
  );
}

function ValueModel({ run }: { run: ModelRun }) {
  const m = run.metrics;
  const rows = [["model", "Modelo (Gradient Boosting)"], ["baseline_group_median", "Baseline: mediana por liga, posición y edad"],
    ["reference_previous_value", "Referencia: repetir el valor previo (usa historial)"]];
  return (
    <div className="space-y-5">
      <RunHeader run={run} />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <thead><tr className="table-head"><th className="py-2">Método</th><th className="py-2 text-right">MAE</th><th className="py-2 text-right">RMSE</th>
            <th className="py-2 text-right">Error mediano</th><th className="py-2 text-right">Error % mediano</th><th className="py-2 text-right">Dentro de ×1,5</th></tr></thead>
          <tbody>
            {rows.map(([k, label]) => (
              <tr key={k} className="border-t border-line/40">
                <td className="py-2">{label}</td>
                <td className="tabular py-2 text-right">{eur(m[k].mae_eur)}</td>
                <td className="tabular py-2 text-right">{eur(m[k].rmse_eur)}</td>
                <td className="tabular py-2 text-right">{eur(m[k].median_ae_eur)}</td>
                <td className="tabular py-2 text-right">{m[k].median_abs_pct_error}%</td>
                <td className="tabular py-2 text-right">{m[k].within_factor_1_5_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Notice>{m.reference_previous_value.note} El modelo le gana claramente al baseline, pero no a conocer el valor anterior: no es un sustituto de una tasación.</Notice>
      <div>
        <div className="label mb-2">Error por posición (temporada de evaluación)</div>
        <div className="grid gap-2 sm:grid-cols-4">
          {Object.entries(m.by_position as Record<string, any>).map(([pos, v]) => (
            <div key={pos} className="rounded-md border border-line bg-bg/60 p-3 text-xs">
              <div className="font-medium text-ink">{positionLabel(pos)}</div>
              <div className="tabular text-muted">MAE {eur(v.mae_eur)} · error % mediano {v.median_abs_pct_error}% · n={int(v.n)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function SimilarityModel({ run }: { run: ModelRun }) {
  const m = run.metrics;
  const pos = Object.entries((m.by_position || {}) as Record<string, any>).map(([k, v]) => ({ position: positionLabel(k), ...v }));
  return (
    <div className="space-y-5">
      <RunHeader run={run} />
      <div className="grid gap-3 sm:grid-cols-4">
        <div className="rounded-md border border-line bg-bg/60 p-3"><div className="label">Hit@10</div><div className="tabular text-xl font-semibold">{pct(m.hit_at_10, 1)}</div><div className="text-[11px] text-muted">azar: {pct(m.random_hit_at_10, 1)}</div></div>
        <div className="rounded-md border border-line bg-bg/60 p-3"><div className="label">Hit@1</div><div className="tabular text-xl font-semibold">{pct(m.hit_at_1, 1)}</div></div>
        <div className="rounded-md border border-line bg-bg/60 p-3"><div className="label">Puesto mediano</div><div className="tabular text-xl font-semibold">{m.median_rank}</div><div className="text-[11px] text-muted">percentil {m.median_percentile_rank}% del grupo</div></div>
        <div className="rounded-md border border-line bg-bg/60 p-3"><div className="label">Consultas</div><div className="tabular text-xl font-semibold">{int(m.queries)}</div></div>
      </div>
      {pos.length > 0 && (
        <div className="h-48">
          <ResponsiveContainer>
            <ScatterChart margin={{ left: -10, right: 16, top: 6 }}>
              <CartesianGrid {...GRID} vertical />
              <XAxis type="category" dataKey="position" {...AXIS} allowDuplicatedCategory={false} />
              <YAxis type="number" dataKey="hit_at_10" {...AXIS} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
              <ZAxis range={[90, 90]} />
              <Tooltip content={tooltip((p) => ({ title: p[0].payload.position, rows: [
                { label: "Hit@10", value: pct(p[0].payload.hit_at_10, 1) }, { label: "Azar", value: pct(p[0].payload.random_hit_at_10, 1) },
                { label: "Consultas", value: int(p[0].payload.queries) }] }))} />
              <Scatter data={pos} fill="var(--series-1)" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
      <Notice>Señal débil pero real (≈{(m.hit_at_10 / m.random_hit_at_10).toFixed(1).replace(".", ",")}× el azar): con pocas variables, el perfil de una temporada a la siguiente cambia bastante. Usalo para generar ideas, no como veredicto.</Notice>
    </div>
  );
}

function DataQuality() {
  const meta = useMeta();
  const r = meta.data?.data.report;
  if (!r) return <EmptyState title="No hay informe de importación" />;
  return (
    <div className="space-y-4 text-sm">
      <div className="grid gap-3 md:grid-cols-3">
        <div><div className="label">Fuente</div><div>{meta.data?.data.source}</div>
          <a className="text-xs text-accent hover:underline" href={meta.data?.data.source_url ?? "#"} target="_blank" rel="noreferrer">{meta.data?.data.source_url}</a>
          <div className="text-xs text-muted">Licencia {meta.data?.data.source_license}</div></div>
        <div><div className="label">Período</div><div>{dateShort(r.date_range?.first_match)} – {dateShort(r.date_range?.last_match)}</div>
          <div className="text-xs text-muted">Importado {dateShort(r.imported_at)}</div></div>
        <div><div className="label">Cobertura</div>
          <div className="text-xs text-muted">Partidos con apariciones de jugadores: {r.coverage.matches_with_appearances_pct}%</div>
          <div className="text-xs text-muted">Jugadores con valor de mercado: {r.coverage.players_with_market_value_pct}%</div></div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <div className="label mb-1">Registros importados</div>
          <table className="w-full text-xs"><tbody>
            {Object.entries(r.tables as Record<string, any>).map(([k, v]) => (
              <tr key={k} className="border-t border-line/40"><td className="py-1.5 text-muted">{k}</td>
                <td className="tabular py-1.5 text-right">{v.raw != null ? `${int(v.raw)} crudos → ` : ""}{int(v.imported ?? v.aggregated_rows)}{v.aggregated_rows ? " usadas" : ""}</td></tr>
            ))}
          </tbody></table>
        </div>
        <div>
          <div className="label mb-1">Filas descartadas o corregidas</div>
          <table className="w-full text-xs"><tbody>
            {Object.entries(r.dropped as Record<string, number>).map(([k, v]) => (
              <tr key={k} className="border-t border-line/40"><td className="py-1.5 text-muted">{k}</td>
                <td className="py-1.5 text-right">{v === 0 ? <CheckCircle2 size={13} className="ml-auto text-good" /> : <span className="tabular">{int(v)}</span>}</td></tr>
            ))}
          </tbody></table>
        </div>
      </div>
      <div>
        <div className="label mb-1">Faltantes en campos clave</div>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(r.missing_pct as Record<string, Record<string, number>>).flatMap(([table, cols]) =>
            Object.entries(cols).map(([c, v]) => <Badge key={table + c} tone={v > 10 ? "warning" : "neutral"}>{table}.{c}: {v}%</Badge>))}
        </div>
      </div>
      {r.coverage.low_appearance_coverage?.length > 0 && (
        <Notice tone="warning" title="Ligas sin estadísticas de jugadores en la fuente">
          {Array.from(new Set((r.coverage.low_appearance_coverage as { league: string }[]).map((x) => x.league))).join(", ")}: la fuente
          trae los resultados pero no las apariciones de jugadores. Se usan en Teams y Match Predictor.
        </Notice>
      )}
    </div>
  );
}

export default function ModelsPage() {
  const { data, error, loading, reload } = useApi(api.models, []);
  const meta = useMeta();
  const byKey = Object.fromEntries((data || []).map((r) => [r.model_key, r]));
  return (
    <div className="space-y-5">
      <PageHeader title="Model Performance" subtitle="Resultados reales de la última evaluación guardada de cada modelo, más el informe de calidad de los datos." />
      {error && <ErrorState error={error} onRetry={reload} />}
      {loading && <Loading />}
      {data && data.length === 0 && (
        <Card><EmptyState title="No hay modelos entrenados" icon={<AlertTriangle size={22} />}>Corré <code className="font-mono">python scripts/train_models.py</code> desde la raíz del proyecto.</EmptyState></Card>
      )}
      {byKey.match_predictor && <Card title={byKey.match_predictor.name}><MatchModel run={byKey.match_predictor} /></Card>}
      {byKey.market_value && <Card title={byKey.market_value.name}><ValueModel run={byKey.market_value} /></Card>}
      {byKey.similarity && <Card title={byKey.similarity.name}><SimilarityModel run={byKey.similarity} /></Card>}
      <Card title="Métricas propias (no son modelos entrenados)">
        <div className="grid gap-4 text-sm md:grid-cols-2">
          <div><div className="label mb-1">FIQ Rating</div><p className="text-muted">{meta.data?.rating_definition}</p>
            <div className="mt-2 space-y-1 text-xs text-muted">
              {Object.entries(meta.data?.rating_weights || {}).map(([pos, w]) => (
                <div key={pos}><span className="text-ink">{positionLabel(pos)}:</span> {Object.entries(w).map(([k, v]) => `${meta.metricMap[k]?.label} ${Math.round(v * 100)}%`).join(" · ")}</div>
              ))}
            </div></div>
          <div><div className="label mb-1">Índice de Oportunidad Estadística</div>
            <pre className="whitespace-pre-wrap font-sans text-xs leading-relaxed text-muted">{meta.data?.opportunity_definition?.trim()}</pre></div>
        </div>
      </Card>
      <Card title={<span className="inline-flex items-center gap-1.5"><Database size={14} /> Calidad de los datos</span>}><DataQuality /></Card>
    </div>
  );
}
