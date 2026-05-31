import type { ShotZoneSummary } from "../api/client";
import { formatNumber, formatPercent } from "../api/formatters";
import { efficiencyLevelLabel, shotZoneLabel } from "../constants/zhLabels";

type HeatMapProps = {
  zones: ShotZoneSummary[];
  title?: string;
};

type ZoneShape = {
  key: string;
  label: string;
  d?: string;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
};

const ZONE_SHAPES: ZoneShape[] = [
  { key: "Backcourt", label: "后场", x: 0, y: 0, width: 500, height: 72 },
  { key: "Above the Break 3", label: "弧顶三分", d: "M30 328 A237.5 237.5 0 0 1 470 328 L410 218 A126 126 0 0 0 90 218 Z" },
  { key: "Left Corner 3", label: "左底角三分", x: 0, y: 328, width: 62, height: 142 },
  { key: "Right Corner 3", label: "右底角三分", x: 438, y: 328, width: 62, height: 142 },
  { key: "Mid-Range", label: "中距离", d: "M90 332 A178 178 0 0 1 410 332 L370 392 A118 118 0 0 0 130 392 Z" },
  { key: "In The Paint", label: "禁区", x: 170, y: 280, width: 160, height: 190 },
  { key: "Restricted Area", label: "合理冲撞区", d: "M210 418 A40 40 0 0 0 290 418 L290 470 H210 Z" },
];

function zoneLabel(zone: ShotZoneSummary) {
  return shotZoneLabel(zone.shot_zone_basic ?? zone.shot_zone_area ?? zone.shot_zone_range);
}

function findZone(zones: ShotZoneSummary[], key: string) {
  return zones.find((zone) => zone.shot_zone_basic === key);
}

function zoneClass(zone?: ShotZoneSummary) {
  const level = zone?.efficiency_level?.toLowerCase();
  if (level === "high" || level === "normal" || level === "low") {
    return `heat-zone heat-zone-${level}`;
  }

  return "heat-zone heat-zone-empty";
}

function zoneTitle(shape: ZoneShape, zone?: ShotZoneSummary) {
  if (!zone) {
    return `${shape.label}: 暂无后端区域汇总`;
  }

  return `${zoneLabel(zone)}：出手 ${zone.fga}，命中 ${zone.fgm}，命中率 ${formatPercent(zone.fg_pct)}，每次出手得分 ${formatNumber(zone.pps)}`;
}

export default function HeatMap({ zones, title = "投篮热区" }: HeatMapProps) {
  return (
    <div className="heat-map" role="img" aria-label={title}>
      <svg viewBox="0 0 500 470" preserveAspectRatio="xMidYMid meet">
        <rect className="heat-court" x="1" y="1" width="498" height="468" rx="2" />
        {ZONE_SHAPES.map((shape) => {
          const zone = findZone(zones, shape.key);

          if (shape.d) {
            return (
              <path className={zoneClass(zone)} d={shape.d} key={shape.key}>
                <title>{zoneTitle(shape, zone)}</title>
              </path>
            );
          }

          return (
            <rect className={zoneClass(zone)} key={shape.key} x={shape.x} y={shape.y} width={shape.width} height={shape.height}>
              <title>{zoneTitle(shape, zone)}</title>
            </rect>
          );
        })}
        <path className="heat-line" d="M190 470 V280 H310 V470 M30 470 V328 M470 470 V328 M30 328 A237.5 237.5 0 0 1 470 328" />
        <line className="heat-line" x1="220" x2="280" y1="430" y2="430" />
        <circle className="heat-line" cx="250" cy="418" r="7.5" />
      </svg>
      <div className="heat-zone-list">
        {zones.length === 0 ? (
          <span>暂无热区数据</span>
        ) : (
          zones.slice(0, 7).map((zone) => (
            <span className={`efficiency-pill efficiency-${zone.efficiency_level ?? "normal"}`} key={`${zoneLabel(zone)}-${zone.shot_zone_area ?? ""}-${zone.shot_zone_range ?? ""}`}>
              {zoneLabel(zone)} {formatPercent(zone.fg_pct)} · {efficiencyLevelLabel(zone.efficiency_level)}
            </span>
          ))
        )}
      </div>
    </div>
  );
}
