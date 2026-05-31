import { useEffect, useMemo, useState } from "react";
import { DEFAULT_SEASON, getTeamDefense, getTeamOffense, getTeamOverview, type TeamTableEntry, useApi } from "../api/client";
import { formatNumber, formatPercent } from "../api/formatters";
import { AsyncStatus } from "../components/AsyncState";
import DataTable from "../components/DataTable";
import StatCard from "../components/StatCard";
import { COMMON_COPY } from "../constants/zhLabels";
import { translateTeamName } from "../utils/nameTranslations";

const SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23"];

type MetricMeta = { label: string; description: string; format?: "number" | "percent"; lowerIsBetter?: boolean };

const METRIC_COPY = {
  OFF_RATING: {
    label: "进攻效率",
    description: "每 100 回合得分，越高说明球队把回合转化为分数的能力越强。",
  },
  EFG_PCT: {
    label: "有效命中率",
    description: "把三分球额外价值计入后的投篮效率，更能反映真实投射质量。",
    format: "percent",
  },
  TM_TOV_PCT: {
    label: "失误率",
    description: "以失误结束的回合占比，进攻端通常越低越好。",
    format: "percent",
    lowerIsBetter: true,
  },
  OREB_PCT: {
    label: "进攻篮板率",
    description: "抢回可争抢进攻篮板的比例，体现二次进攻机会。",
    format: "percent",
  },
  FTA_RATE: {
    label: "罚球率",
    description: "每次出手带来的罚球机会，常用于观察冲击篮筐和造犯规能力。",
    format: "percent",
  },
  DEF_RATING: {
    label: "防守效率",
    description: "每 100 回合失分。注意：防守效率越低，代表防守越好。",
    lowerIsBetter: true,
  },
  OPP_EFG_PCT: {
    label: "对手有效命中率",
    description: "限制对手投篮效率的指标，越低说明防守压制越好。",
    format: "percent",
    lowerIsBetter: true,
  },
  OPP_TOV_PCT: {
    label: "迫使失误率",
    description: "对手回合以失误结束的比例，越高通常代表防守侵略性更强。",
    format: "percent",
  },
  DREB_PCT: {
    label: "防守篮板率",
    description: "保护后场篮板的比例，越高越能终结对手回合。",
    format: "percent",
  },
  OPP_FT_RATE: {
    label: "对手罚球率",
    description: "对手获得罚球的频率，越低说明防守犯规控制更好。",
    format: "percent",
    lowerIsBetter: true,
  },
  PACE: {
    label: "比赛节奏",
    description: "每 48 分钟估算回合数，用来判断球队比赛速度。",
  },
} satisfies Record<string, MetricMeta>;

type MetricKey = keyof typeof METRIC_COPY;

function metricMeta(key: MetricKey): MetricMeta {
  return METRIC_COPY[key];
}

function teamName(team?: TeamTableEntry | null) {
  if (!team) {
    return "暂无";
  }

  return translateTeamName(team.team_abbr ?? team.team_name ?? "暂无", "short");
}

function getTeamId(team: TeamTableEntry) {
  return team.team_id ? String(team.team_id) : team.team_abbr ?? team.team_name ?? "";
}

function numericValue(team: TeamTableEntry | null | undefined, key: MetricKey) {
  const values: Record<MetricKey, number | null | undefined> = {
    OFF_RATING: team?.off_rating,
    EFG_PCT: team?.efg_pct,
    TM_TOV_PCT: team?.tov_pct,
    OREB_PCT: team?.oreb_pct,
    FTA_RATE: team?.ft_rate,
    DEF_RATING: team?.def_rating,
    OPP_EFG_PCT: team?.opp_efg_pct,
    OPP_TOV_PCT: team?.opp_tov_pct,
    DREB_PCT: team?.dreb_pct,
    OPP_FT_RATE: team?.opp_ft_rate,
    PACE: team?.pace,
  };

  return values[key];
}

function netRatingRank(team: TeamTableEntry | null) {
  return team?.rank ? `综合第 ${team.rank}` : "按净效率排序";
}

function formatMetric(value: unknown, key: MetricKey) {
  return metricMeta(key).format === "percent" ? formatPercent(value) : formatNumber(value);
}

function metricRank(rows: TeamTableEntry[], selectedTeam: TeamTableEntry | null, key: MetricKey) {
  if (!selectedTeam) {
    return COMMON_COPY.rankUnavailable;
  }

  const selectedId = getTeamId(selectedTeam);
  const sorted = rows
    .filter((team) => typeof numericValue(team, key) === "number")
    .sort((a, b) => {
      const aValue = numericValue(a, key) ?? 0;
      const bValue = numericValue(b, key) ?? 0;
      return metricMeta(key).lowerIsBetter ? aValue - bValue : bValue - aValue;
    });
  const rank = sorted.findIndex((team) => getTeamId(team) === selectedId) + 1;

  return rank > 0 ? `联盟第 ${rank}` : COMMON_COPY.rankUnavailable;
}

function matchTeam(rows: TeamTableEntry[], selectedTeam: TeamTableEntry | null) {
  if (!selectedTeam) {
    return null;
  }

  const selectedId = getTeamId(selectedTeam);
  return rows.find((team) => getTeamId(team) === selectedId || team.team_abbr === selectedTeam.team_abbr) ?? selectedTeam;
}

function MetricExplainer({ title, subtitle, team, rows, metrics }: { title: string; subtitle: string; team: TeamTableEntry | null; rows: TeamTableEntry[]; metrics: MetricKey[] }) {
  return (
    <section className="analysis-card">
      <div className="card-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <span>{teamName(team)}</span>
      </div>
      <div className="metric-list">
        {metrics.map((key) => (
          <article className="metric-item" key={key}>
            <div className="metric-item-main">
              <span>{metricMeta(key).label}</span>
              <strong>{formatMetric(numericValue(team, key), key)}</strong>
            </div>
            <p>{metricMeta(key).description}</p>
            <small>{metricRank(rows, team, key)}</small>
          </article>
        ))}
      </div>
    </section>
  );
}

function EfficiencyQuadrant({ teams, selectedTeam }: { teams: TeamTableEntry[]; selectedTeam: TeamTableEntry | null }) {
  const points = teams.filter((team) => typeof team.off_rating === "number" && typeof team.def_rating === "number");
  const offValues = points.map((team) => team.off_rating as number);
  const defValues = points.map((team) => team.def_rating as number);
  const minOff = Math.min(...offValues, 100);
  const maxOff = Math.max(...offValues, 120);
  const minDef = Math.min(...defValues, 100);
  const maxDef = Math.max(...defValues, 120);
  const offAvg = points.length > 0 ? offValues.reduce((sum, value) => sum + value, 0) / points.length : (minOff + maxOff) / 2;
  const defAvg = points.length > 0 ? defValues.reduce((sum, value) => sum + value, 0) / points.length : (minDef + maxDef) / 2;
  const xRange = Math.max(maxOff - minOff, 1);
  const yRange = Math.max(maxDef - minDef, 1);

  const plotX = (value: number) => 48 + ((value - minOff) / xRange) * 484;
  const plotY = (value: number) => 272 - ((value - minDef) / yRange) * 224;
  const selectedId = selectedTeam ? getTeamId(selectedTeam) : "";

  return (
    <section className="quadrant-card">
      <div className="card-heading">
        <div>
          <h2>球队攻防象限</h2>
          <p>横轴为进攻效率，纵轴为防守效率；防守效率越低，代表限制对手得分越好。</p>
        </div>
        <span>{points.length} 支球队</span>
      </div>
      <div className="quadrant-wrap" aria-label="球队攻防象限图">
        <svg viewBox="0 0 580 320" role="img">
          <line className="axis-line" x1="48" y1="48" x2="48" y2="272" />
          <line className="axis-line" x1="48" y1="272" x2="532" y2="272" />
          <line className="avg-line" x1={plotX(offAvg)} y1="48" x2={plotX(offAvg)} y2="272" />
          <line className="avg-line" x1="48" y1={plotY(defAvg)} x2="532" y2={plotY(defAvg)} />
          <text className="quadrant-note" x="60" y="68">进攻承压 / 防守偏弱</text>
          <text className="quadrant-note" x="360" y="68">强进攻 / 防守偏弱</text>
          <text className="quadrant-note" x="60" y="258">防守更好</text>
          <text className="quadrant-note" x="350" y="258">强攻强守</text>
          <text className="axis-label" x="290" y="309">进攻效率</text>
          <text className="axis-label axis-label-y" x="14" y="166">防守效率</text>
          {points.map((team) => {
            const id = getTeamId(team);
            const isSelected = id === selectedId;
            const x = plotX(team.off_rating as number);
            const y = plotY(team.def_rating as number);

            return (
              <g className={isSelected ? "team-point team-point-selected" : "team-point"} key={id || teamName(team)}>
                <circle cx={x} cy={y} r={isSelected ? 8 : 6} />
                <text x={x + 9} y={y + 4}>{translateTeamName(team.team_abbr ?? team.team_name, "short")}</text>
                <title>{`${teamName(team)} 进攻 ${formatNumber(team.off_rating)} / 防守 ${formatNumber(team.def_rating)}`}</title>
              </g>
            );
          })}
        </svg>
      </div>
    </section>
  );
}

export function Component() {
  const [season, setSeason] = useState(DEFAULT_SEASON);
  const [selectedTeamId, setSelectedTeamId] = useState("");
  const overview = useApi(() => getTeamOverview({ season }), [season]);
  const offense = useApi(() => getTeamOffense({ season }), [season]);
  const defense = useApi(() => getTeamDefense({ season }), [season]);
  const teams = overview.data?.table ?? [];

  useEffect(() => {
    if (teams.length === 0) {
      return;
    }

    const nextId = getTeamId(teams[0]);
    const currentExists = teams.some((team) => getTeamId(team) === selectedTeamId);
    if (!selectedTeamId || !currentExists) {
      setSelectedTeamId(nextId);
    }
  }, [selectedTeamId, teams]);

  const selectedTeam = useMemo(() => teams.find((team) => getTeamId(team) === selectedTeamId) ?? teams[0] ?? null, [selectedTeamId, teams]);
  const selectedOffense = matchTeam(offense.data?.table ?? [], selectedTeam);
  const selectedDefense = matchTeam(defense.data?.table ?? [], selectedTeam);
  const rankingRows = teams.map((team) => ({
    排名: team.rank ?? "暂无",
    球队: translateTeamName(team.team_abbr ?? team.team_name ?? "暂无", "short"),
    场次: team.gp ?? "暂无",
    战绩: typeof team.wins === "number" && typeof team.losses === "number" ? `${team.wins}-${team.losses}` : "暂无",
    进攻效率: formatNumber(team.off_rating),
    防守效率: formatNumber(team.def_rating),
    净效率: formatNumber(team.net_rating),
    比赛节奏: formatNumber(team.pace),
  }));

  return (
    <div className="page-stack">
      <AsyncStatus loading={overview.loading || offense.loading || defense.loading} error={overview.error ?? offense.error ?? defense.error} />
      <section className="filter-card">
        <label>
          <span>球队</span>
          <select value={selectedTeamId} onChange={(event) => setSelectedTeamId(event.target.value)}>
            {teams.map((team) => (
              <option key={getTeamId(team)} value={getTeamId(team)}>
                {team.team_abbr ? `${translateTeamName(team.team_abbr, "short")} - ${translateTeamName(team.team_name ?? team.team_abbr, "full")}` : translateTeamName(team.team_name ?? "未知球队", "full")}
              </option>
            ))}
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
      </section>
      <section className="stat-grid">
        <StatCard label="进攻效率" value={formatNumber(selectedTeam?.off_rating)} trend={metricRank(teams, selectedTeam, "OFF_RATING")} tone="blue" />
        <StatCard label="防守效率" value={formatNumber(selectedTeam?.def_rating)} trend="越低越好" tone="green" />
        <StatCard label="净效率" value={formatNumber(selectedTeam?.net_rating)} trend={netRatingRank(selectedTeam)} tone="violet" />
        <StatCard label="比赛节奏" value={formatNumber(selectedTeam?.pace)} trend="每 48 分钟回合" tone="amber" />
      </section>
      <section className="dashboard-grid">
        <MetricExplainer title="球队进攻效率分析" subtitle="拆解得分效率、失误控制、二次进攻和造罚球能力。" team={selectedOffense} rows={offense.data?.table ?? teams} metrics={["OFF_RATING", "EFG_PCT", "TM_TOV_PCT", "OREB_PCT", "FTA_RATE"]} />
        <MetricExplainer title="球队防守效率分析" subtitle="观察限制投篮、制造失误、保护篮板和控制犯规的表现。" team={selectedDefense} rows={defense.data?.table ?? teams} metrics={["DEF_RATING", "OPP_EFG_PCT", "OPP_TOV_PCT", "DREB_PCT", "OPP_FT_RATE"]} />
      </section>
      <DataTable
        title="球队排名"
        subtitle="按净效率排序；防守效率数值越低，防守表现越好"
        columns={["排名", "球队", "场次", "战绩", "进攻效率", "防守效率", "净效率", "比赛节奏"]}
        rows={rankingRows}
      />
      <EfficiencyQuadrant teams={teams} selectedTeam={selectedTeam} />
    </div>
  );
}
