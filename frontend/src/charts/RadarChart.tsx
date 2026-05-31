import { useMemo } from "react";
import { radarLabel } from "../constants/zhLabels";

export type RadarChartPoint = {
  key: string;
  label: string;
  value: number;
};

type RadarChartProps = {
  data: RadarChartPoint[];
  title?: string;
};

const SIZE = 420;
const CENTER = SIZE / 2;
const RADIUS = 136;
const RINGS = [20, 40, 60, 80, 100];

function polarPoint(index: number, total: number, value: number) {
  const angle = -Math.PI / 2 + (index / total) * Math.PI * 2;
  const distance = (value / 100) * RADIUS;

  return {
    x: CENTER + Math.cos(angle) * distance,
    y: CENTER + Math.sin(angle) * distance,
  };
}

function ringPath(total: number, value: number) {
  return Array.from({ length: total })
    .map((_, index) => {
      const point = polarPoint(index, total, value);
      return `${point.x},${point.y}`;
    })
    .join(" ");
}

export default function RadarChart({ data, title = "球员能力结构雷达" }: RadarChartProps) {
  const chart = useMemo(() => {
    const points = data.map((item, index) => polarPoint(index, data.length, Number.isFinite(item.value) ? item.value : 0));
    const polygon = points.map((point) => `${point.x},${point.y}`).join(" ");
    const labelPoints = data.map((item, index) => {
      const point = polarPoint(index, data.length, 126);
      return { ...item, ...point };
    });

    return { points, polygon, labelPoints };
  }, [data]);

  if (data.length === 0) {
    return <div className="radar-empty">暂无雷达评分</div>;
  }

  return (
    <div className="radar-chart" role="img" aria-label={title}>
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`}>
        <defs>
          <linearGradient id="radarFill" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#6672d8" stopOpacity="0.34" />
            <stop offset="100%" stopColor="#4f9fcf" stopOpacity="0.2" />
          </linearGradient>
        </defs>

        {RINGS.map((ring) => (
          <polygon key={ring} className="radar-ring" points={ringPath(data.length, ring)} />
        ))}

        {data.map((item, index) => {
          const axisEnd = polarPoint(index, data.length, 100);
          return <line key={item.key} className="radar-axis" x1={CENTER} x2={axisEnd.x} y1={CENTER} y2={axisEnd.y} />;
        })}

        <polygon className="radar-area" points={chart.polygon} />

        {chart.points.map((point, index) => (
          <circle key={data[index].key} className="radar-point" cx={point.x} cy={point.y} r="4.5">
            <title>
              {radarLabel(data[index].label)} {data[index].value.toFixed(0)}
            </title>
          </circle>
        ))}

        {chart.labelPoints.map((point) => (
          <g key={point.key}>
            <text className="radar-label" x={point.x} y={point.y - 5} textAnchor="middle">
              {radarLabel(point.label)}
            </text>
            <text className="radar-value" x={point.x} y={point.y + 12} textAnchor="middle">
              {point.value.toFixed(0)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
