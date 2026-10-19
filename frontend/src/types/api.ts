// Tipos de las respuestas de la API (espejo de backend/app/schemas y servicios).

export type Position = "Goalkeeper" | "Defender" | "Midfield" | "Attack";

export interface MetricDef {
  key: string;
  label: string;
  description: string;
  higher_is_better: boolean;
  scope: "individual" | "team_context" | "usage" | "profile";
  unit: "count" | "p90" | "ratio" | "per_match" | "years" | "eur";
}

export interface LeagueInfo {
  id: number;
  name: string;
  country: string | null;
  confederation: string | null;
  players: number;
  matches: number;
  first_season: number | null;
  last_season: number | null;
  has_player_stats: boolean;
  image_url?: string | null;
}

export interface Meta {
  app_name: string;
  metrics: MetricDef[];
  positions: Position[];
  position_features: Record<Position, string[]>;
  rating_weights: Record<Position, Record<string, number>>;
  rating_definition: string;
  opportunity_components: Record<string, string>;
  opportunity_default_weights: Record<string, number>;
  opportunity_definition: string;
  scouting_metrics: string[];
  data: {
    imported: boolean;
    imported_at: string | null;
    source: string | null;
    source_url: string | null;
    source_license: string | null;
    date_range: { first_match: string; last_match: string } | null;
    report: Record<string, any> | null;
    leagues: LeagueInfo[];
    player_seasons: number[];
    season_labels: Record<string, string>;
  };
}

export interface PlayerListItem {
  player_id: number;
  name: string;
  age: number | null;
  nationality: string | null;
  position: Position | null;
  sub_position: string | null;
  team_id: number | null;
  team_name: string | null;
  league_id: number | null;
  league_name: string | null;
  season: number;
  matches: number;
  minutes: number;
  goals: number;
  assists: number;
  goals_p90: number | null;
  assists_p90: number | null;
  market_value_eur: number | null;
  rating: number | null;
  rating_reliability: number | null;
  image_url?: string | null;
  team_image_url?: string | null;
}

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  season: number;
}

export interface SeasonStats {
  season: number;
  season_label: string;
  team_id: number | null;
  team_name: string | null;
  league_id: number | null;
  league_name: string | null;
  teams_count: number;
  age: number | null;
  matches: number;
  minutes: number;
  goals: number;
  assists: number;
  yellow_cards: number;
  red_cards: number;
  [metric: string]: any;
}

export interface MetricComparison {
  metric: string;
  label: string;
  value: number | null;
  percentile: number | null;
  position_median: number | null;
  position_p90: number | null;
  higher_is_better: boolean;
  scope: string;
}

export interface SimilarResult {
  player_id: number;
  name: string;
  team_name: string | null;
  league_name: string | null;
  age: number | null;
  minutes: number;
  market_value_eur: number | null;
  rating: number | null;
  similarity: number;
  image_url?: string | null;
  team_image_url?: string | null;
  values: Record<string, number | null>;
  imputed_features: string[];
  shared_traits: string[];
  main_differences: string[];
  explanation: string;
}

export interface SimilarResponse {
  position: Position;
  features: string[];
  pool_size: number;
  min_minutes?: number;
  target_values?: Record<string, number | null>;
  results: SimilarResult[];
  warnings: string[];
  index_note?: string;
}

export interface PlayerProfile {
  player: {
    id: number;
    name: string;
    date_of_birth: string | null;
    nationality: string | null;
    country_of_birth: string | null;
    position: Position | null;
    sub_position: string | null;
    foot: string | null;
    height_cm: number | null;
    current_team_id: number | null;
    current_team_name: string | null;
    current_league_name: string | null;
    market_value_eur: number | null;
    market_value_date: string | null;
    highest_market_value_eur: number | null;
    profile_url: string | null;
    image_url?: string | null;
    current_team_image_url?: string | null;
  };
  seasons: SeasonStats[];
  selected_season: number | null;
  valuations: { date: string; value_eur: number }[];
  position_comparison: {
    position: Position;
    reference_size: number;
    metrics: MetricComparison[];
    sample_warning: string | null;
  } | null;
  strengths: MetricComparison[];
  weaknesses: MetricComparison[];
  similar: SimilarResponse | null;
  value_estimate: {
    estimated_value_eur: number;
    typical_range_eur: [number, number];
    out_of_sample: boolean;
    notes: string[];
  } | null;
  data_quality: Record<string, any>;
  unavailable_metrics: string[];
  unavailable_reason: string;
}

export interface CompareResponse {
  players: { player_id: number; name: string; position: Position; sub_position: string | null;
    team_name: string | null; league_name: string | null; season: number; rating: number | null; image_url?: string | null }[];
  metrics: { metric: string; label: string; unit: MetricDef["unit"]; higher_is_better: boolean; scope: string;
    values: (number | null)[]; diff_vs_first: ({ type: "percent" | "points"; value: number } | null)[] }[];
  radar: { metrics: { key: string; label: string }[]; percentiles: Record<string, number | null>[]; normalization: string };
  unavailable_metrics: string[];
  unavailable_reason: string;
  notes: string[];
  same_position: boolean;
}

export interface ScoutingCandidate {
  player_id: number;
  name: string;
  position: Position;
  sub_position: string | null;
  team_name: string | null;
  league_name: string | null;
  age: number | null;
  minutes: number;
  market_value_eur: number | null;
  rating: number | null;
  score: number;
  data_coverage: number;
  image_url?: string | null;
  team_image_url?: string | null;
  percentiles: Record<string, number | null>;
  values: Record<string, number | null>;
  explanation: string;
}

export interface ScoutingResponse {
  candidates: ScoutingCandidate[];
  funnel: { step: string; remaining: number }[];
  weights: Record<string, number>;
  excluded_without_value: number;
  reference: string | null;
  season: number;
}

export interface Opportunity {
  player_id: number;
  name: string;
  position: Position;
  sub_position: string | null;
  team_name: string | null;
  league_name: string | null;
  age: number | null;
  minutes: number;
  matches: number;
  rating: number | null;
  market_value_eur: number | null;
  predicted_value_eur: number | null;
  score: number;
  confidence: number;
  data_coverage: number;
  uncertainty: "baja" | "media" | "alta";
  image_url?: string | null;
  team_image_url?: string | null;
  components: Record<string, number | null>;
  contributions: Record<string, number | null>;
  explanation: string;
}

export interface OpportunityResponse {
  results: Opportunity[];
  total: number;
  weights: Record<string, number>;
  components: Record<string, string>;
  excluded_without_value: number;
  notes: string[];
  disclaimer: string;
  season: number;
  methodology: string;
}

export interface ValueEstimate {
  subject: { type: "player" | "profile"; player_id?: number; name?: string; season?: number };
  estimated_value_eur: number;
  typical_range_eur: [number, number];
  registered_value_eur: number | null;
  difference_pct: number | null;
  reliable: boolean;
  notes: string[];
  model_metrics: { mae_eur?: number; rmse_eur?: number; median_abs_pct_error?: number };
  explanation: string;
}

export interface TeamListItem {
  id: number;
  name: string;
  league_id: number | null;
  league_name: string | null;
  country: string | null;
  last_season: number | null;
  elo: number | null;
  image_url?: string | null;
  league_image_url?: string | null;
}

export interface TeamSeasonSummary {
  season: number;
  season_label: string;
  league_name: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  points: number;
  points_per_match: number | null;
  goals_for_pm: number | null;
  goals_against_pm: number | null;
}

export interface TeamDetail {
  team: { id: number; name: string; league_id: number | null; league_name: string | null; country: string | null;
    stadium: string | null; stadium_seats: number | null; image_url?: string | null; league_image_url?: string | null };
  seasons: TeamSeasonSummary[];
  latest_splits: { home: TeamSeasonSummary; away: TeamSeasonSummary } | null;
  recent_matches: { date: string; venue: "home" | "away"; opponent_id: number; opponent: string; gf: number; ga: number;
    result: "W" | "D" | "L" }[];
  squad: { player_id: number; name: string; position: Position | null; age: number | null; minutes: number;
    goals: number; assists: number; rating: number | null; market_value_eur: number | null; image_url?: string | null }[];
  squad_note: string | null;
  elo_history: { date: string; elo: number }[] | null;
  current_elo: number | null;
}

export type Outcome = "home" | "draw" | "away";

export interface MatchPrediction {
  home_team: { id: number; name: string | null; league_name: string | null; image_url?: string | null };
  away_team: { id: number; name: string | null; league_name: string | null; image_url?: string | null };
  probabilities: Record<"poisson" | "logistic" | "baseline", Record<Outcome, number>>;
  expected_goals: { home: number; away: number };
  scorelines: { home: number; away: number; probability: number }[];
  team_context: Record<"home" | "away", { elo: number; matches: number; last_match: string | null;
    recent_gf: number | null; recent_ga: number | null; recent_points: number[] }>;
  neutral: boolean;
  data_as_of: string;
  warnings: string[];
  model_quality: { log_loss: number; baseline_log_loss: number; accuracy: number; baseline_accuracy: number;
    test_matches: number } | null;
  disclaimer: string;
}

export interface ModelRun {
  model_key: string;
  name: string;
  objective: string;
  trained_at: string;
  n_train: number;
  n_test: number;
  features: any;
  metrics: Record<string, any>;
  validation: string;
  limitations: string[];
}

export interface Overview {
  season: number;
  season_label: string;
  available_seasons: { year: number; label: string }[];
  kpis: {
    players: number; teams: number; teams_with_player_stats: number; average_age: number | null;
    total_market_value_eur: number | null; players_with_market_value: number; matches: number;
    leagues_with_player_stats: number;
  };
  positions: { position: string; players: number }[];
  age_distribution: { range: string; players: number }[];
  top_market_value: TopPlayer[];
  top_rating: TopPlayer[];
  top_rating_min_minutes: number;
  leagues: { league_id: number; league_name: string; players: number; image_url?: string | null; average_age: number | null;
    median_market_value_eur: number | null; total_market_value_eur: number | null; goals_per_match: number | null;
    home_win_pct: number | null; matches: number }[];
  evolution: { season: number; season_label: string; goals_per_match: number; home_win_pct: number; draw_pct: number;
    matches: number }[];
  evolution_note: string;
}

export interface TopPlayer {
  player_id: number;
  name: string;
  team_name: string | null;
  league_name: string | null;
  position: Position | null;
  age: number | null;
  minutes: number;
  rating: number | null;
  market_value_eur: number | null;
  goals: number;
  assists: number;
  image_url?: string | null;
  team_image_url?: string | null;
}

export interface SearchResult {
  players: { id: number; name: string; position: Position | null; team_name: string | null; image_url?: string | null }[];
  teams: { id: number; name: string; league_name: string | null; image_url?: string | null }[];
}

export interface ApiErrorBody {
  error?: string;
  message?: string;
  detail?: unknown;
}
