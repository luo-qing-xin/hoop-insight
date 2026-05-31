import { COMMON_COPY, KPI_LABELS, KPI_TRENDS, metricLabel, shotZoneLabel, statusLabel } from "../constants/zhLabels";
import { translateTeamName } from "../utils/nameTranslations";
import type { GameSummary, ShotZoneSummary, TeamKpi, TeamTableEntry } from "./client";

export type TableRow = Record<string, string | number>;
export type ChartPoint = { label: string; value: number };

export function formatNumber(value: unknown, digits = 1) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : COMMON_COPY.none;
}

export function formatPercent(value: unknown, digits = 1) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return COMMON_COPY.none;
  }

  return `${(value <= 1 ? value * 100 : value).toFixed(digits)}%`;
}

export function formatKpiValue(value: TeamKpi["value"]) {
  if (typeof value === "number") {
    return Math.abs(value) < 1 ? formatPercent(value) : formatNumber(value);
  }

  return value ? String(value) : COMMON_COPY.none;
}

export function gameMatchup(game: GameSummary) {
  if (game.matchup) {
    return game.matchup;
  }

  const away = translateTeamName(game.away_team?.abbreviation ?? game.away_team?.name ?? "客队", "short");
  const home = translateTeamName(game.home_team?.abbreviation ?? game.home_team?.name ?? "主队", "short");
  const awayScore = game.away_team?.score;
  const homeScore = game.home_team?.score;
  const score = typeof awayScore === "number" && typeof homeScore === "number" ? ` ${awayScore} - ${homeScore}` : "";

  return `${away} @ ${home}${score}`;
}

export function formatDate(value?: string | null) {
  if (!value) {
    return COMMON_COPY.none;
  }

  return new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" })
    .format(new Date(value))
    .replace(/\//g, "-");
}

export function formatGameStatus(value?: string | null) {
  return statusLabel(value);
}

export function formatGameScore(game: GameSummary) {
  const homeScore = game.home_team?.score;
  const awayScore = game.away_team?.score;

  return typeof homeScore === "number" && typeof awayScore === "number" ? `${homeScore} - ${awayScore}` : COMMON_COPY.none;
}

export function mapGamesToRows(games: GameSummary[]): TableRow[] {
  return games.map((game) => ({
    对阵: gameMatchup(game),
    日期: formatDate(game.game_date ?? game.game_time_utc),
    状态: formatGameStatus(game.status_text ?? game.status),
    主队: game.home_team?.abbreviation ? translateTeamName(game.home_team.abbreviation, "short") : COMMON_COPY.none,
    客队: game.away_team?.abbreviation ? translateTeamName(game.away_team.abbreviation, "short") : COMMON_COPY.none,
    比分: formatGameScore(game),
  }));
}

export function mapTeamsToRows(teams: TeamTableEntry[]): TableRow[] {
  return teams.slice(0, 12).map((team) => ({
    球队: translateTeamName(team.team_abbr ?? team.team_name ?? COMMON_COPY.none, "short"),
    进攻效率: formatNumber(team.off_rating),
    防守效率: formatNumber(team.def_rating),
    净效率: formatNumber(team.net_rating),
    比赛节奏: formatNumber(team.pace),
  }));
}

export function mapKpis(kpis: TeamKpi[]) {
  const tones = ["blue", "violet", "green", "amber"] as const;

  return kpis.slice(0, 4).map((kpi, index) => ({
    label: KPI_LABELS[kpi.label] ?? metricLabel(kpi.label),
    value: formatKpiValue(kpi.value),
    trend: kpi.rank ? `联盟第 ${kpi.rank}` : KPI_TRENDS[kpi.description ?? ""] ?? kpi.description ?? COMMON_COPY.liveData,
    tone: tones[index % tones.length],
  }));
}

export function mapTeamChart(points?: Array<{ team_abbr?: string | null; team_name?: string | null; label?: string | null; y?: number | null; x?: number | null }>): ChartPoint[] {
  return (points ?? []).slice(0, 8).map((point, index) => ({
    label: translateTeamName(point.team_abbr ?? point.label ?? point.team_name ?? `球队 ${index + 1}`, "short"),
    value: Math.abs(point.y ?? point.x ?? 0),
  }));
}

export function mapShotZones(zones: ShotZoneSummary[]): TableRow[] {
  return zones.slice(0, 8).map((zone) => ({
    投篮区域: shotZoneLabel(zone.shot_zone_basic),
    出手距离: shotZoneLabel(zone.shot_zone_range),
    出手次数: zone.fga,
    命中率: formatPercent(zone.fg_pct),
    每次出手得分: formatNumber(zone.pps),
  }));
}

export function mapShotZonesToChart(zones: ShotZoneSummary[]): ChartPoint[] {
  return zones.slice(0, 5).map((zone) => ({
    label: shotZoneLabel(zone.shot_zone_basic ?? zone.shot_zone_range),
    value: zone.fga,
  }));
}
