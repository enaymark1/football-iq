import { createContext, useContext, type ReactNode } from "react";
import { api } from "../services/api";
import type { Meta, MetricDef } from "../types/api";
import { useApi, type AsyncState } from "./useApi";

const MetaContext = createContext<AsyncState<Meta> | null>(null);

export function MetaProvider({ children }: { children: ReactNode }) {
  const state = useApi(api.meta, []);
  return <MetaContext.Provider value={state}>{children}</MetaContext.Provider>;
}

export function useMeta() {
  const ctx = useContext(MetaContext);
  if (!ctx) throw new Error("useMeta fuera de MetaProvider");
  const metricMap: Record<string, MetricDef> = {};
  ctx.data?.metrics.forEach((m) => (metricMap[m.key] = m));
  const seasonLabel = (s: number | null | undefined) =>
    s == null ? "—" : ctx.data?.data.season_labels[String(s)] ?? String(s);
  const playerLeagues = (ctx.data?.data.leagues || []).filter((l) => l.has_player_stats);
  return { ...ctx, metricMap, seasonLabel, playerLeagues };
}
