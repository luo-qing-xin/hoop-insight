import { useEffect, useMemo, useState } from "react";
import {
  DEFAULT_SEASON,
  getPlayerLeaderboard,
  getPlayerProfile,
  getPlayerRadar,
  useApi,
  type PlayerAdvancedEntry,
  type PlayerLeaderboardEntry,
  type PlayerProfileResponse,
  type PlayerRadarResponse,
} from "../api/client";
import { formatNumber, formatPercent } from "../api/formatters";
import { AsyncStatus } from "../components/AsyncState";
import StatCard from "../components/StatCard";
import RadarChart from "../charts/RadarChart";
import { COMMON_COPY, metricLabel, radarLabel } from "../constants/zhLabels";
import { translatePlayerName, translateTeamName } from "../utils/nameTranslations";

const SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23"];
const SORT_STATS = [
  { value: "PTS", label: "得分" },
  { value: "REB", label: "篮板" },
  { value: "AST", label: "助攻" },
  { value: "STL", label: "抢断" },
  { value: "BLK", label: "盖帽" },
  { value: "FG_PCT", label: "投篮命中率" },
  { value: "FG3_PCT", label: "三分命中率" },
] as const;

type SortStat = (typeof SORT_STATS)[number]["value"];

const STAT_FIELD: Record<SortStat, keyof PlayerLeaderboardEntry> = {
  PTS: "pts",
  REB: "reb",
  AST: "ast",
  STL: "stl",
  BLK: "blk",
  FG_PCT: "fg_pct",
  FG3_PCT: "fg3_pct",
};

const COMPARISON_METRICS = [
  { key: "OFF_RATING", label: "进攻效率" },
  { key: "DEF_RATING", label: "防守效率" },
  { key: "NET_RATING", label: "净效率" },
  { key: "USG_PCT", label: "使用率" },
  { key: "TS_PCT", label: "真实命中率" },
  { key: "PIE", label: "影响力" },
] as const;

function formatStat(stat: string, value: unknown) {
  return stat.endsWith("_PCT") || stat === "PIE" ? formatPercent(value) : formatNumber(value);
}

function playerKpiCards(player?: PlayerAdvancedEntry | null, row?: PlayerLeaderboardEntry | null) {
  return [
    { label: "得分", value: formatNumber(row?.pts), trend: "场均产量", tone: "blue" as const },
    { label: "篮板", value: formatNumber(row?.reb), trend: "场均篮板", tone: "green" as const },
    { label: "助攻", value: formatNumber(row?.ast), trend: "场均组织", tone: "violet" as const },
    { label: "使用率", value: formatPercent(player?.USG_PCT), trend: "球权占比", tone: "violet" as const },
    { label: "真实命中率", value: formatPercent(player?.TS_PCT), trend: "得分效率", tone: "amber" as const },
    { label: "净效率", value: formatNumber(player?.NET_RATING), trend: "在场影响", tone: "green" as const },
  ];
}

function playerSubtitle(player?: PlayerAdvancedEntry | null) {
  if (!player) {
    return "请从排行榜选择一名球员";
  }

  const team = player.TEAM_ABBREVIATION ? translateTeamName(player.TEAM_ABBREVIATION, "short") : "暂无";
  const gp = player.GP ?? "暂无";
  const minutes = formatNumber(player.MIN);
  return `${team} - 出战 ${gp} 场 - ${minutes} 分钟`;
}

export function Component() {
  const [season, setSeason] = useState(DEFAULT_SEASON);
  const [sortStat, setSortStat] = useState<SortStat>("PTS");
  const [minGp, setMinGp] = useState(10);
  const [minMin, setMinMin] = useState(15);
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null);

  const leaderboard = useApi(
    () => getPlayerLeaderboard({ season, stat: sortStat, min_gp: minGp, min_min: minMin }),
    [season, sortStat, minGp, minMin],
  );
  const players = useMemo(() => leaderboard.data?.players ?? [], [leaderboard.data]);
  const selectedRow = useMemo(
    () => players.find((player) => player.player_id === selectedPlayerId) ?? players.find((player) => player.player_id),
    [players, selectedPlayerId],
  );
  const activePlayerId = selectedRow?.player_id ?? null;
  const activePlayerName = selectedRow?.player_name ?? "球员";
  const activePlayerDisplayName = translatePlayerName(activePlayerName, "full");

  useEffect(() => {
    if (players.length === 0) {
      setSelectedPlayerId(null);
      return;
    }

    if (!selectedPlayerId || !players.some((player) => player.player_id === selectedPlayerId)) {
      setSelectedPlayerId(players.find((player) => player.player_id)?.player_id ?? null);
    }
  }, [players, selectedPlayerId]);

  const profile = useApi(
    () => (activePlayerId ? getPlayerProfile(activePlayerId, season) : Promise.resolve<PlayerProfileResponse>({ season, player_id: 0, player: null })),
    [activePlayerId, season],
  );
  const radar = useApi(
    () =>
      activePlayerId
        ? getPlayerRadar(activePlayerId, { season, min_gp: minGp, min_min: minMin })
        : Promise.resolve<PlayerRadarResponse>({ season, player_id: 0, min_gp: minGp, min_min: minMin, radar: [] }),
    [activePlayerId, season, minGp, minMin],
  );

  const selectedProfile = profile.data?.player;
  const radarData = (radar.data?.radar ?? []).map((item) => ({ ...item, label: radarLabel(item.label) }));
  const leaderboardEmpty = !leaderboard.loading && !leaderboard.error && players.length === 0;
  const detailEmpty = !profile.loading && !radar.loading && !selectedProfile && radarData.length === 0;

  return (
    <div className="page-stack">
      <AsyncStatus loading={leaderboard.loading} error={leaderboard.error} empty={leaderboardEmpty} emptyMessage="当前赛季和筛选条件下暂无匹配球员，请调整门槛后重试。" />

      <section className="player-hero-grid">
        <div className="player-core-stack">
          <section className="player-controls player-core-controls">
            <label className="player-select-control">
              <span>球员选择</span>
              <select value={activePlayerId ?? ""} onChange={(event) => setSelectedPlayerId(Number(event.target.value) || null)} disabled={players.length === 0}>
                {players.length === 0 ? (
                  <option value="">暂无球员</option>
                ) : (
                  players.map((player) => (
                    <option key={player.player_id ?? player.player_name} value={player.player_id ?? ""}>
                      {translatePlayerName(player.player_name, "full")}
                    </option>
                  ))
                )}
              </select>
            </label>
            <label>
              <span>赛季</span>
              <select value={season} onChange={(event) => setSeason(event.target.value)}>
                {SEASONS.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>排序指标</span>
              <select value={sortStat} onChange={(event) => setSortStat(event.target.value as SortStat)}>
                {SORT_STATS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>最低出场场次</span>
              <input min="0" type="number" value={minGp} onChange={(event) => setMinGp(Math.max(0, Number(event.target.value) || 0))} />
            </label>
            <label>
              <span>最低出场时间</span>
              <input min="0" step="0.5" type="number" value={minMin} onChange={(event) => setMinMin(Math.max(0, Number(event.target.value) || 0))} />
            </label>
          </section>

          <AsyncStatus loading={profile.loading || radar.loading} error={profile.error ?? radar.error} empty={detailEmpty} emptyMessage="请选择一名拥有高级数据的球员查看完整画像。" />

          <section className="detail-banner">
            <span>已选球员</span>
            <strong>{translatePlayerName(selectedProfile?.PLAYER_NAME ?? radar.data?.player_name ?? activePlayerName, "full")}</strong>
            <p>{playerSubtitle(selectedProfile)}</p>
          </section>

          <section className="stat-grid player-advanced-grid">
            {playerKpiCards(selectedProfile, selectedRow).map((item) => (
              <StatCard key={item.label} {...item} />
            ))}
          </section>
        </div>

        <section className="chart-card player-radar-card">
          <div className="card-heading">
            <div>
              <h2>能力结构雷达</h2>
              <p>基于多维指标构建球员能力画像，保留原始 0-100 分归一化结果。</p>
            </div>
            <span>{radarData.length} 个维度</span>
          </div>
          <RadarChart data={radarData} title={`${activePlayerDisplayName} 能力结构雷达`} />
          <p className="radar-card-note">基于得分、组织、防守、效率、篮板、影响力等维度，构建球员综合能力画像。</p>
        </section>
      </section>

      <section className="chart-card player-analysis-card">
        <div className="card-heading">
          <div>
            <h2>球员高级数据分析</h2>
            <p>将核心高级指标与符合条件的球员池进行横向比较。</p>
          </div>
        </div>
        <div className="player-comparison-list">
          {COMPARISON_METRICS.map((metric) => {
            const comparison = selectedProfile?.league_comparison?.[metric.key];
            return (
              <div className="player-comparison-row" key={metric.key}>
                <strong>{metricLabel(metric.label)}</strong>
                <span>球员 {formatStat(metric.key, comparison?.player_value)}</span>
                <span>联盟 {formatStat(metric.key, comparison?.league_average)}</span>
                <em>{formatNumber(comparison?.percentile_rank, 0)} 百分位</em>
              </div>
            );
          })}
        </div>
      </section>

      <section className="table-card player-leaderboard">
        <div className="card-heading">
          <div>
            <h2>球员基础数据榜</h2>
            <p>
              {leaderboard.data?.season ?? season} - 按 {SORT_STATS.find((item) => item.value === (leaderboard.data?.stat ?? sortStat))?.label ?? sortStat} 排序
            </p>
          </div>
          <span>{players.length} 名球员</span>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>排名</th>
                <th>球员</th>
                <th>球队</th>
                <th>场次</th>
                <th>出场时间</th>
                <th>{SORT_STATS.find((item) => item.value === sortStat)?.label ?? sortStat}</th>
                <th>得分</th>
                <th>篮板</th>
                <th>助攻</th>
              </tr>
            </thead>
            <tbody>
              {players.length === 0 ? (
                <tr>
                  <td colSpan={9}>{COMMON_COPY.noData}</td>
                </tr>
              ) : (
                players.slice(0, 30).map((player) => {
                  const isSelected = player.player_id === activePlayerId;
                  return (
                    <tr
                      key={`${player.rank}-${player.player_id ?? player.player_name}`}
                      className={isSelected ? "selected-row" : undefined}
                      onClick={() => player.player_id && setSelectedPlayerId(player.player_id)}
                    >
                      <td>{player.rank}</td>
                      <td>{translatePlayerName(player.player_name, "full")}</td>
                      <td>{player.team_abbr ? translateTeamName(player.team_abbr, "short") : COMMON_COPY.none}</td>
                      <td>{player.gp ?? COMMON_COPY.none}</td>
                      <td>{formatNumber(player.min)}</td>
                      <td>{formatStat(sortStat, player[STAT_FIELD[sortStat]])}</td>
                      <td>{formatNumber(player.pts)}</td>
                      <td>{formatNumber(player.reb)}</td>
                      <td>{formatNumber(player.ast)}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
