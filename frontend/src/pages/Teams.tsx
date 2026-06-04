import { useEffect, useMemo, useRef, useState } from "react";
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
  return team.team_id != null ? String(team.team_id) : team.team_abbr ?? team.team_name ?? "";
}

function normalizeTeamIdentity(value: string | number | null | undefined) {
  return value == null ? "" : String(value).trim().toLowerCase();
}

function sameTeam(a: TeamTableEntry | null | undefined, b: TeamTableEntry | null | undefined) {
  if (!a || !b) {
    return false;
  }

  const aId = normalizeTeamIdentity(a.team_id);
  const bId = normalizeTeamIdentity(b.team_id);
  if (aId && bId && aId === bId) {
    return true;
  }

  const aAbbr = normalizeTeamIdentity(a.team_abbr);
  const bAbbr = normalizeTeamIdentity(b.team_abbr);
  if (aAbbr && bAbbr && aAbbr === bAbbr) {
    return true;
  }

  const aName = normalizeTeamIdentity(a.team_name);
  const bName = normalizeTeamIdentity(b.team_name);
  return Boolean(aName && bName && aName === bName);
}

function firstDefined<T>(...values: Array<T | null | undefined>) {
  return values.find((value): value is T => value !== null && value !== undefined);
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

  const sorted = rows
    .filter((team) => typeof numericValue(team, key) === "number")
    .sort((a, b) => {
      const aValue = numericValue(a, key) ?? 0;
      const bValue = numericValue(b, key) ?? 0;
      return metricMeta(key).lowerIsBetter ? aValue - bValue : bValue - aValue;
    });
  const rank = sorted.findIndex((team) => sameTeam(team, selectedTeam)) + 1;

  return rank > 0 ? `联盟第 ${rank}` : COMMON_COPY.rankUnavailable;
}

function matchTeam(rows: TeamTableEntry[], selectedTeam: TeamTableEntry | null) {
  if (!selectedTeam) {
    return null;
  }

  return rows.find((team) => sameTeam(team, selectedTeam)) ?? null;
}

function buildCurrentTeamData(
  overviewTeam: TeamTableEntry | null,
  offenseTeam: TeamTableEntry | null,
  defenseTeam: TeamTableEntry | null,
) {
  if (!overviewTeam && !offenseTeam && !defenseTeam) {
    return null;
  }

  return {
    rank: firstDefined(overviewTeam?.rank, offenseTeam?.rank, defenseTeam?.rank),
    team_id: firstDefined(overviewTeam?.team_id, offenseTeam?.team_id, defenseTeam?.team_id),
    team_name: firstDefined(overviewTeam?.team_name, offenseTeam?.team_name, defenseTeam?.team_name),
    team_abbr: firstDefined(overviewTeam?.team_abbr, offenseTeam?.team_abbr, defenseTeam?.team_abbr),
    gp: firstDefined(overviewTeam?.gp, offenseTeam?.gp, defenseTeam?.gp),
    wins: firstDefined(overviewTeam?.wins, offenseTeam?.wins, defenseTeam?.wins),
    losses: firstDefined(overviewTeam?.losses, offenseTeam?.losses, defenseTeam?.losses),
    win_pct: firstDefined(overviewTeam?.win_pct, offenseTeam?.win_pct, defenseTeam?.win_pct),
    pts: firstDefined(overviewTeam?.pts, offenseTeam?.pts, defenseTeam?.pts),
    plus_minus: firstDefined(overviewTeam?.plus_minus, offenseTeam?.plus_minus, defenseTeam?.plus_minus),
    off_rating: firstDefined(offenseTeam?.off_rating, overviewTeam?.off_rating, defenseTeam?.off_rating),
    efg_pct: firstDefined(offenseTeam?.efg_pct, overviewTeam?.efg_pct, defenseTeam?.efg_pct),
    tov_pct: firstDefined(offenseTeam?.tov_pct, overviewTeam?.tov_pct, defenseTeam?.tov_pct),
    oreb_pct: firstDefined(offenseTeam?.oreb_pct, overviewTeam?.oreb_pct, defenseTeam?.oreb_pct),
    ft_rate: firstDefined(offenseTeam?.ft_rate, overviewTeam?.ft_rate, defenseTeam?.ft_rate),
    def_rating: firstDefined(defenseTeam?.def_rating, overviewTeam?.def_rating, offenseTeam?.def_rating),
    opp_efg_pct: firstDefined(defenseTeam?.opp_efg_pct, overviewTeam?.opp_efg_pct, offenseTeam?.opp_efg_pct),
    opp_tov_pct: firstDefined(defenseTeam?.opp_tov_pct, overviewTeam?.opp_tov_pct, offenseTeam?.opp_tov_pct),
    dreb_pct: firstDefined(defenseTeam?.dreb_pct, overviewTeam?.dreb_pct, offenseTeam?.dreb_pct),
    opp_ft_rate: firstDefined(defenseTeam?.opp_ft_rate, overviewTeam?.opp_ft_rate, offenseTeam?.opp_ft_rate),
    net_rating: firstDefined(overviewTeam?.net_rating, offenseTeam?.net_rating, defenseTeam?.net_rating),
    pace: firstDefined(overviewTeam?.pace, offenseTeam?.pace, defenseTeam?.pace),
    explanations: firstDefined(overviewTeam?.explanations, offenseTeam?.explanations, defenseTeam?.explanations),
  } satisfies TeamTableEntry;
}

type ChartDomain = {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
};

type InteractionMode = "pan" | "zoom";

type DragState =
  | {
      mode: "pan";
      startX: number;
      startY: number;
      domain: ChartDomain;
    }
  | {
      mode: "zoom";
      startX: number;
      startY: number;
      currentX: number;
      currentY: number;
    };

const QUADRANT_PLOT = {
  left: 58,
  top: 44,
  width: 470,
  height: 224,
};

const MIN_ZOOM_RANGE = 0.5;

function roundMetric(value: number) {
  return Math.round(value * 10) / 10;
}

function makeTicks(min: number, max: number, count = 5) {
  if (!Number.isFinite(min) || !Number.isFinite(max) || count < 2) {
    return [];
  }

  const step = (max - min) / (count - 1);
  return Array.from({ length: count }, (_, index) => roundMetric(min + step * index));
}

function clampDomainToBase(domain: ChartDomain, baseDomain: ChartDomain): ChartDomain {
  const baseXRange = baseDomain.xMax - baseDomain.xMin;
  const baseYRange = baseDomain.yMax - baseDomain.yMin;
  const nextXRange = Math.min(Math.max(domain.xMax - domain.xMin, MIN_ZOOM_RANGE), baseXRange);
  const nextYRange = Math.min(Math.max(domain.yMax - domain.yMin, MIN_ZOOM_RANGE), baseYRange);
  let xMin = domain.xMin;
  let xMax = domain.xMin + nextXRange;
  let yMin = domain.yMin;
  let yMax = domain.yMin + nextYRange;

  if (xMin < baseDomain.xMin) {
    xMin = baseDomain.xMin;
    xMax = xMin + nextXRange;
  }
  if (xMax > baseDomain.xMax) {
    xMax = baseDomain.xMax;
    xMin = xMax - nextXRange;
  }
  if (yMin < baseDomain.yMin) {
    yMin = baseDomain.yMin;
    yMax = yMin + nextYRange;
  }
  if (yMax > baseDomain.yMax) {
    yMax = baseDomain.yMax;
    yMin = yMax - nextYRange;
  }

  return { xMin, xMax, yMin, yMax };
}

function zoomDomain(domain: ChartDomain, factor: number, anchorX: number, anchorY: number, baseDomain: ChartDomain) {
  const xRange = domain.xMax - domain.xMin;
  const yRange = domain.yMax - domain.yMin;
  const nextXRange = xRange * factor;
  const nextYRange = yRange * factor;
  const xRatio = (anchorX - domain.xMin) / xRange;
  const yRatio = (anchorY - domain.yMin) / yRange;

  return clampDomainToBase(
    {
      xMin: anchorX - nextXRange * xRatio,
      xMax: anchorX + nextXRange * (1 - xRatio),
      yMin: anchorY - nextYRange * yRatio,
      yMax: anchorY + nextYRange * (1 - yRatio),
    },
    baseDomain,
  );
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
      {team ? (
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
      ) : (
        <div className="empty-panel">当前球队或赛季暂无可用数据。</div>
      )}
    </section>
  );
}

const KPI_TOOLTIP_COPY = {
  offense:
    "进攻效率表示球队每 100 个进攻回合可以得到多少分。相比场均得分，它能减少比赛节奏快慢带来的影响，因此更适合比较不同球队的真实进攻质量。数值越高，说明进攻产出越好。",
  defense:
    "防守效率表示球队每 100 个防守回合会让对手得到多少分。相比场均失分，它能减少比赛节奏差异带来的影响。数值越低，说明球队限制对手得分的能力越强。",
  net:
    "净效率 = 进攻效率 - 防守效率，表示球队每 100 回合相对于对手的净胜分能力。通常净效率越高，说明球队整体竞争力越强，也更能反映长期实力。",
  pace:
    "比赛节奏通常表示球队每 48 分钟大约进行多少个回合。数值越高，说明球队比赛回合更多、攻防转换更快；数值越低，说明球队节奏更慢，更偏阵地战。",
} as const;

function EfficiencyQuadrant({ teams, selectedTeam }: { teams: TeamTableEntry[]; selectedTeam: TeamTableEntry | null }) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [viewport, setViewport] = useState<ChartDomain | null>(null);
  const [interactionMode, setInteractionMode] = useState<InteractionMode>("pan");
  const [showTeamNames, setShowTeamNames] = useState(true);
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [hoverTeam, setHoverTeam] = useState<{ team: TeamTableEntry; x: number; y: number } | null>(null);
  const points = useMemo(() => teams.filter((team) => typeof team.off_rating === "number" && typeof team.def_rating === "number"), [teams]);
  const selectedId = selectedTeam ? getTeamId(selectedTeam) : "";
  const chart = useMemo(() => {
    const offValues = points.map((team) => team.off_rating as number);
    const defValues = points.map((team) => team.def_rating as number);
    const minOff = points.length > 0 ? Math.min(...offValues) : 100;
    const maxOff = points.length > 0 ? Math.max(...offValues) : 120;
    const minDef = points.length > 0 ? Math.min(...defValues) : 100;
    const maxDef = points.length > 0 ? Math.max(...defValues) : 120;
    const xPadding = Math.max((maxOff - minOff) * 0.15, 1);
    const yPadding = Math.max((maxDef - minDef) * 0.15, 1);
    const baseDomain = {
      xMin: minOff - xPadding,
      xMax: maxOff + xPadding,
      yMin: minDef - yPadding,
      yMax: maxDef + yPadding,
    };
    const offAvg = points.length > 0 ? offValues.reduce((sum, value) => sum + value, 0) / points.length : (minOff + maxOff) / 2;
    const defAvg = points.length > 0 ? defValues.reduce((sum, value) => sum + value, 0) / points.length : (minDef + maxDef) / 2;
    const extremeIds = new Set<string>();

    if (!selectedId && points.length > 0) {
      const byOffAsc = [...points].sort((a, b) => (a.off_rating ?? 0) - (b.off_rating ?? 0));
      const byDefAsc = [...points].sort((a, b) => (a.def_rating ?? 0) - (b.def_rating ?? 0));
      const withNet = points.filter((team) => typeof team.net_rating === "number");
      const byNetAsc = [...withNet].sort((a, b) => (a.net_rating ?? 0) - (b.net_rating ?? 0));

      [byOffAsc[0], byOffAsc[byOffAsc.length - 1], byDefAsc[0], byDefAsc[byDefAsc.length - 1], byNetAsc[0], byNetAsc[byNetAsc.length - 1]].forEach((team) => {
        if (team) {
          extremeIds.add(getTeamId(team));
        }
      });
    }

    return { baseDomain, offAvg, defAvg, extremeIds };
  }, [points, selectedId]);
  const domain = viewport ?? chart.baseDomain;
  const xTicks = makeTicks(domain.xMin, domain.xMax);
  const yTicks = makeTicks(domain.yMin, domain.yMax);
  const xRange = Math.max(domain.xMax - domain.xMin, MIN_ZOOM_RANGE);
  const yRange = Math.max(domain.yMax - domain.yMin, MIN_ZOOM_RANGE);

  useEffect(() => {
    setViewport(chart.baseDomain);
  }, [chart.baseDomain.xMin, chart.baseDomain.xMax, chart.baseDomain.yMin, chart.baseDomain.yMax]);

  const plotX = (value: number) => QUADRANT_PLOT.left + ((value - domain.xMin) / xRange) * QUADRANT_PLOT.width;
  const plotY = (value: number) => QUADRANT_PLOT.top + ((value - domain.yMin) / yRange) * QUADRANT_PLOT.height;
  const dataX = (x: number) => domain.xMin + ((x - QUADRANT_PLOT.left) / QUADRANT_PLOT.width) * xRange;
  const dataY = (y: number) => domain.yMin + ((y - QUADRANT_PLOT.top) / QUADRANT_PLOT.height) * yRange;
  const averageX = plotX(chart.offAvg);
  const averageY = plotY(chart.defAvg);
  const showAverageX = chart.offAvg >= domain.xMin && chart.offAvg <= domain.xMax;
  const showAverageY = chart.defAvg >= domain.yMin && chart.defAvg <= domain.yMax;
  const plottedPoints = [...points].sort((team) => (getTeamId(team) === selectedId ? 1 : 0));
  const selectionRect =
    dragState?.mode === "zoom"
      ? {
          x: Math.min(dragState.startX, dragState.currentX),
          y: Math.min(dragState.startY, dragState.currentY),
          width: Math.abs(dragState.currentX - dragState.startX),
          height: Math.abs(dragState.currentY - dragState.startY),
        }
      : null;

  function svgPoint(event: React.PointerEvent<SVGSVGElement> | React.WheelEvent<SVGSVGElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * 580,
      y: ((event.clientY - rect.top) / rect.height) * 320,
    };
  }

  function isInsidePlot(point: { x: number; y: number }) {
    return (
      point.x >= QUADRANT_PLOT.left &&
      point.x <= QUADRANT_PLOT.left + QUADRANT_PLOT.width &&
      point.y >= QUADRANT_PLOT.top &&
      point.y <= QUADRANT_PLOT.top + QUADRANT_PLOT.height
    );
  }

  function handlePointerDown(event: React.PointerEvent<SVGSVGElement>) {
    const point = svgPoint(event);
    if (!isInsidePlot(point)) {
      return;
    }

    event.currentTarget.setPointerCapture(event.pointerId);
    setHoverTeam(null);
    if (interactionMode === "zoom") {
      setDragState({ mode: "zoom", startX: point.x, startY: point.y, currentX: point.x, currentY: point.y });
      return;
    }

    setDragState({ mode: "pan", startX: point.x, startY: point.y, domain });
  }

  function handlePointerMove(event: React.PointerEvent<SVGSVGElement>) {
    const point = svgPoint(event);
    if (!dragState) {
      return;
    }

    if (dragState.mode === "zoom") {
      setDragState({ ...dragState, currentX: point.x, currentY: point.y });
      return;
    }

    const xDelta = ((point.x - dragState.startX) / QUADRANT_PLOT.width) * (dragState.domain.xMax - dragState.domain.xMin);
    const yDelta = ((point.y - dragState.startY) / QUADRANT_PLOT.height) * (dragState.domain.yMax - dragState.domain.yMin);
    setViewport(
      clampDomainToBase(
        {
          xMin: dragState.domain.xMin - xDelta,
          xMax: dragState.domain.xMax - xDelta,
          yMin: dragState.domain.yMin - yDelta,
          yMax: dragState.domain.yMax - yDelta,
        },
        chart.baseDomain,
      ),
    );
  }

  function handlePointerUp(event: React.PointerEvent<SVGSVGElement>) {
    if (!dragState) {
      return;
    }

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }

    if (dragState.mode === "zoom") {
      const rect = {
        x1: Math.min(dragState.startX, dragState.currentX),
        x2: Math.max(dragState.startX, dragState.currentX),
        y1: Math.min(dragState.startY, dragState.currentY),
        y2: Math.max(dragState.startY, dragState.currentY),
      };

      if (rect.x2 - rect.x1 > 8 && rect.y2 - rect.y1 > 8) {
        setViewport(
          clampDomainToBase(
            {
              xMin: dataX(rect.x1),
              xMax: dataX(rect.x2),
              yMin: dataY(rect.y1),
              yMax: dataY(rect.y2),
            },
            chart.baseDomain,
          ),
        );
      }
    }

    setDragState(null);
  }

  function handleWheel(event: React.WheelEvent<SVGSVGElement>) {
    const point = svgPoint(event);
    if (!isInsidePlot(point)) {
      return;
    }

    event.preventDefault();
    const factor = event.deltaY < 0 ? 0.85 : 1.15;
    setViewport((current) => zoomDomain(current ?? chart.baseDomain, factor, dataX(point.x), dataY(point.y), chart.baseDomain));
  }

  function zoomBy(factor: number) {
    const anchorX = (domain.xMin + domain.xMax) / 2;
    const anchorY = (domain.yMin + domain.yMax) / 2;
    setViewport((current) => zoomDomain(current ?? chart.baseDomain, factor, anchorX, anchorY, chart.baseDomain));
  }

  function moveTooltip(team: TeamTableEntry, event: React.PointerEvent<SVGGElement>) {
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) {
      return;
    }

    setHoverTeam({ team, x: event.clientX - rect.left + 14, y: event.clientY - rect.top + 14 });
  }

  function labelPosition(x: number, y: number, index: number) {
    const nearRight = x > QUADRANT_PLOT.left + QUADRANT_PLOT.width - 72;
    const nearTop = y < QUADRANT_PLOT.top + 20;
    const positions = [
      { dx: 10, dy: -10, anchor: "start" },
      { dx: 10, dy: 16, anchor: "start" },
      { dx: -10, dy: -10, anchor: "end" },
      { dx: -10, dy: 16, anchor: "end" },
      { dx: 0, dy: -16, anchor: "middle" },
      { dx: 0, dy: 22, anchor: "middle" },
    ] as const;
    const position = positions[index % positions.length];

    return {
      x: x + (nearRight ? -10 : position.dx),
      y: y + (nearTop ? Math.abs(position.dy) + 8 : position.dy),
      anchor: (nearRight ? "end" : position.anchor) as "end" | "middle" | "start",
    };
  }

  return (
    <section className="quadrant-card">
      <div className="card-heading">
        <div>
          <h2>球队攻防象限</h2>
          <p>横轴为进攻效率，纵轴为防守效率；防守效率越低，代表限制对手得分越好。</p>
        </div>
        <span>{points.length} 支球队</span>
      </div>
      <div className="quadrant-toolbar" aria-label="球队攻防象限图控制">
        <button className={interactionMode === "pan" ? "quadrant-tool-active" : ""} type="button" onClick={() => setInteractionMode("pan")}>
          平移
        </button>
        <button className={interactionMode === "zoom" ? "quadrant-tool-active" : ""} type="button" onClick={() => setInteractionMode("zoom")}>
          框选
        </button>
        <button className={showTeamNames ? "quadrant-tool-active" : ""} type="button" onClick={() => setShowTeamNames((value) => !value)}>
          队名
        </button>
        <button type="button" aria-label="放大" onClick={() => zoomBy(0.82)}>
          +
        </button>
        <button type="button" aria-label="缩小" onClick={() => zoomBy(1.18)}>
          -
        </button>
        <button type="button" onClick={() => setViewport(chart.baseDomain)}>
          重置
        </button>
      </div>
      <div className="quadrant-wrap" aria-label="球队攻防象限图" ref={wrapRef}>
        <svg
          className={`quadrant-svg quadrant-svg-${interactionMode}`}
          viewBox="0 0 580 320"
          role="img"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={() => setDragState(null)}
          onWheel={handleWheel}
          onDoubleClick={() => setViewport(chart.baseDomain)}
        >
          <defs>
            <clipPath id="team-efficiency-plot">
              <rect x={QUADRANT_PLOT.left} y={QUADRANT_PLOT.top} width={QUADRANT_PLOT.width} height={QUADRANT_PLOT.height} />
            </clipPath>
          </defs>
          <rect className="plot-area" x={QUADRANT_PLOT.left} y={QUADRANT_PLOT.top} width={QUADRANT_PLOT.width} height={QUADRANT_PLOT.height} />
          {xTicks.map((tick) => {
            const x = plotX(tick);
            return (
              <g className="axis-tick" key={`x-${tick}`}>
                <line x1={x} y1={QUADRANT_PLOT.top} x2={x} y2={QUADRANT_PLOT.top + QUADRANT_PLOT.height} />
                <text x={x} y={QUADRANT_PLOT.top + QUADRANT_PLOT.height + 19}>
                  {tick.toFixed(1)}
                </text>
              </g>
            );
          })}
          {yTicks.map((tick) => {
            const y = plotY(tick);
            return (
              <g className="axis-tick axis-tick-y" key={`y-${tick}`}>
                <line x1={QUADRANT_PLOT.left} y1={y} x2={QUADRANT_PLOT.left + QUADRANT_PLOT.width} y2={y} />
                <text x={QUADRANT_PLOT.left - 9} y={y + 4}>
                  {tick.toFixed(1)}
                </text>
              </g>
            );
          })}
          <line className="axis-line" x1={QUADRANT_PLOT.left} y1={QUADRANT_PLOT.top} x2={QUADRANT_PLOT.left} y2={QUADRANT_PLOT.top + QUADRANT_PLOT.height} />
          <line className="axis-line" x1={QUADRANT_PLOT.left} y1={QUADRANT_PLOT.top + QUADRANT_PLOT.height} x2={QUADRANT_PLOT.left + QUADRANT_PLOT.width} y2={QUADRANT_PLOT.top + QUADRANT_PLOT.height} />
          <g clipPath="url(#team-efficiency-plot)">
            {showAverageX ? <line className="avg-line" x1={averageX} y1={QUADRANT_PLOT.top} x2={averageX} y2={QUADRANT_PLOT.top + QUADRANT_PLOT.height} /> : null}
            {showAverageY ? <line className="avg-line" x1={QUADRANT_PLOT.left} y1={averageY} x2={QUADRANT_PLOT.left + QUADRANT_PLOT.width} y2={averageY} /> : null}
            {plottedPoints.map((team, index) => {
              const id = getTeamId(team);
              const isSelected = id === selectedId;
              const x = plotX(team.off_rating as number);
              const y = plotY(team.def_rating as number);
              const shouldShowLabel = showTeamNames || isSelected || (!selectedId && chart.extremeIds.has(id));
              const label = labelPosition(x, y, index);

              return (
                <g
                  className={isSelected ? "team-point team-point-selected" : "team-point"}
                  key={id || teamName(team)}
                  onPointerEnter={(event) => moveTooltip(team, event)}
                  onPointerMove={(event) => moveTooltip(team, event)}
                  onPointerLeave={() => setHoverTeam(null)}
                >
                  <circle cx={x} cy={y} r={isSelected ? 8 : 6} />
                  {shouldShowLabel ? (
                    <text x={label.x} y={label.y} textAnchor={label.anchor}>
                      {translateTeamName(team.team_abbr ?? team.team_name, "short")}
                    </text>
                  ) : null}
                </g>
              );
            })}
          </g>
          <text className="quadrant-note" x="70" y="64">防守更好 / 进攻承压</text>
          <text className="quadrant-note" x="360" y="64">强攻强守</text>
          <text className="quadrant-note" x="70" y="256">攻防承压</text>
          <text className="quadrant-note" x="346" y="256">强进攻 / 防守偏弱</text>
          <text className="axis-label" x="292" y="309">进攻效率</text>
          <text className="axis-label axis-label-y" x="14" y="166">防守效率</text>
          {selectionRect && selectionRect.width > 2 && selectionRect.height > 2 ? (
            <rect className="zoom-selection" x={selectionRect.x} y={selectionRect.y} width={selectionRect.width} height={selectionRect.height} />
          ) : null}
        </svg>
        {hoverTeam ? (
          <div className="quadrant-tooltip" style={{ left: hoverTeam.x, top: hoverTeam.y }}>
            <strong>{teamName(hoverTeam.team)}</strong>
            <span>进攻效率：{formatNumber(hoverTeam.team.off_rating)}</span>
            <span>防守效率：{formatNumber(hoverTeam.team.def_rating)}</span>
            <span>净效率：{formatNumber(hoverTeam.team.net_rating)}</span>
            <span>节奏：{formatNumber(hoverTeam.team.pace)}</span>
          </div>
        ) : null}
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
  const offenseRows = offense.data?.table ?? [];
  const defenseRows = defense.data?.table ?? [];

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
  const selectedOffense = useMemo(() => matchTeam(offenseRows, selectedTeam), [offenseRows, selectedTeam]);
  const selectedDefense = useMemo(() => matchTeam(defenseRows, selectedTeam), [defenseRows, selectedTeam]);
  const currentTeamData = useMemo(
    () => buildCurrentTeamData(selectedTeam, selectedOffense, selectedDefense),
    [selectedTeam, selectedOffense, selectedDefense],
  );
  const isLoading = overview.loading || offense.loading || defense.loading;
  const loadError = overview.error ?? offense.error ?? defense.error;
  const noTeamData = !isLoading && !loadError && teams.length === 0;
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
      <AsyncStatus loading={isLoading} error={loadError} empty={noTeamData} emptyMessage={`当前赛季 ${season} 暂无球队数据。`} />
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
        <StatCard label="进攻效率" value={formatNumber(currentTeamData?.off_rating)} trend={metricRank(offenseRows.length > 0 ? offenseRows : teams, currentTeamData, "OFF_RATING")} tone="blue" tooltip={KPI_TOOLTIP_COPY.offense} />
        <StatCard label="防守效率" value={formatNumber(currentTeamData?.def_rating)} trend={metricRank(defenseRows.length > 0 ? defenseRows : teams, currentTeamData, "DEF_RATING")} tone="green" tooltip={KPI_TOOLTIP_COPY.defense} />
        <StatCard label="净效率" value={formatNumber(currentTeamData?.net_rating)} trend={netRatingRank(currentTeamData)} tone="violet" tooltip={KPI_TOOLTIP_COPY.net} />
        <StatCard label="比赛节奏" value={formatNumber(currentTeamData?.pace)} trend="每 48 分钟回合" tone="amber" tooltip={KPI_TOOLTIP_COPY.pace} />
      </section>
      <section className="dashboard-grid">
        <MetricExplainer title="球队进攻效率分析" subtitle="拆解得分效率、失误控制、二次进攻和造罚球能力。" team={currentTeamData} rows={offenseRows.length > 0 ? offenseRows : teams} metrics={["OFF_RATING", "EFG_PCT", "TM_TOV_PCT", "OREB_PCT", "FTA_RATE"]} />
        <MetricExplainer title="球队防守效率分析" subtitle="观察限制投篮、制造失误、保护篮板和控制犯规的表现。" team={currentTeamData} rows={defenseRows.length > 0 ? defenseRows : teams} metrics={["DEF_RATING", "OPP_EFG_PCT", "OPP_TOV_PCT", "DREB_PCT", "OPP_FT_RATE"]} />
      </section>
      <EfficiencyQuadrant teams={teams} selectedTeam={currentTeamData} />
      <DataTable
        title="球队排名"
        subtitle="按净效率排序；防守效率数值越低，防守表现越好"
        columns={["排名", "球队", "场次", "战绩", "进攻效率", "防守效率", "净效率", "比赛节奏"]}
        rows={rankingRows}
        showMetricTooltips={false}
      />
    </div>
  );
}
