import type { ShotPoint } from "../api/client";
import { shotZoneLabel } from "../constants/zhLabels";

type ShotChartProps = {
  shots: ShotPoint[];
  title?: string;
};

const COURT_WIDTH = 500;
const COURT_HEIGHT = 470;
const BASKET_Y = 52.5;
const MAX_Y = COURT_HEIGHT - 1;

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function plotShot(shot: ShotPoint) {
  const locX = typeof shot.loc_x === "number" && Number.isFinite(shot.loc_x) ? shot.loc_x : 0;
  const locY = typeof shot.loc_y === "number" && Number.isFinite(shot.loc_y) ? shot.loc_y : 0;
  const x = clamp(locX + COURT_WIDTH / 2, 2, COURT_WIDTH - 2);
  const y = clamp(COURT_HEIGHT - (locY + BASKET_Y), 2, MAX_Y);

  return { x, y };
}

function shotTitle(shot: ShotPoint) {
  const result = shot.shot_made_flag === 1 ? "命中" : "未命中";
  const zone = shotZoneLabel(shot.shot_zone_basic);
  const range = shot.shot_zone_range ? `，${shotZoneLabel(shot.shot_zone_range)}` : "";
  const action = shot.action_type ? `, ${shot.action_type}` : "";
  return `${result}：${zone}${range}${action}`;
}

export default function ShotChart({ shots, title = "投篮图" }: ShotChartProps) {
  return (
    <div className="shot-chart" role="img" aria-label={title}>
      <svg viewBox={`0 0 ${COURT_WIDTH} ${COURT_HEIGHT}`} preserveAspectRatio="xMidYMid meet">
        <rect className="court-line court-boundary" x="1" y="1" width="498" height="468" rx="2" />
        <line className="court-line" x1="0" x2="500" y1="0" y2="0" />
        <path className="court-line" d="M190 470 V280 H310 V470" />
        <path className="court-line court-line-muted" d="M190 280 A60 60 0 0 0 310 280" />
        <path className="court-line" d="M170 470 V280 H330 V470" />
        <path className="court-line court-line-muted" d="M170 280 A80 80 0 0 0 330 280" />
        <path className="court-line" d="M30 470 V328 M470 470 V328 M30 328 A237.5 237.5 0 0 1 470 328" />
        <path className="court-line" d="M210 418 A40 40 0 0 0 290 418" />
        <line className="court-line" x1="220" x2="280" y1="430" y2="430" />
        <circle className="court-line" cx="250" cy="418" r="7.5" />
        <path className="court-line court-line-muted" d="M190 0 A60 60 0 0 0 310 0" />

        {shots.map((shot, index) => {
          const point = plotShot(shot);
          const made = shot.shot_made_flag === 1;

          return (
            <g className={made ? "shot-point shot-point-made" : "shot-point shot-point-missed"} key={`${shot.loc_x}-${shot.loc_y}-${index}`}>
              {made ? <circle cx={point.x} cy={point.y} r="4.8" /> : <path d={`M${point.x - 4.8} ${point.y - 4.8} L${point.x + 4.8} ${point.y + 4.8} M${point.x + 4.8} ${point.y - 4.8} L${point.x - 4.8} ${point.y + 4.8}`} />}
              <title>{shotTitle(shot)}</title>
            </g>
          );
        })}
      </svg>
      <div className="shot-legend" aria-hidden="true">
        <span>
          <i className="legend-dot legend-made" />
          命中
        </span>
        <span>
          <i className="legend-x" />
          未命中
        </span>
      </div>
    </div>
  );
}
