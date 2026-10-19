import { API_BASE } from "../config";
import type {
  ApiErrorBody, CompareResponse, MatchPrediction, Meta, ModelRun, OpportunityResponse, Overview, Paged,
  PlayerListItem, PlayerProfile, ScoutingResponse, SearchResult, SimilarResponse, TeamDetail, TeamListItem,
  ValueEstimate,
} from "../types/api";

export class ApiError extends Error {
  constructor(public status: number, message: string, public body?: ApiErrorBody) {
    super(message);
  }
}

function describeValidation(detail: unknown): string | null {
  if (!Array.isArray(detail)) return null;
  return detail
    .map((d: any) => `${(d.loc || []).filter((x: unknown) => x !== "body").join(".")}: ${d.msg}`)
    .join(" · ");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el backend. ¿Está corriendo en http://127.0.0.1:8000?");
  }
  if (!res.ok) {
    let body: ApiErrorBody | undefined;
    try {
      body = await res.json();
    } catch {
      /* respuesta sin JSON */
    }
    const msg = body?.message || describeValidation(body?.detail) || `Error ${res.status}`;
    throw new ApiError(res.status, msg, body);
  }
  return res.json() as Promise<T>;
}

type Query = Record<string, string | number | boolean | undefined | null | (string | number)[]>;

function qs(params: Query): string {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    if (Array.isArray(v)) v.forEach((x) => sp.append(k, String(x)));
    else sp.set(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

const post = <T,>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  health: () => request<{ status: string; data_imported: boolean; models_trained: string[] }>("/api/health"),
  meta: () => request<Meta>("/api/meta"),
  overview: (season?: number) => request<Overview>(`/api/overview${qs({ season })}`),
  search: (q: string) => request<SearchResult>(`/api/search${qs({ q })}`),
  players: (params: Query) => request<Paged<PlayerListItem>>(`/api/players${qs(params)}`),
  playerFilters: (season?: number) =>
    request<{ season: number; positions: string[]; nationalities: string[]; sortable: string[] }>(
      `/api/players/filters${qs({ season })}`),
  player: (id: number, season?: number) => request<PlayerProfile>(`/api/players/${id}${qs({ season })}`),
  similar: (id: number, params: Query) => request<SimilarResponse>(`/api/players/${id}/similar${qs(params)}`),
  compare: (player_ids: number[], season?: number) => post<CompareResponse>("/api/players/compare", { player_ids, season }),
  scouting: (body: unknown) => post<ScoutingResponse>("/api/scouting/search", body),
  opportunities: (body: unknown) => post<OpportunityResponse>("/api/market/opportunities", body),
  valueEstimate: (body: unknown) => post<ValueEstimate>("/api/market/value-estimate", body),
  teams: (params: Query = {}) => request<TeamListItem[]>(`/api/teams${qs(params)}`),
  team: (id: number) => request<TeamDetail>(`/api/teams/${id}`),
  predict: (home_team_id: number, away_team_id: number, neutral: boolean) =>
    post<MatchPrediction>("/api/matches/predict", { home_team_id, away_team_id, neutral }),
  models: () => request<ModelRun[]>("/api/models/performance"),
};
