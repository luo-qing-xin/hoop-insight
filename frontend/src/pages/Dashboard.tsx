import type { CSSProperties } from "react";
import { getRecentGames, getTeamOverview, useApi } from "../api/client";
import type { TeamTableEntry } from "../api/client";
import { mapGamesToRows, mapTeamChart } from "../api/formatters";
import { AsyncStatus } from "../components/AsyncState";
import ChartCard from "../components/ChartCard";
import DataTable from "../components/DataTable";
import PageIntroCard from "../components/PageIntroCard";
import StatCard from "../components/StatCard";
import { COMMON_COPY } from "../constants/zhLabels";
import { translateTeamName } from "../utils/nameTranslations";

const overviewTags = [
  { label: "比赛数据", icon: "grid", to: "/games" },
  { label: "球队效率", icon: "bars", to: "/teams" },
  { label: "球员表现", icon: "user", to: "/players" },
  { label: "投篮空间", icon: "target", to: "/shots" },
] as const;

const dashboardKpis = [
  {
    label: "联盟进攻效率",
    value: "114.8",
    description: "每 100 回合平均得分，衡量整体进攻产出。",
    tone: "blue" as const,
    icon: "trend" as const,
  },
  {
    label: "联盟防守效率",
    value: "114.7",
    description: "每 100 回合平均失分，数值越低代表防守越好。",
    tone: "violet" as const,
    icon: "shield" as const,
  },
  {
    label: "联盟净效率",
    value: "5.3%",
    description: "进攻效率与防守效率之差，反映整体胜负强度。",
    tone: "green" as const,
    icon: "pulse" as const,
  },
  {
    label: "联盟比赛节奏",
    value: "100.2",
    description: "每场平均回合数，用于衡量比赛速度。",
    tone: "amber" as const,
    icon: "timer" as const,
  },
];

const fallbackChart = [
  { label: "老鹰", value: 95 },
  { label: "凯尔特人", value: 119 },
  { label: "篮网", value: 124 },
  { label: "黄蜂", value: 106 },
  { label: "公牛", value: 107 },
  { label: "骑士", value: 102 },
  { label: "独行侠", value: 106 },
  { label: "掘金", value: 106 },
];

const fallbackGames = [
  {
    对阵: "湖人 vs 勇士",
    日期: "2024-05-20",
    状态: "已结束",
    主队: "湖人",
    客队: "勇士",
    比分: "112 - 108",
  },
];

type LooseTeamEntry = TeamTableEntry & Record<string, unknown>;

type NetEfficiencyCardRow = {
  key: string;
  teamName: string;
  netEfficiency: number | null;
};

const lastSevenGamesLabel = COMMON_COPY.lastSevenGames;

function toFiniteNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function readMetric(team: LooseTeamEntry, keys: string[]) {
  for (const key of keys) {
    const value = toFiniteNumber(team[key]);
    if (value !== null) {
      return value;
    }
  }

  return null;
}

function computeNetEfficiency(team: LooseTeamEntry) {
  const directNet = readMetric(team, ["net_rating", "NET_RATING", "netRating", "net_efficiency", "netEfficiency"]);
  if (directNet !== null) {
    return directNet;
  }

  const offensiveRating = readMetric(team, ["off_rating", "OFF_RATING", "offRating", "offensive_rating"]);
  const defensiveRating = readMetric(team, ["def_rating", "DEF_RATING", "defRating", "defensive_rating"]);

  return offensiveRating !== null && defensiveRating !== null ? offensiveRating - defensiveRating : null;
}

function formatSignedNetEfficiency(value: number | null) {
  if (value === null) {
    return "暂无数据";
  }

  const rounded = Number(value.toFixed(1));
  const formatted = Math.abs(rounded).toFixed(1);

  if (rounded > 0) {
    return `+${formatted}`;
  }

  return rounded < 0 ? `-${formatted}` : formatted;
}

function teamDisplayName(team: LooseTeamEntry, fallbackIndex: number) {
  const rawName = team.team_name ?? team.TEAM_NAME ?? team.name ?? team.label ?? team.team_abbr ?? team.TEAM_ABBREVIATION;
  const name = typeof rawName === "string" && rawName.trim() !== "" ? rawName : `球队 ${fallbackIndex + 1}`;
  return translateTeamName(name, "short");
}

function mapNetEfficiencyCards(teams: TeamTableEntry[] = []) {
  return teams
    .map((team, index) => {
      const looseTeam = team as LooseTeamEntry;

      return {
        key: String(looseTeam.team_id ?? looseTeam.TEAM_ID ?? looseTeam.team_abbr ?? looseTeam.TEAM_ABBREVIATION ?? index),
        teamName: teamDisplayName(looseTeam, index),
        netEfficiency: computeNetEfficiency(looseTeam),
      };
    })
    .sort((a, b) => {
      if (a.netEfficiency === null && b.netEfficiency === null) {
        return 0;
      }
      if (a.netEfficiency === null) {
        return 1;
      }
      if (b.netEfficiency === null) {
        return -1;
      }
      return b.netEfficiency - a.netEfficiency;
    })
    .slice(0, 8);
}

function NetEfficiencyGridCard({ teams }: { teams: TeamTableEntry[] }) {
  const cards = mapNetEfficiencyCards(teams);
  const maxAbs = Math.max(...cards.map((team) => Math.abs(team.netEfficiency ?? 0)), 0);

  return (
    <section className="chart-card net-grid-card">
      <div className="card-heading">
        <div>
          <h2>净效率对比</h2>
          <p>展示当前样本中净效率领先的球队，辅助识别近期表现更稳定的队伍。</p>
        </div>
        <span>{lastSevenGamesLabel}</span>
      </div>

      {cards.length > 0 ? (
        <div className="net-team-grid" aria-label="净效率对比">
          {cards.map((team, index) => {
            const isPositive = (team.netEfficiency ?? 0) >= 0;
            const intensity = maxAbs > 0 && team.netEfficiency !== null ? Math.max(Math.abs(team.netEfficiency) / maxAbs, 0.28) : 0.28;

            return (
              <article className="net-team-card" key={team.key}>
                <div className="net-bar-card" style={{ "--net-intensity": intensity } as CSSProperties}>
                  <span className="team-rank">第 {index + 1}</span>
                  <span className={team.netEfficiency === null ? "net-value net-value-empty" : isPositive ? "net-value net-value-positive" : "net-value net-value-negative"}>
                    {formatSignedNetEfficiency(team.netEfficiency)}
                  </span>
                </div>
                <div className="team-name" title={team.teamName}>
                  {team.teamName}
                </div>
                <div className="team-subtitle">{lastSevenGamesLabel}</div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="net-grid-empty">暂无数据</div>
      )}
    </section>
  );
}

export function Component() {
  const recentGames = useApi(() => getRecentGames(), []);
  const teamOverview = useApi(() => getTeamOverview(), []);
  const strengthChart = mapTeamChart(teamOverview.data?.charts[0]?.points);
  const games = mapGamesToRows(recentGames.data?.games ?? []);

  return (
    <div className="page-stack dashboard-page">
      <AsyncStatus loading={teamOverview.loading || recentGames.loading} error={teamOverview.error ?? recentGames.error} />

      <PageIntroCard
        title="本页概览"
        body="当前页面用于快速观察联盟整体表现。核心指标覆盖进攻效率、防守效率、净效率与比赛节奏，适合作为进入球队分析、球员分析和投篮分析前的全局入口。"
        tags={overviewTags}
      />

      <section className="stat-grid">
        {dashboardKpis.map((item) => (
          <StatCard key={item.label} {...item} />
        ))}
      </section>

      <section className="dashboard-grid">
        <ChartCard
          title="球队效率走势"
          subtitle="基于后端球队总览接口生成，用于观察样本球队之间的效率差异和整体波动。"
          data={strengthChart.length > 0 ? strengthChart : fallbackChart}
          variant="line"
          insight="当前样本中，部分球队在净效率上存在明显分层，可进一步进入球队分析页面查看进攻、防守和节奏拆解。"
        />
        <NetEfficiencyGridCard teams={teamOverview.data?.table ?? []} />
      </section>

      <DataTable
        title="近期比赛概览"
        subtitle="用于快速识别已完成比赛、球队对阵关系和基础赛果，是后续单场复盘与智能问数的入口。"
        actionLabel="查看更多 →"
        columns={["对阵", "日期", "状态", "主队", "客队", "比分"]}
        rows={games.length > 0 ? games : fallbackGames}
      />
    </div>
  );
}
