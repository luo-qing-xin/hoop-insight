import { useEffect, useState, type DependencyList } from "react";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
export const DEFAULT_SEASON = "2025-26";

type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue>;

export type ApiState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export type TeamGameSummary = {
  team_id?: number | null;
  abbreviation?: string | null;
  name?: string | null;
  city?: string | null;
  score?: number | null;
  wins?: number | null;
  losses?: number | null;
  win_pct?: number | null;
  recent_wins?: number | null;
};

export type GameSummary = {
  game_id: string;
  game_date?: string | null;
  game_time_utc?: string | null;
  status?: string | null;
  status_text?: string | null;
  matchup?: string | null;
  home_team?: TeamGameSummary | null;
  away_team?: TeamGameSummary | null;
  focus_score?: number;
  focus_reasons?: string[];
};

export type RecentGamesResponse = {
  season: string;
  days: number;
  games: GameSummary[];
};

export type TodayGamesResponse = {
  game_date: string;
  games: GameSummary[];
};

export type FocusGamesResponse = {
  season: string;
  game_date: string;
  games: GameSummary[];
};

export type GameReviewResponse = {
  ok: boolean;
  game_id: string;
  message?: string | null;
  basic_summary: Record<string, unknown>;
  team_comparison: Record<string, unknown>;
  top_players: Array<Record<string, unknown>>;
  game_flow: Array<{
    period?: number | null;
    game_clock?: string | null;
    home_score: number;
    away_score: number;
    score_margin: number;
  }>;
  key_moments: Array<Record<string, unknown>>;
};

export type PlayerLeaderboardParams = {
  season?: string;
  stat?: string;
  min_gp?: number;
  min_min?: number;
  team_abbr?: string;
};

export type PlayerLeaderboardEntry = {
  rank: number;
  player_id?: number | null;
  player_name: string;
  team_id?: number | null;
  team_abbr?: string | null;
  age?: number | null;
  gp?: number | null;
  min?: number | null;
  pts?: number | null;
  reb?: number | null;
  ast?: number | null;
  stl?: number | null;
  blk?: number | null;
  fg_pct?: number | null;
  fg3_pct?: number | null;
  ft_pct?: number | null;
  plus_minus?: number | null;
};

export type PlayerLeaderboardResponse = {
  season: string;
  stat: string;
  min_gp: number;
  min_min: number;
  team_abbr?: string | null;
  players: PlayerLeaderboardEntry[];
};

export type PlayerAdvancedParams = {
  season?: string;
  player_name?: string;
};

export type PlayerMetricComparison = {
  player_value?: number | null;
  league_average?: number | null;
  percentile_rank?: number | null;
};

export type PlayerAdvancedEntry = {
  PLAYER_ID?: number | null;
  PLAYER_NAME: string;
  TEAM_ABBREVIATION?: string | null;
  GP?: number | null;
  MIN?: number | null;
  OFF_RATING?: number | null;
  DEF_RATING?: number | null;
  NET_RATING?: number | null;
  AST_PCT?: number | null;
  REB_PCT?: number | null;
  USG_PCT?: number | null;
  TS_PCT?: number | null;
  EFG_PCT?: number | null;
  PACE?: number | null;
  PIE?: number | null;
  league_comparison?: Record<string, PlayerMetricComparison>;
};

export type PlayerAdvancedResponse = {
  season: string;
  player_name?: string | null;
  players: PlayerAdvancedEntry[];
};

export type PlayerProfileResponse = {
  season: string;
  player_id: number;
  player?: PlayerAdvancedEntry | null;
};

export type PlayerRadarResponse = {
  season: string;
  player_id: number;
  player_name?: string | null;
  team_abbr?: string | null;
  gp?: number | null;
  min?: number | null;
  min_gp: number;
  min_min: number;
  radar: Array<{
    key: string;
    label: string;
    value: number;
    metrics?: Array<{ metric: string; value?: number | null; score?: number | null }>;
  }>;
};

export type TeamModuleParams = {
  season?: string;
};

export type TeamKpi = {
  key: string;
  label: string;
  value?: string | number | null;
  rank?: number | null;
  description?: string | null;
};

export type TeamTableEntry = {
  rank?: number | null;
  team_id?: number | null;
  team_name?: string | null;
  team_abbr?: string | null;
  gp?: number | null;
  wins?: number | null;
  losses?: number | null;
  win_pct?: number | null;
  pts?: number | null;
  plus_minus?: number | null;
  off_rating?: number | null;
  def_rating?: number | null;
  net_rating?: number | null;
  efg_pct?: number | null;
  tov_pct?: number | null;
  oreb_pct?: number | null;
  ft_rate?: number | null;
  opp_efg_pct?: number | null;
  opp_tov_pct?: number | null;
  dreb_pct?: number | null;
  opp_ft_rate?: number | null;
  pace?: number | null;
  explanations?: Array<{
    key?: string | null;
    label?: string | null;
    value?: number | string | null;
    higher_is_better?: boolean | null;
    description?: string | null;
  }>;
};

export type TeamChart = {
  key: string;
  title: string;
  x_label?: string | null;
  y_label?: string | null;
  points: Array<{
    team_id?: number | null;
    team_abbr?: string | null;
    team_name?: string | null;
    label?: string | null;
    x?: number | null;
    y?: number | null;
    size?: number | null;
  }>;
};

export type TeamModuleResponse = {
  season: string;
  kpis: TeamKpi[];
  table: TeamTableEntry[];
  charts: TeamChart[];
};

export type ShotPoint = {
  loc_x?: number | null;
  loc_y?: number | null;
  shot_made_flag?: number | null;
  shot_type?: string | null;
  shot_zone_basic?: string | null;
  shot_zone_area?: string | null;
  shot_zone_range?: string | null;
  action_type?: string | null;
  points?: number | null;
};

export type ShotZoneSummary = {
  shot_zone_basic?: string | null;
  shot_zone_area?: string | null;
  shot_zone_range?: string | null;
  fga: number;
  fgm: number;
  fg_pct?: number | null;
  points: number;
  pps?: number | null;
  efficiency_level?: string | null;
};

export type ShotChartResponse = {
  season: string;
  player_id?: number | null;
  team_id?: number | null;
  shots: ShotPoint[];
  zones: ShotZoneSummary[];
  totals: { fga: number; fgm: number; fg_pct?: number | null; points: number; pps?: number | null };
};

export type ShotZoneResponse = {
  season: string;
  player_id?: number | null;
  team_id?: number | null;
  min_fga: number;
  zones: ShotZoneSummary[];
  totals: { fga: number; fgm: number; fg_pct?: number | null; points: number; pps?: number | null };
};

export type AskAiResponse = {
  answer?: string;
  signal?: string;
  confidence?: string;
  intent?: string | null;
  entities?: Record<string, unknown>;
  need_data?: string[];
  data?: unknown;
  [key: string]: unknown;
};

export type DataCenterDatasetSummary = {
  key: string;
  label: string;
  name: string;
  data_type: string;
  source: string;
  source_path: string;
  data_format: string;
  file_size: number;
  rows?: number | null;
  columns?: number | null;
  updated_at?: string | null;
  encoding?: string | null;
  status: string;
  error?: string | null;
  exists: boolean;
};

export type DataCenterOverview = {
  data_mode: string;
  data_source: string;
  data_file_count: number;
  total_rows: number;
  total_columns: number;
  recognized_table_count: number;
  latest_updated_at?: string | null;
  format_count: number;
  formats: string[];
  data_types: string[];
  missing_data_types: string[];
  scanned_directories: string[];
};

export type DataCenterSchemaField = {
  field_name: string;
  dtype: string;
  non_null_count: number;
  missing_count: number;
  missing_rate: number;
  sample_value: string;
  zh_explanation: string;
};

export type DataCenterDataset = {
  key: string;
  label: string;
  name: string;
  data_type: string;
  source: string;
  source_path: string;
  data_format: string;
  file_size: number;
  rows?: number | null;
  updated_at?: string | null;
  encoding?: string | null;
  status: string;
  error?: string | null;
  columns: string[];
  records: Array<Record<string, unknown>>;
  preview_records: Array<Record<string, unknown>>;
  schema: DataCenterSchemaField[];
  api_record_limit: number;
  is_truncated?: boolean;
  metadata: {
    rows: number;
    columns: number;
    missing_values: number;
    duplicate_rows: number;
    updated_at?: string | null;
    file_size: number;
    source_path: string;
    data_format: string;
    data_type: string;
    encoding?: string | null;
    status: string;
    error?: string | null;
    exists: boolean;
  };
};

function withDefaults(params: QueryParams = {}) {
  return { season: DEFAULT_SEASON, ...params };
}

function buildUrl(path: string, params?: QueryParams) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const href = `${API_BASE_URL}${normalizedPath}`;
  const absoluteBaseUrl = /^https?:\/\//i.test(API_BASE_URL);
  const url = absoluteBaseUrl ? new URL(href) : new URL(href, window.location.origin);

  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  return absoluteBaseUrl ? url.toString() : `${url.pathname}${url.search}`;
}

async function readError(response: Response) {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item: { msg?: string }) => item.msg ?? JSON.stringify(item)).join("; ");
    }
    if (typeof payload.message === "string") {
      return payload.message;
    }
  } catch {
    return response.statusText || "请求失败，请稍后重试。";
  }

  return response.statusText || "请求失败，请稍后重试。";
}

async function request<T>(path: string, options: RequestInit = {}, params?: QueryParams): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(buildUrl(path, params), {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }

  return response.json() as Promise<T>;
}

export function useApi<T>(loader: () => Promise<T>, deps: DependencyList): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({ data: null, loading: true, error: null });

  useEffect(() => {
    let active = true;
    setState((current) => ({ ...current, loading: true, error: null }));

    loader()
      .then((data) => {
        if (active) {
          setState({ data, loading: false, error: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setState({
            data: null,
            loading: false,
            error: error instanceof Error ? error.message : "数据加载失败，请稍后重试。",
          });
        }
      });

    return () => {
      active = false;
    };
  }, deps);

  return state;
}

export function getRecentGames(params?: { season?: string; days?: number }) {
  return request<RecentGamesResponse>("/api/games/recent", {}, withDefaults({ days: 14, ...params }));
}

export function getTodayGames() {
  return request<TodayGamesResponse>("/api/games/today");
}

export function getFocusGames() {
  return request<FocusGamesResponse>("/api/games/focus");
}

export function getGameReview(gameId: string) {
  return request<GameReviewResponse>(`/api/games/${encodeURIComponent(gameId)}/review`);
}

export function getPlayerLeaderboard(params?: PlayerLeaderboardParams) {
  return request<PlayerLeaderboardResponse>("/api/players/leaderboard", {}, withDefaults({ stat: "PTS", min_gp: 10, min_min: 15, ...params }));
}

export function getPlayerAdvanced(params?: PlayerAdvancedParams) {
  return request<PlayerAdvancedResponse>("/api/players/advanced", {}, withDefaults({ ...params }));
}

export function getPlayerProfile(playerId: number, season = DEFAULT_SEASON) {
  return request<PlayerProfileResponse>(`/api/players/${playerId}/profile`, {}, { season });
}

export function getPlayerRadar(playerId: number, params?: { season?: string; min_gp?: number; min_min?: number }) {
  return request<PlayerRadarResponse>(`/api/players/${playerId}/radar`, {}, withDefaults({ min_gp: 10, min_min: 15, ...params }));
}

export function getTeamOverview(params?: TeamModuleParams) {
  return request<TeamModuleResponse>("/api/teams/overview", {}, withDefaults({ ...params }));
}

export function getTeamOffense(params?: TeamModuleParams) {
  return request<TeamModuleResponse>("/api/teams/offense", {}, withDefaults({ ...params }));
}

export function getTeamDefense(params?: TeamModuleParams) {
  return request<TeamModuleResponse>("/api/teams/defense", {}, withDefaults({ ...params }));
}

export function getPlayerShotChart(playerId: number, season = DEFAULT_SEASON) {
  return request<ShotChartResponse>(`/api/shots/player/${playerId}`, {}, { season });
}

export function getTeamShotChart(teamId: number, season = DEFAULT_SEASON) {
  return request<ShotChartResponse>(`/api/shots/team/${teamId}`, {}, { season });
}

export function getPlayerShotZones(playerId: number, params?: { season?: string; min_fga?: number }) {
  return request<ShotZoneResponse>(`/api/shots/player/${playerId}/zones`, {}, withDefaults({ min_fga: 20, ...params }));
}

export function getTeamShotZones(teamId: number, params?: { season?: string; min_fga?: number }) {
  return request<ShotZoneResponse>(`/api/shots/team/${teamId}/zones`, {}, withDefaults({ min_fga: 20, ...params }));
}

export function askAI(question: string) {
  return request<AskAiResponse>("/api/ai/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export function getDataCenterDatasets() {
  return request<{ overview: DataCenterOverview; datasets: DataCenterDatasetSummary[] }>("/api/data-center/datasets");
}

export function getDataCenterDataset(datasetKey: string) {
  return request<DataCenterDataset>(`/api/data-center/datasets/${encodeURIComponent(datasetKey)}`);
}

export function getDataCenterDownloadUrl(datasetKey: string) {
  return buildUrl(`/api/data-center/datasets/${encodeURIComponent(datasetKey)}/download`);
}
