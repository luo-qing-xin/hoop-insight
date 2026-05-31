import { getRecentGames, getTeamOverview, useApi } from "../api/client";
import { mapGamesToRows, mapTeamChart } from "../api/formatters";
import { AsyncStatus } from "../components/AsyncState";
import ChartCard from "../components/ChartCard";
import DataTable from "../components/DataTable";
import PageIntroCard from "../components/PageIntroCard";
import StatCard from "../components/StatCard";

const overviewTags = [
  { label: "比赛数据", icon: "grid" },
  { label: "球队效率", icon: "bars" },
  { label: "球员表现", icon: "user" },
  { label: "投篮空间", icon: "target" },
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

const fallbackNetChart = [
  { label: "老鹰", value: 13.4 },
  { label: "凯尔特人", value: 12.6 },
  { label: "篮网", value: 13.2 },
  { label: "黄蜂", value: 13.5 },
  { label: "公牛", value: 13.7 },
  { label: "骑士", value: 7.8 },
  { label: "独行侠", value: 8.2 },
  { label: "掘金", value: 8.7 },
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

export function Component() {
  const recentGames = useApi(() => getRecentGames(), []);
  const teamOverview = useApi(() => getTeamOverview(), []);
  const strengthChart = mapTeamChart(teamOverview.data?.charts[0]?.points);
  const netChart = mapTeamChart(teamOverview.data?.charts[1]?.points);
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
        <ChartCard
          title="净效率对比"
          subtitle="展示当前样本中净效率领先的球队，辅助识别近期表现更稳定的队伍。"
          data={netChart.length > 0 ? netChart : fallbackNetChart}
        />
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
