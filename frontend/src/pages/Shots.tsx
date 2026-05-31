import { useEffect, useMemo, useState } from "react";
import {
  DEFAULT_SEASON,
  getPlayerLeaderboard,
  getPlayerShotChart,
  getPlayerShotZones,
  getTeamOverview,
  getTeamShotChart,
  getTeamShotZones,
  useApi,
  type PlayerLeaderboardEntry,
  type ShotChartResponse,
  type ShotZoneResponse,
  type ShotZoneSummary,
  type TeamTableEntry,
} from "../api/client";
import { formatNumber, formatPercent } from "../api/formatters";
import HeatMap from "../charts/HeatMap";
import ShotChart from "../charts/ShotChart";
import { AsyncStatus } from "../components/AsyncState";
import StatCard from "../components/StatCard";
import { COMMON_COPY, efficiencyLevelLabel, shotZoneLabel } from "../constants/zhLabels";
import { translatePlayerName, translateTeamName } from "../utils/nameTranslations";

const SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23"];
const DEFAULT_PLAYER_ID = 2544;
const DEFAULT_TEAM_ID = 1610612747;
const MIN_FGA = 20;

type AnalysisTarget = "player" | "team";

const EMPTY_CHART: ShotChartResponse = {
  season: DEFAULT_SEASON,
  shots: [],
  zones: [],
  totals: { fga: 0, fgm: 0, fg_pct: null, points: 0, pps: null },
};

const EMPTY_ZONES: ShotZoneResponse = {
  season: DEFAULT_SEASON,
  min_fga: MIN_FGA,
  zones: [],
  totals: { fga: 0, fgm: 0, fg_pct: null, points: 0, pps: null },
};

function playerId(player: PlayerLeaderboardEntry) {
  return player.player_id ? String(player.player_id) : "";
}

function teamId(team: TeamTableEntry) {
  return team.team_id ? String(team.team_id) : "";
}

function zoneName(zone: ShotZoneSummary) {
  const parts = [zone.shot_zone_basic, zone.shot_zone_area, zone.shot_zone_range].filter(Boolean).map((part) => shotZoneLabel(part));
  return parts.length > 0 ? parts.join(" / ") : "未知区域";
}

function labelForLevel(level?: string | null) {
  const normalized = level?.toLowerCase();
  if (normalized === "high") {
    return { value: "high", label: efficiencyLevelLabel("high") };
  }
  if (normalized === "low") {
    return { value: "low", label: efficiencyLevelLabel("low") };
  }
  return { value: "normal", label: efficiencyLevelLabel("normal") };
}

function targetName(target: AnalysisTarget, player?: PlayerLeaderboardEntry, team?: TeamTableEntry) {
  if (target === "player") {
    return player?.player_name ? translatePlayerName(player.player_name, "full") : `球员 ${DEFAULT_PLAYER_ID}`;
  }

  return team ? translateTeamName(team.team_abbr ?? team.team_name, "short") : `球队 ${DEFAULT_TEAM_ID}`;
}

function DistributionCards({ zones }: { zones: ShotZoneSummary[] }) {
  if (zones.length === 0) {
    return <div className="empty-panel">暂无区域分布数据，请调整对象或赛季后重试。</div>;
  }

  return (
    <section className="shot-distribution-grid" aria-label="投篮命中率分布">
      {zones.slice(0, 4).map((zone) => (
        <article className="shot-distribution-card" key={zoneName(zone)}>
          <span>{shotZoneLabel(zone.shot_zone_basic)}</span>
          <strong>{formatPercent(zone.fg_pct)}</strong>
          <small>
            {zone.fgm}/{zone.fga} 命中，每次出手得分 {formatNumber(zone.pps)}
          </small>
        </article>
      ))}
    </section>
  );
}

function EfficiencyList({ zones }: { zones: ShotZoneSummary[] }) {
  return (
    <section className="table-card">
      <div className="card-heading">
        <div>
          <h2>投篮区域效率</h2>
          <p>基于区域聚合结果识别高效区域、常规区域与低效区域。</p>
        </div>
        <span>{zones.length} 个区域</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>区域</th>
              <th>出手</th>
              <th>命中</th>
              <th>命中率</th>
              <th>每次出手得分</th>
              <th>标签</th>
            </tr>
          </thead>
          <tbody>
            {zones.length === 0 ? (
              <tr>
                <td colSpan={6}>{COMMON_COPY.noData}</td>
              </tr>
            ) : (
              zones.map((zone) => {
                const level = labelForLevel(zone.efficiency_level);
                return (
                  <tr key={zoneName(zone)}>
                    <td>{zoneName(zone)}</td>
                    <td>{zone.fga}</td>
                    <td>{zone.fgm}</td>
                    <td>{formatPercent(zone.fg_pct)}</td>
                    <td>{formatNumber(zone.pps)}</td>
                    <td>
                      <span className={`efficiency-pill efficiency-${level.value}`}>{level.label}</span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function Component() {
  const [season, setSeason] = useState(DEFAULT_SEASON);
  const [target, setTarget] = useState<AnalysisTarget>("player");
  const [selectedPlayerId, setSelectedPlayerId] = useState(String(DEFAULT_PLAYER_ID));
  const [selectedTeamId, setSelectedTeamId] = useState(String(DEFAULT_TEAM_ID));

  const playerOptionsState = useApi(() => getPlayerLeaderboard({ season, stat: "PTS", min_gp: 1, min_min: 1 }), [season]);
  const teamOptionsState = useApi(() => getTeamOverview({ season }), [season]);

  const players = useMemo(() => playerOptionsState.data?.players.filter((player) => player.player_id) ?? [], [playerOptionsState.data]);
  const teams = useMemo(() => teamOptionsState.data?.table.filter((team) => team.team_id) ?? [], [teamOptionsState.data]);

  useEffect(() => {
    if (players.length > 0 && !players.some((player) => playerId(player) === selectedPlayerId)) {
      setSelectedPlayerId(playerId(players[0]));
    }
  }, [players, selectedPlayerId]);

  useEffect(() => {
    if (teams.length > 0 && !teams.some((team) => teamId(team) === selectedTeamId)) {
      setSelectedTeamId(teamId(teams[0]));
    }
  }, [teams, selectedTeamId]);

  const activePlayer = useMemo(() => players.find((player) => playerId(player) === selectedPlayerId), [players, selectedPlayerId]);
  const activeTeam = useMemo(() => teams.find((team) => teamId(team) === selectedTeamId), [teams, selectedTeamId]);
  const activeId = Number(target === "player" ? selectedPlayerId : selectedTeamId);
  const activeName = targetName(target, activePlayer, activeTeam);

  const shotChart = useApi(
    () => {
      if (!Number.isFinite(activeId) || activeId <= 0) {
        return Promise.resolve({ ...EMPTY_CHART, season });
      }

      return target === "player" ? getPlayerShotChart(activeId, season) : getTeamShotChart(activeId, season);
    },
    [activeId, season, target],
  );
  const shotZones = useApi(
    () => {
      if (!Number.isFinite(activeId) || activeId <= 0) {
        return Promise.resolve({ ...EMPTY_ZONES, season });
      }

      return target === "player" ? getPlayerShotZones(activeId, { season, min_fga: MIN_FGA }) : getTeamShotZones(activeId, { season, min_fga: MIN_FGA });
    },
    [activeId, season, target],
  );

  const chartData = shotChart.data ?? EMPTY_CHART;
  const zoneData = shotZones.data?.zones ?? chartData.zones;
  const totals = shotZones.data?.totals ?? chartData.totals;
  const optionLoading = target === "player" ? playerOptionsState.loading : teamOptionsState.loading;
  const optionError = target === "player" ? playerOptionsState.error : teamOptionsState.error;
  const isEmpty = !shotChart.loading && !shotZones.loading && chartData.shots.length === 0 && zoneData.length === 0;

  return (
    <div className="page-stack">
      <section className="filter-card shots-filter-card">
        <label>
          <span>分析对象</span>
          <select value={target} onChange={(event) => setTarget(event.target.value as AnalysisTarget)}>
            <option value="player">球员</option>
            <option value="team">球队</option>
          </select>
        </label>
        <label>
          <span>{target === "player" ? "球员" : "球队"}</span>
          {target === "player" ? (
            <select value={selectedPlayerId} onChange={(event) => setSelectedPlayerId(event.target.value)}>
              {players.length === 0 && <option value={selectedPlayerId}>球员 {selectedPlayerId}</option>}
              {players.map((player) => (
                <option key={playerId(player)} value={playerId(player)}>
                  {translatePlayerName(player.player_name, "full")} {player.team_abbr ? `- ${translateTeamName(player.team_abbr, "short")}` : ""}
                </option>
              ))}
            </select>
          ) : (
            <select value={selectedTeamId} onChange={(event) => setSelectedTeamId(event.target.value)}>
              {teams.length === 0 && <option value={selectedTeamId}>球队 {selectedTeamId}</option>}
              {teams.map((team) => (
                <option key={teamId(team)} value={teamId(team)}>
                  {team.team_abbr ? `${translateTeamName(team.team_abbr, "short")} - ${translateTeamName(team.team_name ?? team.team_abbr, "full")}` : translateTeamName(team.team_name ?? teamId(team), "full")}
                </option>
              ))}
            </select>
          )}
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
      </section>

      <AsyncStatus
        loading={optionLoading || shotChart.loading || shotZones.loading}
        error={optionError ?? shotChart.error ?? shotZones.error}
        empty={isEmpty}
        emptyMessage="当前对象和赛季暂无投篮数据，请切换球员、球队或赛季后重试。"
      />

      <section className="stat-grid">
        <StatCard label="出手次数" value={String(totals.fga)} trend={`${totals.fgm} 次命中`} tone="blue" />
        <StatCard label="投篮命中率" value={formatPercent(totals.fg_pct)} trend={activeName} tone="green" />
        <StatCard label="每次出手得分" value={formatNumber(totals.pps)} trend="后端计算值" tone="violet" />
        <StatCard label="得分" value={String(totals.points)} trend={chartData.season ?? season} tone="amber" />
      </section>

      <section className="shots-main-grid">
        <section className="chart-card">
          <div className="card-heading">
            <div>
              <h2>投篮分布图</h2>
              <p>根据出手坐标还原半场投篮分布，用于观察空间选择。</p>
            </div>
            <span>{chartData.shots.length} 次出手</span>
          </div>
          <ShotChart shots={chartData.shots} title={`${activeName} 投篮分布图`} />
        </section>

        <section className="chart-card">
          <div className="card-heading">
            <div>
              <h2>投篮热区</h2>
              <p>结合投篮区域汇总，观察高效区域与低效区域的分布。</p>
            </div>
            <span>最低出手 {shotZones.data?.min_fga ?? MIN_FGA}</span>
          </div>
          <HeatMap zones={zoneData} title={`${activeName} 投篮热区`} />
        </section>
      </section>

      <section className="chart-card">
        <div className="card-heading">
          <div>
            <h2>命中率分布</h2>
            <p>按投篮区域展示出手次数、命中次数与每次出手得分。</p>
          </div>
          <span>{activeName}</span>
        </div>
        <DistributionCards zones={zoneData} />
      </section>

      <EfficiencyList zones={zoneData} />
    </div>
  );
}
