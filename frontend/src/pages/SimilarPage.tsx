import { GitCompareArrows, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PlayerPicker } from "../components/Pickers";
import { Avatar, Badge, Card, cx, EmptyState, ErrorState, Field, Loading, Notice, NumberInput, PageHeader } from "../components/ui";
import { logActivity } from "../hooks/useActivity";
import { useApi, useDebounced } from "../hooks/useApi";
import { useMeta } from "../hooks/useMeta";
import { api } from "../services/api";
import { dec1, eur, int, metricValue, positionLabel } from "../utils/format";

const SELECTABLE = ["goals_p90", "assists_p90", "goal_contrib_p90", "goal_involvement_share", "minutes_share", "cards_p90",
  "team_ppm", "team_ga_pm", "clean_sheet_rate", "age"];

export default function SimilarPage() {
  const [sp, setSp] = useSearchParams();
  const id = Number(sp.get("id")) || 0;
  const meta = useMeta();
  const [features, setFeatures] = useState<string[] | null>(null);
  const [minMinutes, setMinMinutes] = useState<number | "">(900);
  const dMin = useDebounced(minMinutes, 400);
  const profile = useApi(() => api.player(id), [id], id > 0);
  const position = profile.data?.player.position;
  useEffect(() => setFeatures(null), [id]);
  const feats = features ?? (position ? meta.data?.position_features[position] ?? [] : []);
  const sim = useApi(() => api.similar(id, { k: 10, min_minutes: dMin === "" ? 0 : dMin, features: features ?? undefined }),
    [id, dMin, (features ?? []).join(",")], id > 0 && feats.length >= 2);

  useEffect(() => {
    if (sim.data && profile.data) logActivity({ kind: "similar", label: `Similares a ${profile.data.player.name}`,
      detail: `${sim.data.results.length} perfiles · ${positionLabel(sim.data.position)}`, path: `/similar?id=${id}` });
  }, [sim.data]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = (k: string) => setFeatures(feats.includes(k) ? feats.filter((f) => f !== k) : [...feats, k]);

  return (
    <div className="space-y-5">
      <PageHeader title="Similar Players"
        subtitle="Los 10 perfiles estadísticos más parecidos de la misma posición, según similitud coseno sobre métricas estandarizadas." />
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
        <Card title="Jugador de referencia" className="self-start">
          <div className="space-y-4">
            <PlayerPicker onPick={(p) => setSp({ id: String(p.id) })} placeholder="Buscar jugador…" />
            {profile.data && (
              <div className="flex items-center gap-3 rounded-md border border-line bg-bg/60 p-3">
                <Avatar name={profile.data.player.name} src={profile.data.player.image_url} size={36} />
                <div className="min-w-0">
                  <Link to={`/players/${id}`} className="link block truncate font-medium">{profile.data.player.name}</Link>
                  <div className="text-xs text-muted">{positionLabel(position)} · {profile.data.player.current_team_name}</div>
                </div>
              </div>
            )}
            {position && (
              <>
                <Field label="Variables consideradas" hint="Por defecto, las de su posición. Mínimo 2.">
                  <div className="flex flex-wrap gap-1.5">
                    {SELECTABLE.map((k) => (
                      <button key={k} onClick={() => toggle(k)} aria-pressed={feats.includes(k)}
                        className={cx("rounded-md border px-2 py-1 text-xs transition-colors",
                          feats.includes(k) ? "border-accent/40 bg-accent/10 text-accent" : "border-line text-muted hover:text-ink")}>
                        {meta.metricMap[k]?.label}
                      </button>
                    ))}
                  </div>
                </Field>
                {features && <button className="text-xs text-accent hover:underline" onClick={() => setFeatures(null)}>Volver a las variables de la posición</button>}
                <Field label="Minutos mínimos de los candidatos"><NumberInput value={minMinutes} min={0} step={90} onChange={setMinMinutes} /></Field>
              </>
            )}
            <Notice>El índice va de −1 a 1 (se muestra ×100). Es una medida geométrica entre perfiles, no una probabilidad de que dos jugadores “sean iguales”.</Notice>
          </div>
        </Card>

        <div className="space-y-4">
          {!id && <Card><EmptyState title="Elegí un jugador" icon={<Sparkles size={22} />}>Buscá un jugador para ver los perfiles más parecidos.</EmptyState></Card>}
          {profile.error && <ErrorState error={profile.error} />}
          {feats.length < 2 && id > 0 && <Notice tone="warning">Elegí al menos 2 variables.</Notice>}
          {sim.error && <ErrorState error={sim.error} onRetry={sim.reload} />}
          {sim.loading && !sim.data && <Loading label="Buscando perfiles" />}
          {sim.data && id > 0 && feats.length >= 2 && (
            <>
              {sim.data.warnings.map((w) => <Notice key={w} tone="warning">{w}</Notice>)}
              <Card title={`${sim.data.results.length} perfiles más similares`}
                subtitle={`${int(sim.data.pool_size)} ${positionLabel(sim.data.position).toLowerCase()}s candidatos con ${int(sim.data.min_minutes ?? 0)}+ minutos en la misma temporada`}
                bodyClass="p-0 sm:p-0">
                <div className="overflow-x-auto">
                  <table className={cx("w-full min-w-[760px] text-sm", sim.loading && "opacity-60")}>
                    <thead>
                      <tr className="table-head border-b border-line/70">
                        <th className="px-4 py-2.5">Jugador</th>
                        <th className="px-3 py-2.5">Índice de similitud</th>
                        {sim.data.features.map((f) => <th key={f} className="px-3 py-2.5 text-right">{meta.metricMap[f]?.label}</th>)}
                        <th className="px-3 py-2.5 text-right">Valor</th>
                        <th className="px-3 py-2.5" />
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-line/70 bg-accent/[0.04]">
                        <td className="px-4 py-2 font-medium">{profile.data?.player.name} <Badge tone="accent">referencia</Badge></td>
                        <td className="px-3 py-2 text-xs text-muted">—</td>
                        {sim.data.features.map((f) => <td key={f} className="tabular px-3 py-2 text-right">{metricValue(sim.data!.target_values?.[f], meta.metricMap[f]?.unit)}</td>)}
                        <td className="tabular px-3 py-2 text-right">{eur(profile.data?.player.market_value_eur)}</td>
                        <td />
                      </tr>
                      {sim.data.results.map((r) => (
                        <tr key={r.player_id} className="border-b border-line/40 align-top last:border-0 hover:bg-raised/30">
                          <td className="px-4 py-2.5">
                            <div className="flex items-center gap-2">
                              <Avatar name={r.name} src={r.image_url} size={26} />
                              <Link to={`/players/${r.player_id}`} className="link font-medium">{r.name}</Link>
                            </div>
                            <div className="text-[11px] text-muted">{r.team_name} · {r.league_name} · {dec1(r.age)} años</div>
                            <div className="mt-1 max-w-xs text-[11px] leading-snug text-muted">{r.explanation}</div>
                            {r.imputed_features.length > 0 && <div className="mt-1 text-[11px] text-warning">Sin dato en {r.imputed_features.map((f) => meta.metricMap[f]?.label).join(", ")} (se usó la mediana)</div>}
                          </td>
                          <td className="px-3 py-2.5">
                            <div className="flex items-center gap-2">
                              <div className="h-1.5 w-20 overflow-hidden rounded-full bg-raised">
                                <div className="h-full rounded-full bg-accent" style={{ width: `${Math.max(0, r.similarity) * 100}%` }} />
                              </div>
                              <span className="tabular text-xs">{(r.similarity * 100).toFixed(0)}</span>
                            </div>
                          </td>
                          {sim.data!.features.map((f) => (
                            <td key={f} className={cx("tabular px-3 py-2.5 text-right", r.shared_traits.includes(f) ? "text-accent" : "text-muted")}>
                              {metricValue(r.values[f], meta.metricMap[f]?.unit)}
                            </td>
                          ))}
                          <td className="tabular px-3 py-2.5 text-right">{eur(r.market_value_eur)}</td>
                          <td className="px-3 py-2.5">
                            <Link to={`/compare?ids=${id},${r.player_id}`} className="btn-ghost h-7 px-2 text-xs" title="Comparar"><GitCompareArrows size={13} /></Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
              <p className="text-[11px] text-faint">En verde, las variables donde ambos jugadores se apartan del promedio en la misma dirección (rasgo compartido).</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
