import { useMemo, useState } from "react";

export type GameFlowDatum = {
  period?: number | null;
  game_clock?: string | null;
  home_score: number;
  away_score: number;
  score_margin: number;
  event?: string | null;
};

export type GameFlowEvent = {
  period?: number | null;
  game_clock?: string | null;
  description?: string | null;
  type?: string | null;
};

type GameFlowChartProps = {
  points: GameFlowDatum[];
  events?: GameFlowEvent[];
  homeLabel?: string;
  awayLabel?: string;
};

type ChartPoint = GameFlowDatum & {
  x: number;
  y: number;
  timeLabel: string;
  eventLabel: string;
};

const WIDTH = 720;
const HEIGHT = 320;
const PADDING = { top: 24, right: 28, bottom: 46, left: 48 };
const INNER_WIDTH = WIDTH - PADDING.left - PADDING.right;
const INNER_HEIGHT = HEIGHT - PADDING.top - PADDING.bottom;

function clockToSeconds(clock?: string | null) {
  if (!clock) {
    return null;
  }

  const parts = clock.split(":").map((part) => Number(part));
  if (parts.some((part) => Number.isNaN(part))) {
    return null;
  }

  if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  }

  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }

  return null;
}

function elapsedSeconds(point: GameFlowDatum, fallbackIndex: number) {
  const period = point.period ?? 1;
  const periodLength = period <= 4 ? 12 * 60 : 5 * 60;
  const priorRegulation = Math.min(period - 1, 4) * 12 * 60;
  const priorOvertime = Math.max(period - 5, 0) * 5 * 60;
  const remaining = clockToSeconds(point.game_clock);

  if (remaining === null) {
    return fallbackIndex;
  }

  return priorRegulation + priorOvertime + Math.max(periodLength - remaining, 0);
}

function timeLabel(point: GameFlowDatum) {
  const period = point.period ? (point.period <= 4 ? `第 ${point.period} 节` : `加时 ${point.period - 4}`) : "时间";
  return point.game_clock ? `${period} ${point.game_clock}` : period;
}

function eventKey(event: Pick<GameFlowEvent, "period" | "game_clock">) {
  return `${event.period ?? ""}-${event.game_clock ?? ""}`;
}

function eventText(type?: string | null) {
  const labels: Record<string, string> = {
    max_lead: "最大领先",
    lead_change: "领先变化",
    scoring_run: "得分高潮",
    clutch_score: "关键得分",
  };

  return type ? labels[type] ?? type : "比赛事件";
}

export default function GameFlowChart({ points, events = [], homeLabel = "主队", awayLabel = "客队" }: GameFlowChartProps) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const chart = useMemo(() => {
    if (points.length === 0) {
      return { points: [] as ChartPoint[], line: "", zeroY: PADDING.top + INNER_HEIGHT / 2, maxAbs: 1 };
    }

    const eventMap = new Map(events.map((event) => [eventKey(event), event.description || eventText(event.type)]));
    const elapsed = points.map((point, index) => elapsedSeconds(point, index));
    const minElapsed = Math.min(...elapsed);
    const maxElapsed = Math.max(...elapsed);
    const elapsedRange = Math.max(maxElapsed - minElapsed, 1);
    const maxAbs = Math.max(...points.map((point) => Math.abs(point.score_margin)), 1);

    const mapped = points.map((point, index) => {
      const x = PADDING.left + ((elapsed[index] - minElapsed) / elapsedRange) * INNER_WIDTH;
      const y = PADDING.top + ((maxAbs - point.score_margin) / (maxAbs * 2)) * INNER_HEIGHT;
      const key = eventKey(point);

      return {
        ...point,
        x,
        y,
        timeLabel: timeLabel(point),
        eventLabel: point.event || eventMap.get(key) || "常规回合",
      };
    });

    return {
      points: mapped,
      line: mapped.map((point) => `${point.x},${point.y}`).join(" "),
      zeroY: PADDING.top + INNER_HEIGHT / 2,
      maxAbs,
    };
  }, [events, points]);

  const active = activeIndex === null ? null : chart.points[activeIndex];

  if (points.length === 0) {
    return (
      <section className="game-flow-card">
        <div className="card-heading">
          <div>
            <h2>比赛走势</h2>
            <p>当逐回合数据可用时，这里会显示分差走势线。</p>
          </div>
        </div>
        <div className="empty-panel">暂无比赛走势数据</div>
      </section>
    );
  }

  return (
    <section className="game-flow-card">
      <div className="card-heading">
        <div>
          <h2>比赛走势</h2>
          <p>
            Y 轴是分差。正值代表 {homeLabel} 领先，负值代表 {awayLabel} 领先。
          </p>
        </div>
        <span>{points.length} 个回合</span>
      </div>

      <div className="game-flow-shell">
        <svg className="game-flow-svg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="比分分差走势折线图">
          <defs>
            <linearGradient id="gameFlowLine" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stopColor="#4f9fcf" />
              <stop offset="100%" stopColor="#5364c9" />
            </linearGradient>
          </defs>
          {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
            const y = PADDING.top + tick * INNER_HEIGHT;
            return <line className="game-flow-grid" key={tick} x1={PADDING.left} x2={WIDTH - PADDING.right} y1={y} y2={y} />;
          })}
          <line className="game-flow-axis" x1={PADDING.left} x2={WIDTH - PADDING.right} y1={chart.zeroY} y2={chart.zeroY} />
          <text className="game-flow-y-label" x={10} y={PADDING.top + 4}>
            +{chart.maxAbs}
          </text>
          <text className="game-flow-y-label" x={17} y={chart.zeroY + 4}>
            0
          </text>
          <text className="game-flow-y-label" x={10} y={PADDING.top + INNER_HEIGHT + 4}>
            -{chart.maxAbs}
          </text>
          <polyline className="game-flow-line" points={chart.line} />
          {chart.points.map((point, index) => (
            <circle
              className={`game-flow-dot${activeIndex === index ? " active" : ""}`}
              key={`${point.timeLabel}-${index}`}
              cx={point.x}
              cy={point.y}
              r={activeIndex === index ? 5 : 3.5}
              onMouseEnter={() => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
              onFocus={() => setActiveIndex(index)}
              onBlur={() => setActiveIndex(null)}
              tabIndex={0}
            />
          ))}
          {chart.points.length > 0 ? (
            <>
              <text className="game-flow-x-label" x={PADDING.left} y={HEIGHT - 14}>
                {chart.points[0].timeLabel}
              </text>
              <text className="game-flow-x-label end" x={WIDTH - PADDING.right} y={HEIGHT - 14}>
                {chart.points[chart.points.length - 1].timeLabel}
              </text>
            </>
          ) : null}
        </svg>

        {active ? (
          <div className="game-flow-tooltip" style={{ left: `${(active.x / WIDTH) * 100}%`, top: `${(active.y / HEIGHT) * 100}%` }}>
            <strong>{active.timeLabel}</strong>
            <span>
              {awayLabel} {active.away_score} - {active.home_score} {homeLabel}
            </span>
            <span>
              分差 {active.score_margin > 0 ? "+" : ""}
              {active.score_margin}
            </span>
            <p>{active.eventLabel}</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
